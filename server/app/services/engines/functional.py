from __future__ import annotations

import asyncio
import logging
from typing import List
from urllib.parse import urlsplit

from playwright.async_api import Page

from app.core.config import settings
from app.utils.urls import normalize_url, same_site, strip_fragment

from . import EngineContext, collect_js, issue_count_cap, short_url

log = logging.getLogger("siteprobe.functional")

LINKS_JS = collect_js("a[href]", 120, "href: el.href || ''")
IMAGES_JS = collect_js(
    "img", 60,
    "src: (el.currentSrc || el.src || ''), "
    "naturalWidth: el.naturalWidth, alt: el.alt || '', loading: el.loading || ''",
)

TARGET_EXISTS_JS = (
    "(id) => !!document.getElementById(id) || "
    "Array.from(document.querySelectorAll('a[name]'))"
    ".some(a => a.getAttribute('name') === id)"
)


async def run(page: Page, ctx: EngineContext) -> List:
    issues: List = []

    # ---------------------------------------------------------- anchors
    try:
        anchors = await page.evaluate(LINKS_JS, ["a[href]", 120])
    except Exception:
        anchors = []
    page_base = normalize_url(strip_fragment(ctx.page_url))

    for a in anchors:
        href = a.get("href", "")
        if href.lower().startswith("javascript:"):
            issues.append(ctx.new_issue(
                category="functional", severity="low",
                title='Link uses a "javascript:" URL',
                description=f'Anchor "{a.get("text") or a.get("selector")}" uses a '
                "javascript: href, which is a bad practice that breaks middle-click "
                "and accessibility.",
                suggestion="Use a real URL, or a <button> with an event listener.",
                selector=a.get("selector"), html_snippet=a.get("html"),
                bounding_box=a.get("box"),
                metadata={"href": href[:200]},
            ))
            continue

        parts = urlsplit(href)
        if parts.fragment and normalize_url(strip_fragment(href)) == page_base:
            frag = parts.fragment
            if frag.startswith(("!", "/")):
                # SPA hashbang/path routes (#!/about-us, #/contact) — client-
                # side navigation, NOT in-page anchors. Skip to avoid noise.
                continue
            try:
                exists = await page.evaluate(TARGET_EXISTS_JS, frag)
            except Exception:
                exists = True
            if not exists:
                issues.append(ctx.new_issue(
                    category="functional", severity="low",
                    title=f'Broken in-page anchor "#{frag}"',
                    description=f'The anchor links to "#{frag}" on this page but no '
                    "element with that id (or a[name]) exists.",
                    suggestion="Add an element with a matching id or fix the link.",
                    selector=a.get("selector"), html_snippet=a.get("html"),
                    bounding_box=a.get("box"),
                    metadata={"fragment": frag},
                ))
    issues = issue_count_cap(issues, 20, "in-page anchor/javascript: links")

    # ---------------------------------------------------------- images
    try:
        imgs = await page.evaluate(IMAGES_JS, ["img", 60])
    except Exception:
        imgs = []

    candidates = [im for im in imgs
                  if im.get("src") and not im["src"].startswith("data:")]
    sem = asyncio.Semaphore(settings.link_check_concurrency)

    async def check_image(im: dict) -> None:
        src = im["src"]
        async with sem:
            status = await _probe(ctx, src)
        if status is None or status >= 400:
            issues.append(ctx.new_issue(
                category="functional",
                severity="high" if not status or status >= 500 else "medium",
                title=f"Broken image: {short_url(src)}"
                + (f" (HTTP {status})" if status else " (unreachable)"),
                description="The browser could not load this image"
                + (f" and the file responded with HTTP {status}." if status else
                   " and the server could not be reached."),
                suggestion="Fix the image path/URL or replace the image.",
                selector=im.get("selector"), html_snippet=im.get("html"),
                bounding_box=im.get("box"),
                metadata={"src": src, "status": status, "alt": im.get("alt", "")},
            ))

    if candidates:
        await asyncio.gather(*(check_image(im) for im in candidates))

    # ---------------------------------------------------------- external links
    externals: List[str] = []
    for a in anchors:
        href = a.get("href", "")
        if href.startswith(("http://", "https://")) and not same_site(ctx.page_url, href):
            if href not in externals:
                externals.append(href)
    externals = externals[: settings.link_check_cap]

    async def check_link(url: str):
        async with sem:
            return url, await _probe(ctx, url)

    if externals:
        results = await asyncio.gather(*(check_link(u) for u in externals))
        anchor_by_href = {a.get("href"): a for a in anchors}
        for url, status in results:
            if status is None or status >= 400:
                a = anchor_by_href.get(url, {})
                issues.append(ctx.new_issue(
                    category="functional",
                    severity="medium" if status else "low",
                    title=f"Broken external link: {short_url(url)}"
                    + (f" (HTTP {status})" if status else " (unreachable)"),
                    description="This outbound link "
                    + (f"responded with HTTP {status}." if status else
                       "could not be reached (DNS/connection failure or timeout)."),
                    suggestion="Update or remove the dead link.",
                    selector=a.get("selector"), html_snippet=a.get("html"),
                    bounding_box=a.get("box"),
                    metadata={"href": url, "status": status},
                ))


    issues = issue_count_cap(issues, 40, "functional issues")
    return issues


async def _probe(ctx: EngineContext, url: str):
    """HEAD a URL, fall back to GET.

    Many servers mishandle or ignore HEAD (empty reply, connection reset) —
    a failed HEAD must NOT count as a broken link, so retry with GET before
    giving up. Returns final status code or None (truly unreachable)."""
    try:
        try:
            resp = await ctx.http.head(url)
            if resp.status_code in (405, 501, 403, 400):
                resp = await ctx.http.get(url)
            return resp.status_code
        except Exception:
            resp = await ctx.http.get(url)
            return resp.status_code
    except Exception:
        return None
