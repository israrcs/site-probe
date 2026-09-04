from __future__ import annotations

import logging
from typing import List

from playwright.async_api import Page

from . import ELEMENT_INFO_JS, EngineContext

log = logging.getLogger("siteprobe.seo")

SEO_JS = """() => {
  const q = s => document.querySelector(s);
  const title = document.title || '';
  const descMeta = q('meta[name="description"]');
  const desc = descMeta ? (descMeta.getAttribute('content') || '') : null;
  const canonicals = Array.from(document.querySelectorAll('link[rel="canonical"]')).map(l => l.href);
  const viewportMeta = !!q('meta[name="viewport"]');
  const lang = document.documentElement.getAttribute('lang');
  const robotsEl = q('meta[name="robots"]');
  const robotsMeta = robotsEl ? (robotsEl.getAttribute('content') || '') : null;
  const ogTitle = !!q('meta[property="og:title"]');
  const h1s = document.querySelectorAll('h1').length;
  const levels = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6'))
    .map(h => parseInt(h.tagName[1], 10));
  const imgsNoAlt = Array.from(document.images).filter(i => !i.hasAttribute('alt'));
  const favicon = !!q('link[rel~="icon"]');
  return {
    title: title, titleLen: title.length,
    desc: desc, descLen: desc ? desc.length : 0,
    canonicals: canonicals, viewportMeta: viewportMeta, lang: lang,
    robotsMeta: robotsMeta, ogTitle: ogTitle, h1s: h1s, levels: levels,
    imgsNoAltCount: imgsNoAlt.length,
    imgSample: imgsNoAlt.slice(0, 1).map(el => (__SP_EL__)(el)),
    favicon: favicon
  };
}""".replace("__SP_EL__", ELEMENT_INFO_JS)


async def run(page: Page, ctx: EngineContext) -> List:
    try:
        d = await page.evaluate(SEO_JS)
    except Exception:
        return []

    issues: List = []
    add = ctx.new_issue

    title = d.get("title") or ""
    if not title.strip():
        issues.append(add(category="seo", severity="high",
                          title="Missing page title",
                          description="The page has no <title> or it is empty.",
                          suggestion="Add a unique, descriptive <title> (50-60 chars)."))
    elif d["titleLen"] > 60:
        issues.append(add(category="seo", severity="info",
                          title=f"Page title is long ({d['titleLen']} chars)",
                          description=f'"{title[:140]}"',
                          suggestion="Keep titles under 60 characters so they are not "
                          "truncated in search results."))

    desc = d.get("desc")
    if desc is None:
        issues.append(add(category="seo", severity="high",
                          title="Missing meta description",
                          description='No <meta name="description"> tag found.',
                          suggestion="Add a 120-160 character meta description."))
    elif d["descLen"] > 160:
        issues.append(add(category="seo", severity="info",
                          title=f"Meta description is long ({d['descLen']} chars)",
                          suggestion="Keep descriptions at 120-160 characters."))

    if d.get("h1s", 0) != 1:
        issues.append(add(category="seo", severity="medium",
                          title=f"Expected exactly one <h1>, found {d.get('h1s')}",
                          description="Search engines use the h1 to understand the "
                          "main topic of a page.",
                          suggestion="Use a single h1 and structure the rest with "
                          "h2/h3."))

    levels = d.get("levels") or []
    for prev, cur in zip(levels, levels[1:]):
        if cur > prev + 1:
            issues.append(add(category="seo", severity="low",
                              title=f"Heading level skipped (h{prev} -> h{cur})",
                              description="Heading order should not skip levels.",
                              suggestion="Nest headings sequentially (h1, h2, h3…)."))
            break

    if d.get("imgsNoAltCount"):
        sample = (d.get("imgSample") or [{}])[0]
        issues.append(add(
            category="seo", severity="medium",
            title=f"{d['imgsNoAltCount']} image(s) missing alt attributes",
            description="Alt text is required for accessibility and image search.",
            suggestion='Add meaningful alt text (or alt="" for decorative images).',
            selector=sample.get("selector"), html_snippet=sample.get("html"),
            bounding_box=sample.get("box"),
            metadata={"count": d["imgsNoAltCount"]},
        ))

    canonicals = d.get("canonicals") or []
    if len(canonicals) == 0:
        issues.append(add(category="seo", severity="info",
                          title="No canonical link",
                          suggestion="Add <link rel=canonical> to avoid duplicate-"
                          "content issues."))
    elif len(canonicals) > 1:
        issues.append(add(category="seo", severity="medium",
                          title=f"{len(canonicals)} canonical links found",
                          description="Multiple canonicals confuse crawlers.",
                          metadata={"canonicals": canonicals[:5]}))

    if not d.get("viewportMeta"):
        issues.append(add(category="seo", severity="medium",
                          title="Missing viewport meta tag",
                          description="Without <meta name=viewport> the page renders "
                          "poorly on mobile and fails mobile-friendly checks.",
                          suggestion='Add <meta name="viewport" content="width=device-'
                          'width, initial-scale=1">.'))

    if not d.get("lang"):
        issues.append(add(category="seo", severity="low",
                          title="Missing lang attribute on <html>",
                          suggestion='Add e.g. <html lang="en">.'))

    if d.get("robotsMeta") and "noindex" in d["robotsMeta"].lower():
        issues.append(add(category="seo", severity="info",
                          title="Page is marked noindex",
                          description=f'meta robots: "{d["robotsMeta"]}"',
                          suggestion="Remove noindex if this page should appear in "
                          "search engines."))

    if not d.get("ogTitle"):
        issues.append(add(category="seo", severity="info",
                          title="Missing Open Graph tags",
                          suggestion="Add og:title/og:description/og:image for better "
                          "social sharing."))
    if not d.get("favicon"):
        issues.append(add(category="seo", severity="info",
                          title="No favicon link found"))

    return issues
