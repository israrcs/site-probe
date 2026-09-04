from __future__ import annotations

import logging
from typing import List

from playwright.async_api import Page

from . import EngineContext, short_url

log = logging.getLogger("siteprobe.performance")

# Injected before any page script runs, so LCP/CLS observe everything.
PERF_INIT_JS = """() => {
  window.__siteprobe = { lcp: null, cls: 0 };
  try {
    new PerformanceObserver(list => {
      const entries = list.getEntries();
      if (entries.length) window.__siteprobe.lcp = entries[entries.length - 1].startTime;
    }).observe({ type: 'largest-contentful-paint', buffered: true });
    new PerformanceObserver(list => {
      for (const e of list.getEntries()) {
        if (!e.hadRecentInput) window.__siteprobe.cls += e.value;
      }
    }).observe({ type: 'layout-shift', buffered: true });
  } catch (e) { /* older browsers */ }
}"""

METRICS_JS = """async () => {
  const nav = performance.getEntriesByType('navigation')[0];
  const fcpEntry = performance.getEntriesByType('paint')
    .find(p => p.name === 'first-contentful-paint');
  const res = performance.getEntriesByType('resource');
  const transfer = res.reduce((a, r) => a + (r.transferSize || 0), 0);
  const slowest = res.slice().sort((a, b) => b.duration - a.duration).slice(0, 5)
    .map(r => ({
      url: r.name.length > 140 ? r.name.slice(0, 139) + '…' : r.name,
      ms: Math.round(r.duration),
      kb: Math.round((r.transferSize || 0) / 1024)
    }));
  const sp = window.__siteprobe || {};
  return {
    ttfb: nav ? Math.round(nav.responseStart) : null,
    domInteractive: nav ? Math.round(nav.domInteractive) : null,
    load: (nav && nav.loadEventEnd > 0) ? Math.round(nav.loadEventEnd) : null,
    fcp: fcpEntry ? Math.round(fcpEntry.startTime) : null,
    lcp: sp.lcp != null ? Math.round(sp.lcp) : null,
    cls: Math.round((sp.cls || 0) * 1000) / 1000,
    domNodes: document.getElementsByTagName('*').length,
    requests: res.length,
    transferKB: Math.round(transfer / 1024),
    slowest: slowest
  };
}"""


async def run(page: Page, ctx: EngineContext) -> List:
    try:
        m = await page.evaluate(METRICS_JS)
    except Exception as exc:
        log.warning("metrics failed on %s: %s", ctx.page_url, exc)
        return []
    ctx.extra["metrics"] = m

    issues: List = []
    add = ctx.new_issue
    meta = lambda key: {"metric": m.get(key)}  # noqa: E731

    ttfb = m.get("ttfb")
    if ttfb is not None and ttfb > 800:
        issues.append(add(
            category="performance",
            severity="high" if ttfb > 2000 else "medium",
            title=f"Slow Time to First Byte ({ttfb} ms)",
            description="The server took long to respond with the first byte.",
            suggestion="Add caching/CDN or optimize server response time.",
            metadata=meta("ttfb"),
        ))

    fcp = m.get("fcp")
    if fcp is not None and fcp > 1800:
        issues.append(add(
            category="performance",
            severity="high" if fcp > 3000 else "medium",
            title=f"Slow First Contentful Paint ({fcp} ms)",
            suggestion="Reduce render-blocking CSS/JS and preload critical assets.",
            metadata=meta("fcp"),
        ))

    lcp = m.get("lcp")
    if lcp is not None and lcp > 2500:
        issues.append(add(
            category="performance",
            severity="high" if lcp > 4000 else "medium",
            title=f"Slow Largest Contentful Paint ({lcp} ms)",
            description="The main content took long to become visible.",
            suggestion="Optimize the largest image/element; use lazy-loading and "
            "modern image formats.",
            metadata=meta("lcp"),
        ))

    cls = m.get("cls")
    if cls is not None and cls > 0.1:
        issues.append(add(
            category="performance",
            severity="high" if cls > 0.25 else "medium",
            title=f"High cumulative layout shift (CLS {cls})",
            description="Elements move around while the page loads.",
            suggestion="Set explicit width/height on media and reserve space for "
            "late-loading content.",
            metadata=meta("cls"),
        ))

    kb = m.get("transferKB") or 0
    if kb > 3072:
        issues.append(add(
            category="performance",
            severity="high" if kb > 6144 else "medium",
            title=f"Heavy page: {kb // 1024} MB transferred",
            suggestion="Compress/optimize images and scripts; enable text compression.",
            metadata=meta("transferKB"),
        ))

    if (m.get("domNodes") or 0) > 1500:
        issues.append(add(
            category="performance", severity="low",
            title=f"Large DOM: {m['domNodes']} elements",
            suggestion="Reduce DOM complexity for better runtime performance.",
            metadata=meta("domNodes"),
        ))

    if (m.get("requests") or 0) > 100:
        issues.append(add(
            category="performance", severity="low",
            title=f"Many requests: {m['requests']}",
            suggestion="Bundle assets and use HTTP/2 multiplexing.",
            metadata=meta("requests"),
        ))

    return issues
