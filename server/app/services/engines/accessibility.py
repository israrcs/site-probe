from __future__ import annotations

import logging
import re
from typing import List

from playwright.async_api import Error as PWError
from playwright.async_api import Page

from app.core.config import settings

from . import ELEMENT_INFO_JS, EngineContext, issue_count_cap

log = logging.getLogger("siteprobe.a11y")

AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"]
IMPACT_TO_SEVERITY = {
    "critical": "critical",
    "serious": "high",
    "moderate": "medium",
    "minor": "low",
}

# Fake same-origin path we serve axe-core from. Strict CSP (script-src 'self')
# blocks inline <script> injection, but same-origin scripts pass the check.
AXE_ROUTE_PATH = "/__siteprobe__/axe.min.js"


async def _inject_axe(page: Page) -> bool:
    """Load axe-core even on CSP-protected pages.

    Registers a Playwright route that fulfills a same-origin fake URL with the
    vendored axe.min.js, then tags it into the page. Falls back to a plain
    inline tag for pages whose CSP allows inline scripts. Returns whether
    window.axe became available."""

    async def _serve(route):
        await route.fulfill(path=str(settings.axe_path),
                            content_type="application/javascript")

    try:
        await page.route("**" + AXE_ROUTE_PATH, _serve)
    except Exception:
        pass

    match = re.match(r"(https?://[^/]+)", page.url or "")
    if match:
        try:
            await page.add_script_tag(url=match.group(1) + AXE_ROUTE_PATH)
        except Exception:
            pass
        try:
            if await page.evaluate("typeof window.axe !== 'undefined'"):
                return True
        except Exception:
            pass

    # fallback: plain inline injection (works when CSP allows inline scripts)
    try:
        await page.add_script_tag(path=str(settings.axe_path))
        return bool(await page.evaluate("typeof window.axe !== 'undefined'"))
    except Exception:
        return False

AXE_RUN_JS = """async (tags) => {
  if (!window.axe) return null;
  const r = await axe.run(document, {
    runOnly: { type: 'tag', values: tags },
    resultTypes: ['violations']
  });
  return r.violations.map(v => ({
    id: v.id, impact: v.impact, help: v.help,
    description: v.description, helpUrl: v.helpUrl,
    nodes: v.nodes.slice(0, 4).map(n => {
      let info = null;
      try { info = n.element ? window.__spDescribe(n.element) : null; }
      catch (e) { info = null; }
      return {
        target: n.target,
        html: (n.html || '').slice(0, 400),
        summary: n.failureSummary || '',
        info: info
      };
    })
  }));
}"""


async def run(page: Page, ctx: EngineContext) -> List:
    issues: List = []

    try:
        await page.evaluate("window.__spDescribe = " + ELEMENT_INFO_JS)
        injected = await _inject_axe(page)
        if not injected:
            return [ctx.new_issue(
                category="a11y", severity="info",
                title="Accessibility scan skipped (engine blocked by page CSP)",
                description="The page's Content-Security-Policy prevented the "
                "axe-core engine from loading, even via same-origin injection.",
                suggestion="Only the accessibility engine is affected; all "
                "other engines ran normally.")]
        violations = await page.evaluate(AXE_RUN_JS, AXE_TAGS)
    except PWError as exc:
        log.warning("axe scan failed on %s: %s", ctx.page_url, exc)
        return [ctx.new_issue(
            category="a11y", severity="info",
            title="Accessibility scan could not complete on this page",
            description=str(exc)[:400],
            suggestion="Usually caused by a navigation/timeout during the scan; "
            "re-run the test.",
        )]

    if violations is None:
        return [ctx.new_issue(
            category="a11y", severity="info",
            title="Accessibility scan skipped (axe-core did not initialise)",
        )]

    for v in violations:
        sev = IMPACT_TO_SEVERITY.get(v.get("impact") or "", "medium")
        nodes = v.get("nodes") or []
        for idx, node in enumerate(nodes):
            info = node.get("info") or {}
            target = node.get("target") or []
            sel = target[0] if target else info.get("selector")
            suffix = f" (node {idx + 1})" if len(nodes) > 1 else ""
            issues.append(ctx.new_issue(
                category="a11y", severity=sev,
                title=f"{v.get('help', 'Accessibility issue')}{suffix}",
                description=node.get("summary") or v.get("description") or "",
                suggestion=f"How to fix: {v.get('helpUrl', 'see WCAG guidance')}",
                selector=sel,
                html_snippet=info.get("html") or node.get("html"),
                bounding_box=info.get("box"),
                metadata={
                    "axe_rule": v.get("id"),
                    "impact": v.get("impact"),
                    "help_url": v.get("helpUrl"),
                    "target": target,
                },
            ))

    return issue_count_cap(issues, 40, "accessibility violations")
