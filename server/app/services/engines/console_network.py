from __future__ import annotations

import logging
from typing import List

from playwright.async_api import Page

from . import EngineContext, issue_count_cap, short_url

log = logging.getLogger("siteprobe.console_network")


async def run(page: Page, ctx: EngineContext) -> List:
    """Turn the buffered console/network listener data into Issues.

    The runner attaches the listeners before navigation; this engine only
    transforms the captured buffers."""
    issues: List = []
    cap = ctx.capture

    # Unhandled exceptions in page JS
    for err in cap.get("pageerrors", [])[:10]:
        issues.append(ctx.new_issue(
            category="console", severity="critical",
            title="Unhandled JavaScript exception",
            description=str(err)[:600],
            suggestion="Fix the exception thrown while the page was loading; it can "
            "break interactive features.",
            metadata={"type": "pageerror"},
        ))

    # console.error / console.warning
    for m in cap.get("console", [])[:15]:
        sev = "high" if m.get("type") == "error" else "low"
        issues.append(ctx.new_issue(
            category="console", severity=sev,
            title=f'Console {m.get("type")}: {short_url(m.get("text", ""), 100)}',
            description=m.get("text", ""),
            suggestion="Resolve the browser console message; errors often indicate "
            "broken functionality.",
            metadata={"source": m.get("location", "")},
        ))

    # Requests that never completed (DNS, refused, aborted, TLS…)
    for f in cap.get("failed", [])[:15]:
        issues.append(ctx.new_issue(
            category="network", severity="high",
            title=f'Request failed: {f.get("method", "GET")} {short_url(f.get("url", ""))}',
            description=f"The request did not complete ({f.get('failure')}).",
            suggestion="Check the resource URL, DNS, TLS certificate and server logs.",
            metadata={"url": f.get("url"), "failure": str(f.get("failure"))},
        ))

    # HTTP error responses
    for r in cap.get("responses", [])[:20]:
        sev = "high" if r["status"] >= 500 else "medium"
        issues.append(ctx.new_issue(
            category="network", severity=sev,
            title=f'HTTP {r["status"]}: {short_url(r.get("url", ""))}',
            description="A sub-resource or navigation request returned an error status.",
            suggestion="Fix or remove the failing request.",
            metadata={"url": r.get("url"), "status": r.get("status")},
        ))

    return issue_count_cap(issues, 40, "console/network issues")
