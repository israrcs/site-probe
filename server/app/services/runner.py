from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

import httpx
from playwright.async_api import Error as PWError
from playwright.async_api import Page

from app.core.config import settings
from app.core.models import (
    SEVERITY_WEIGHT,
    Category,
    Issue,
    PageResult,
    Run,
    RunStatus,
    VIEWPORT_SIZES,
)
from app.core.store import store
from app.utils.urls import is_web_url, normalize_url, same_site, slug_for_url, strip_fragment

from .annotator import annotate_and_crop
from .browser import BrowserManager
from .crawler import Robots, extract_page_links, fetch_sitemap_urls
from .engines import EngineContext
from .engines import accessibility as a11y_engine
from .engines import console_network as console_engine
from .engines import functional as functional_engine
from .engines import performance as perf_engine
from .engines import security as security_engine
from .engines import seo as seo_engine
from .engines.performance import PERF_INIT_JS
from .reporter import write_reports

log = logging.getLogger("siteprobe.runner")

# A real Chrome fingerprint: many sites (CDN bot protection, WAFs) block
# non-browser user agents outright. Overridable via RunOptions.user_agent.
DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Paths that typically indicate an authentication wall after redirect.
LOGIN_HINTS = ("login", "signin", "sign-in", "sign_in", "wp-login", "auth",
               "session/new", "account/login")

ENGINE_BY_CATEGORY = {
    Category.functional: functional_engine.run,
    Category.console: console_engine.run,
    Category.network: console_engine.run,
    Category.a11y: a11y_engine.run,
    Category.seo: seo_engine.run,
    Category.security: security_engine.run,
    Category.performance: perf_engine.run,
}


def attach_capture(page: Page) -> dict:
    """Attach console/network listeners; returns a buffer dict read later."""
    cap: dict = {
        "console": [], "pageerrors": [], "failed": [],
        "responses": [], "request_urls": [], "headers": {},
    }

    def on_console(msg):
        if msg.type in ("error", "warning"):
            loc = msg.location or {}
            cap["console"].append({
                "type": msg.type,
                "text": (msg.text or "")[:500],
                "location": f"{loc.get('url', '')}:{loc.get('lineNumber', '')}",
            })

    def on_request_failed(r):
        try:
            if r.frame == page.main_frame:
                # Main-document aborts happen when SiteProbe itself abandons a
                # slow first navigation attempt (load -> domcontentloaded ->
                # commit retry chain). goto() reports real failures; don't
                # double-report our own aborted attempt as "Request failed".
                return
        except Exception:
            pass
        cap["failed"].append(
            {"url": r.url, "method": r.method, "failure": str(r.failure)})

    page.on("console", on_console)
    page.on("pageerror", lambda e: cap["pageerrors"].append(str(e)[:500]))
    page.on("requestfailed", on_request_failed)
    page.on("request", lambda r: cap["request_urls"].append(r.url))
    page.on("response", lambda r: cap["responses"].append(
        {"url": r.url, "status": r.status}) if r.status >= 400 else None)
    return cap


def compute_scores(run: Run) -> dict:
    by_cat: Dict[str, List[Issue]] = {c.value: [] for c in Category
                                      if c in run.options.engines}
    for issue in run.issues:
        by_cat.setdefault(issue.category.value, []).append(issue)
    cats = {}
    for cat, items in by_cat.items():
        penalty = sum(SEVERITY_WEIGHT[i.severity.value] for i in items)
        cats[cat] = max(0, 100 - penalty)
    total = sum(SEVERITY_WEIGHT[i.severity.value] for i in run.issues)
    overall = max(0, 100 - total)
    grade = ("A" if overall >= 90 else "B" if overall >= 80 else
             "C" if overall >= 70 else "D" if overall >= 60 else "F")
    return {"overall": overall, "grade": grade, "categories": cats}


class Runner:
    """Executes one run: crawl + engines + screenshots + reports."""

    def __init__(self, run: Run) -> None:
        self.run = run
        self.run_dir = settings.runs_dir / run.id
        self.shots_dir = self.run_dir / "screenshots"

    def _set(self, phase: Optional[str] = None, **kw) -> None:
        if phase is not None:
            self.run.phase = phase
        for k, v in kw.items():
            setattr(self.run, k, v)
        store.broadcast(self.run)

    async def execute(self) -> None:
        run = self.run
        run.status = RunStatus.running
        run.started_at = time.time()
        self._set(phase="starting browser")
        self.shots_dir.mkdir(parents=True, exist_ok=True)

        bm = BrowserManager()
        http = httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.request_timeout_s,
            headers={"User-Agent": run.options.user_agent or DEFAULT_UA},
        )
        try:
            await bm.start()
            await self._crawl(bm, http)
            self._set(phase="computing scores")
            run.scores = compute_scores(run)
            self._set(phase="generating reports")
            write_reports(run, self.run_dir)
            run.status = RunStatus.completed
            run.finished_at = time.time()
            self._set(phase="done")
        except asyncio.CancelledError:
            run.status = RunStatus.cancelled
            run.finished_at = time.time()
            self._set(phase="cancelled")
            raise
        except Exception as exc:
            log.exception("run %s failed", run.id)
            run.status = RunStatus.failed
            run.error = str(exc)[:1000]
            run.finished_at = time.time()
            self._set(phase="failed")
        finally:
            await http.aclose()
            await bm.stop()

    async def _crawl(self, bm: BrowserManager, http: httpx.AsyncClient) -> None:
        run = self.run
        opts = run.options
        seed = opts.url
        primary_vp = opts.viewports[0].value
        extra_vps = [v.value for v in opts.viewports[1:]]

        robots = None
        if opts.follow_robots:  # unrestricted by default; opt in to robots.txt
            robots = await Robots.load(http, seed)
        # sitemap is discovery, not a restriction — always try it
        sitemap_urls = await fetch_sitemap_urls(http, seed)

        frontier: deque = deque([seed])
        seen: Set[str] = {seed}
        for u in sitemap_urls:
            if same_site(u, seed) and u not in seen:
                frontier.append(u)
                seen.add(u)

        visited: Set[str] = set()
        order: List[str] = []
        results: Dict[str, PageResult] = {}
        slugs: Dict[str, str] = {}
        used_slugs: Set[str] = set()

        while frontier and len(order) < opts.max_pages:
            url = frontier.popleft()
            norm = normalize_url(strip_fragment(url))
            if norm in visited or not is_web_url(url):
                continue
            if robots and not robots.allowed(url):
                log.info("robots.txt disallows %s", url)
                visited.add(norm)
                continue
            visited.add(norm)
            run.pages_total = max(run.pages_total, len(seen))
            self._set(phase="scanning pages", current_url=url)

            res, links = await self._visit_page(
                bm, http, url, primary_vp, full_scan=True,
                slugs=slugs, used_slugs=used_slugs)
            if res is None:
                continue
            order.append(url)
            results[url] = res
            run.pages.append(res)
            run.pages_done = len(order)

            for link in links:
                n = normalize_url(strip_fragment(link))
                if (is_web_url(n) and same_site(n, seed)
                        and n not in seen and n not in visited):
                    if robots is None or robots.allowed(n):
                        frontier.append(n)
                        seen.add(n)
            run.pages_total = max(run.pages_total, len(seen))
            self._set(phase="scanning pages")

            if opts.delay_ms:
                await asyncio.sleep(opts.delay_ms / 1000)

        # Extra viewports: screenshots + responsive overflow check only.
        for vp in extra_vps:
            self._set(phase=f"capturing {vp} screenshots")
            for url in order:
                await self._visit_page(bm, http, url, vp, full_scan=False,
                                       slugs=slugs, used_slugs=used_slugs)
                if opts.delay_ms:
                    await asyncio.sleep(opts.delay_ms / 1000)

        # Cross-page SEO: duplicate titles
        seen_titles: Dict[str, str] = {}
        for url in order:
            t = (results[url].title or "").strip().lower()
            if not t:
                continue
            if t in seen_titles:
                run.issues.append(Issue(
                    run_id=run.id, page_url=url, viewport=primary_vp,
                    category="seo", severity="medium",
                    title="Duplicate page title",
                    description=f'"{results[url].title}" is also used by '
                    f"{seen_titles[t]}",
                    suggestion="Give every page a unique, descriptive title."))
            else:
                seen_titles[t] = url

        store.broadcast(run)

    async def _visit_page(
        self,
        bm: BrowserManager,
        http: httpx.AsyncClient,
        url: str,
        vp: str,
        full_scan: bool,
        slugs: Dict[str, str],
        used_slugs: Set[str],
    ) -> Tuple[Optional[PageResult], List[str]]:
        """Visit one page in one viewport: screenshot, engines, annotation."""
        run = self.run
        opts = run.options
        context = await bm.new_context(VIEWPORT_SIZES[vp], opts.timeout_ms,
                                       opts.user_agent, PERF_INIT_JS)
        page = await context.new_page()
        capture = attach_capture(page)
        new_issues: List[Issue] = []
        links: List[str] = []

        def make_issue(**kw) -> Issue:
            return Issue(run_id=run.id, page_url=url, viewport=vp, **kw)

        try:
            ectx = EngineContext(run_id=run.id, page_url=url, viewport=vp,
                                 http=http, capture=capture,
                                 new_issue=make_issue)
            # Resilient navigation with a SINGLE shared time budget (not three
            # full timeouts):
            #   1) try "load"   (full load event)
            #   2) fall back to "domcontentloaded" (document ready even when a
            #      sub-resource hangs — many sites never fire load/networkidle)
            #   3) last resort "commit" (response headers arrived; body may
            #      still stream — very slow servers)
            # If even that times out but the page partially rendered, degrade
            # gracefully: treat as loaded (informational note, not a failure).
            deadline = time.monotonic() + opts.timeout_ms / 1000

            def nav_budget() -> int:
                return max(5000, int((deadline - time.monotonic()) * 1000))

            resp = None
            nav_error: Optional[str] = None
            got_content = False
            for wait_until in ("load", "domcontentloaded", "commit"):
                try:
                    resp = await page.goto(url, wait_until=wait_until,
                                           timeout=nav_budget())
                    nav_error = None
                    break
                except PWError as exc:
                    nav_error = str(exc)
                # A timed-out goto can still leave a partially rendered doc.
                try:
                    html_len = len(await page.content())
                except Exception:
                    html_len = 0
                if html_len > 500:
                    got_content = True
                    break

            if resp is None and not got_content:
                first_line = (nav_error or "unknown").split("\n")[0][:200]
                new_issues.append(make_issue(
                    category="functional", severity="critical",
                    title=f"Page failed to load: {first_line}",
                    description=(nav_error or "")[:600],
                    suggestion="Check the URL, DNS, TLS certificate and server "
                    "availability. If the site is very slow, raise the page "
                    "timeout slider."))
                run.issues.extend(new_issues)
                return PageResult(url=url, status=None), links

            if resp is None and got_content:
                new_issues.append(make_issue(
                    category="performance", severity="info",
                    title="Page loaded very slowly (navigation timed out)",
                    description="The server took longer than the configured page "
                    "timeout to finish loading, but content did render so the "
                    "scan continued.",
                    suggestion="This is usually a server/CDN performance problem; "
                    "raise the page timeout in the UI for stricter tests."))

            # Grace period: give the network a moment to settle (better
            # screenshots/metrics) but NEVER fail the page if it stays busy.
            try:
                await page.wait_for_load_state(
                    "networkidle", timeout=min(8000, opts.timeout_ms))
            except Exception:
                pass

            status = resp.status if resp else None
            capture["headers"] = dict(resp.headers) if resp else None

            final_url = page.url
            tail = strip_fragment(final_url).lower()
            if strip_fragment(final_url).rstrip("/") != strip_fragment(url).rstrip("/") \
                    and any(hint in tail for hint in LOGIN_HINTS):
                new_issues.append(make_issue(
                    category="functional", severity="info",
                    title="Page redirected to a login/authentication page",
                    description=f"{url} redirects to {final_url}. The visible "
                    "content is behind authentication, so only the login wall "
                    "was tested (no credentials are used by SiteProbe).",
                    suggestion="If this page should be public, remove the auth "
                "redirect. For members-only pages, results cover the login wall "
                "only.",
                    metadata={"requested_url": url, "final_url": final_url}))
            if status and status >= 400:
                new_issues.append(make_issue(
                    category="functional",
                    severity="critical" if status >= 500 else "high",
                    title=f"Page returned HTTP {status}",
                    description=f"The main document of {url} responded with "
                    f"HTTP {status}.",
                    suggestion="Restore the resource or fix/remove links pointing "
                    "to it.",
                    metadata={"status": status}))
            title = await page.title()

            if url not in slugs:
                slugs[url] = slug_for_url(url, used_slugs)
            slug = slugs[url]
            rel_dir = f"screenshots/{slug}__{vp}"
            (self.run_dir / rel_dir).mkdir(parents=True, exist_ok=True)
            full_rel = f"{rel_dir}/fullpage.png"
            full_path = self.run_dir / full_rel
            await page.screenshot(path=str(full_path), full_page=True)

            if full_scan:
                selected = set(opts.engines)
                engines_to_run = []
                for cat, fn in ENGINE_BY_CATEGORY.items():
                    if cat in selected and fn not in engines_to_run:
                        engines_to_run.append(fn)
                for fn in engines_to_run:
                    name = fn.__module__.rsplit(".", 1)[-1]
                    try:
                        new_issues.extend(await asyncio.wait_for(
                            fn(page, ectx), timeout=settings.engine_timeout_s))
                    except asyncio.TimeoutError:
                        new_issues.append(make_issue(
                            category="functional", severity="info",
                            title=f"Engine '{name}' timed out on this page"))
                    except Exception as exc:
                        log.warning("engine %s failed on %s: %s", name, url, exc)
                        new_issues.append(make_issue(
                            category="functional", severity="info",
                            title=f"Engine '{name}' failed on this page",
                            description=str(exc)[:300]))
                try:
                    links = await extract_page_links(page)
                except Exception:
                    links = []

            # Responsive overflow check (all viewports).
            try:
                overflow = await page.evaluate(
                    "() => document.documentElement.scrollWidth "
                    "- document.documentElement.clientWidth")
                if overflow and overflow > 2:
                    new_issues.append(make_issue(
                        category="functional", severity="medium",
                        title=f"Horizontal overflow of {overflow}px on {vp} viewport",
                        description="Content is wider than the viewport; visitors "
                        "must scroll sideways.",
                        suggestion="Look for fixed widths or elements that do not "
                        "wrap.",
                        metadata={"overflowPx": overflow, "viewport": vp}))
            except Exception:
                pass

            res = PageResult(
                url=url, final_url=final_url or None, status=status,
                title=title or None,
                screenshots={vp: full_rel},
                console_errors=len(capture.get("console", []))
                + len(capture.get("pageerrors", [])),
                failed_requests=len(capture.get("failed", []))
                + len(capture.get("responses", [])),
                metrics=(ectx.extra.get("metrics") or {}),
            )

            # Attach screenshots; annotate issues that carry a bounding box.
            n = 0
            for issue in new_issues:
                run.issues.append(issue)
                if full_path.exists():
                    issue.screenshot = {"fullPage": full_rel}
                    if issue.bounding_box:
                        n += 1
                        ann_rel = f"{rel_dir}/issue-{n:03d}.png"
                        el_rel = f"{rel_dir}/issue-{n:03d}-element.png"
                        try:
                            annotate_and_crop(full_path, issue,
                                              self.run_dir / ann_rel,
                                              self.run_dir / el_rel)
                            issue.screenshot = {
                                "annotated": ann_rel, "element": el_rel,
                                "fullPage": full_rel}
                        except Exception as exc:
                            log.warning("annotation failed: %s", exc)

            self._set(phase="scanning pages")
            return res, links

        finally:
            try:
                await context.close()
            except Exception:
                pass


