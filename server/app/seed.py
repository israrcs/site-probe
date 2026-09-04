"""Seed the in-memory store with realistic demo data on startup.

All demo targets use reserved example.* domains — no real/private sites.
Demo runs are tagged ``is_demo=True`` so the UI can label them, and every
completed demo run gets generated screenshot artifacts + downloadable reports,
so the dashboard feels alive on first load.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from PIL import Image, ImageDraw

from app.core.config import settings
from app.core.models import (
    SEVERITY_WEIGHT,
    BoundingBox,
    Issue,
    PageResult,
    Run,
    RunOptions,
    RunStatus,
)
from app.core.store import store
from app.services.annotator import annotate_and_crop
from app.services.reporter import write_reports


def _scores(run: Run) -> dict:
    by_cat: Dict[str, List[Issue]] = {}
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


def _issue(run_id: str, page_url: str, category, severity, title: str,
           description: str = "", suggestion: str = "",
           selector: Optional[str] = None,
           bbox: Optional[BoundingBox] = None,
           html: Optional[str] = None,
           meta: Optional[Dict] = None) -> Issue:
    return Issue(run_id=run_id, page_url=page_url, category=category,
                 severity=severity, title=title, description=description,
                 suggestion=suggestion, selector=selector, bounding_box=bbox,
                 html_snippet=html, viewport="desktop", metadata=meta or {})


def _page_image(width: int = 1000, height: int = 1400,
                accent: str = "#0ea5e9") -> Image.Image:
    """A fake but plausible webpage screenshot (nav, hero, cards, footer)."""
    img = Image.new("RGB", (width, height), "#f1f5f9")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, 84], fill="#0f172a")                 # navbar
    d.rectangle([26, 30, 190, 53], fill="#94a3b8")                 # logo
    for i in range(4):                                             # nav links
        d.rectangle([width - 600 + i * 150, 33, width - 540 + i * 150, 51],
                    fill="#475569")
    d.rectangle([40, 130, width - 40, 320], fill="#ffffff")        # hero panel
    d.rectangle([66, 155, 430, 186], fill="#0f172a")               # h1 line
    d.rectangle([66, 204, width - 130, 228], fill="#cbd5e1")       # para 1
    d.rectangle([66, 240, width - 220, 264], fill="#cbd5e1")       # para 2
    d.rectangle([66, 288, 270, 310], fill=accent)                  # CTA button
    for i in range(4):                                             # cards grid
        x = 44 + i * 236
        d.rectangle([x, 360, x + 216, 500], fill="#ffffff", outline="#e2e8f0")
        d.rectangle([x + 14, 374, x + 202, 438], fill="#e8edf5")   # card image
        d.rectangle([x + 14, 450, x + 182, 466], fill="#94a3b8")   # card title
        d.rectangle([x + 14, 474, x + 130, 486], fill="#e2e8f0")   # card meta
    d.rectangle([0, 900, width, 980], fill="#e2e8f0")              # mid band
    d.rectangle([70, 922, 420, 950], fill="#94a3b8")
    d.rectangle([0, height - 72, width, height], fill="#0f172a")   # footer
    d.rectangle([30, height - 46, 260, height - 30], fill="#64748b")
    return img


def _build_completed(run_id: str, url: str, slug: str, accent: str,
                     created_hours_ago: float, pages: List[PageResult],
                     issues: List[Issue], title: str) -> Run:
    now = time.time()
    started = now - created_hours_ago * 3600
    run = Run(
        id=run_id,
        options=RunOptions(url=url, max_pages=len(pages),
                           viewports=["desktop"], follow_robots=False),
        status=RunStatus.completed, phase="done",
        pages_done=len(pages), pages_total=len(pages),
        pages=pages, issues=issues, is_demo=True,
        created_at=started - 30, started_at=started,
        finished_at=started + max(25, 60 * len(pages)),
    )
    run.scores = _scores(run)

    run_dir = settings.runs_dir / run.id
    rel_dir = f"screenshots/{slug}__desktop"
    (run_dir / rel_dir).mkdir(parents=True, exist_ok=True)
    full_rel = f"{rel_dir}/fullpage.png"
    _page_image(accent=accent).save(run_dir / full_rel)

    for pr in pages:
        pr.screenshots = {"desktop": full_rel}
        pr.title = pr.title or title

    ann = 0
    for issue in issues:
        issue.screenshot = {"fullPage": full_rel}
        if issue.bounding_box:
            ann += 1
            ann_rel = f"{rel_dir}/issue-{ann:03d}.png"
            el_rel = f"{rel_dir}/issue-{ann:03d}-element.png"
            annotate_and_crop(run_dir / full_rel, issue,
                              run_dir / ann_rel, run_dir / el_rel)
            issue.screenshot = {
                "annotated": ann_rel, "element": el_rel,
                "fullPage": full_rel,
            }

    write_reports(run, run_dir)
    store.add(run)
    return run


def _metrics(ttfb=1200, fcp=1600, lcp=2400, cls=0.12, nodes=640, reqs=48,
             kb=2140, slowest=None) -> Dict:
    return {
        "ttfb": ttfb, "fcp": fcp, "lcp": lcp, "cls": cls,
        "domNodes": nodes, "requests": reqs, "transferKB": kb,
        "slowest": slowest or [{"url": "https://cdn.example.net/app.js",
                                "ms": 620, "kb": 340}],
    }


def _cancelled_run() -> Run:
    """A run that was cancelled mid-scan (variety in the history list)."""
    now = time.time()
    started = now - 3 * 3600
    url = "https://app.example.net/"
    run = Run(
        id="demo-app",
        options=RunOptions(url=url, max_pages=10, viewports=["desktop"],
                           follow_robots=False),
        status=RunStatus.cancelled, phase="cancelled",
        pages_done=2, pages_total=6, is_demo=True,
        created_at=started - 20, started_at=started,
        finished_at=started + 90,
    )
    run_dir = settings.runs_dir / run.id
    rel_dir = "screenshots/app__desktop"
    (run_dir / rel_dir).mkdir(parents=True, exist_ok=True)
    full_rel = f"{rel_dir}/fullpage.png"
    _page_image(accent="#8b5cf6").save(run_dir / full_rel)
    pages = [
        PageResult(url=url, status=200, title="Example App — Dashboard",
                   screenshots={"desktop": full_rel},
                   console_errors=2, failed_requests=1,
                   metrics=_metrics(ttfb=2100, fcp=2900, cls=0.21, kb=3740)),
        PageResult(url="https://app.example.net/settings", status=200,
                   title="Settings — Example App",
                   screenshots={"desktop": full_rel},
                   console_errors=0, failed_requests=0,
                   metrics=_metrics(ttfb=980, fcp=1300, cls=0.05)),
    ]
    run.pages = pages
    run.issues = [
        _issue(run.id, url, "seo", "high", "Missing meta description",
               'No <meta name="description"> tag found.',
               "Add a 120-160 character meta description."),
        _issue(run.id, url, "security", "medium",
               "Missing Content-Security-Policy header",
               "CSP mitigates XSS and injection attacks.",
               "Add a Content-Security-Policy response header."),
        _issue(run.id, url, "a11y", "medium",
               "All page content should be contained by landmarks",
               "Some page content is not contained by landmarks.",
               "Wrap content in header/main/footer landmarks."),
    ]
    store.add(run)
    return run


def _build_demo_example() -> None:
    """https://example.com — a minimal page (grade F, matches a real scan)."""
    url = "https://example.com/"
    page = PageResult(url=url, status=200, title="Example Domain",
                      console_errors=0, failed_requests=0,
                      metrics=_metrics(ttfb=80, fcp=95, lcp=120, cls=0.0,
                                       nodes=30, reqs=4, kb=2))
    issues = [
        _issue("demo-example", url, "a11y", "medium",
               "Document should have one main landmark",
               "The document does not have a main landmark.",
               "Wrap primary content in a <main> element.",
               selector="div.container",
               bbox=BoundingBox(x=40, y=130, width=920, height=600),
               html='<div class="container" style="...">…</div>',
               meta={"axe_rule": "landmark-one-main"}),
        _issue("demo-example", url, "a11y", "medium",
               "All page content should be contained by landmarks",
               "Some page content is not contained by landmarks.",
               "Use header/main/footer landmarks.",
               meta={"axe_rule": "region"}),
        _issue("demo-example", url, "seo", "high", "Missing meta description",
               'No <meta name="description"> tag found.',
               "Add a 120-160 character meta description."),
        _issue("demo-example", url, "seo", "info", "No canonical link",
               "Add <link rel=canonical> to avoid duplicate-content issues."),
        _issue("demo-example", url, "seo", "info", "Missing Open Graph tags",
               "Add og:title/og:description/og:image for better social sharing."),
        _issue("demo-example", url, "security", "medium",
               "Missing Content-Security-Policy header",
               "CSP mitigates XSS and injection attacks.",
               "Add a Content-Security-Policy response header."),
        _issue("demo-example", url, "security", "medium",
               "Missing Strict-Transport-Security (HSTS) header",
               "Add Strict-Transport-Security: max-age=31536000; includeSubDomains"),
        _issue("demo-example", url, "security", "low",
               "Missing X-Content-Type-Options header",
               "Add X-Content-Type-Options: nosniff"),
        _issue("demo-example", url, "security", "low",
               "Missing clickjacking protection",
               "Add X-Frame-Options: DENY or a CSP frame-ancestors directive."),
        _issue("demo-example", url, "security", "low",
               "Missing Referrer-Policy header",
               "Add Referrer-Policy: strict-origin-when-cross-origin"),
        _issue("demo-example", url, "security", "info",
               "Missing Permissions-Policy header",
               "Declare which browser features the site uses."),
    ]
    _build_completed("demo-example", url, "example", "#0ea5e9",
                     26, [page], issues, "Example Domain")


def _build_demo_shop() -> None:
    """https://shop.example.com — a product store with typical issues."""
    home = "https://shop.example.com/"
    products = "https://shop.example.com/products"
    pages = [
        PageResult(url=home, status=200, title="Example Store — Home",
                   console_errors=1, failed_requests=2,
                   metrics=_metrics(ttfb=1400, fcp=2100, lcp=3900, cls=0.31,
                                    nodes=980, reqs=86, kb=6120)),
        PageResult(url=products, status=200, title="Products — Example Store",
                   console_errors=0, failed_requests=1,
                   metrics=_metrics(ttfb=900, fcp=1400, lcp=2100, cls=0.08,
                                    nodes=760, reqs=64, kb=3310)),
    ]
    issues = [
        _issue("demo-shop", home, "functional", "low",
               'Link uses a "javascript:" URL',
               'An "Add to cart" control uses a javascript: href.',
               "Use a real URL or a <button> with an event listener.",
               selector="button.quick-add",
               bbox=BoundingBox(x=770, y=884, width=190, height=46),
               html='<button class="quick-add" onclick="addToCart(this)">Add</button>'),
        _issue("demo-shop", home, "network", "medium",
               "HTTP 503: https://shop.example.com/api/recommendations",
               "A sub-resource returned an error status.",
               "Fix the failing API endpoint.",
               meta={"url": "https://shop.example.com/api/recommendations",
                     "status": 503}),
        _issue("demo-shop", home, "a11y", "medium",
               "Images must have alternate text (node 1)",
               "The image does not have an alt attribute.",
               "Add meaningful alt text or alt=\"\" for decorative images.",
               selector=".product-card img",
               bbox=BoundingBox(x=320, y=374, width=188, height=64),
               html='<img class="product-card" src="/img/tshirt.webp">',
               meta={"axe_rule": "image-alt", "impact": "serious"}),
        _issue("demo-shop", home, "security", "medium",
               "Missing Content-Security-Policy header",
               "CSP mitigates XSS and injection attacks.",
               "Add a Content-Security-Policy response header."),
        _issue("demo-shop", home, "security", "low",
               'Cookie "session" has no SameSite attribute',
               "Set SameSite=Lax or Strict.",
               meta={"cookie": "session"}),
        _issue("demo-shop", home, "performance", "medium",
               "High cumulative layout shift (CLS 0.31)",
               "Elements move around while the page loads.",
               "Set explicit width/height on media and reserve space.",
               meta={"metric": 0.31}),
        _issue("demo-shop", home, "performance", "high",
               "Slow Largest Contentful Paint (3900 ms)",
               "The main content took long to become visible.",
               "Optimize the largest image; use lazy-loading and modern formats.",
               meta={"metric": 3900}),
    ]
    _build_completed("demo-shop", home, "shop", "#f59e0b",
                     3, pages, issues, "Example Store")


def _build_demo_blog() -> None:
    """https://blog.example.org — healthy site with minor polish items."""
    home = "https://blog.example.org/"
    post = "https://blog.example.org/posts/hello-world"
    pages = [
        PageResult(url=home, status=200, title="Example Blog — Notes on the web",
                   console_errors=0, failed_requests=0,
                   metrics=_metrics(ttfb=320, fcp=740, lcp=900, cls=0.02,
                                    nodes=520, reqs=118, kb=2210)),
        PageResult(url=post, status=200, title="Hello World — Example Blog",
                   console_errors=0, failed_requests=0,
                   metrics=_metrics(ttfb=300, fcp=680, lcp=860, cls=0.01,
                                    nodes=380, reqs=52, kb=1480)),
    ]
    issues = [
        _issue("demo-blog", home, "seo", "info",
               "Meta description is long (174 chars)",
               "Keep descriptions at 120-160 characters.",
               meta={"chars": 174}),
        _issue("demo-blog", home, "security", "info",
               "Missing Permissions-Policy header",
               "Declare which browser features the site uses."),
        _issue("demo-blog", home, "performance", "info",
               "Many requests: 118",
               "Bundle assets and use HTTP/2 multiplexing.",
               meta={"requests": 118}),
        _issue("demo-blog", post, "a11y", "medium",
               "Heading levels should only increase by one",
               "Heading order should not skip levels.",
               "Nest headings sequentially (h1, h2, h3…).",
               meta={"axe_rule": "heading-order"}),
    ]
    _build_completed("demo-blog", home, "blog", "#10b981",
                     50, pages, issues, "Example Blog")


def seed_demo_data() -> None:
    """Build the demo runs. Called on app startup (fresh in-memory store)."""
    if not settings.runs_dir.exists():
        return
    _build_demo_example()
    _build_demo_shop()
    _build_demo_blog()
    _cancelled_run()