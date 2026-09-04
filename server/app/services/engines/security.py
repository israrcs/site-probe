from __future__ import annotations

import logging
import re
from typing import List

from playwright.async_api import Page

from . import EngineContext, short_url

log = logging.getLogger("siteprobe.security")


async def run(page: Page, ctx: EngineContext) -> List:
    issues: List = []
    add = ctx.new_issue
    raw_headers = ctx.capture.get("headers")
    has_headers = bool(raw_headers)
    headers = {k.lower(): v for k, v in (raw_headers or {}).items()}
    is_https = ctx.page_url.lower().startswith("https://")
    csp = headers.get("content-security-policy")

    if not is_https:
        issues.append(add(
            category="security", severity="critical",
            title="Page is served over plain HTTP",
            description="Traffic (including passwords and cookies) is not encrypted.",
            suggestion="Serve the site over HTTPS and redirect HTTP -> HTTPS.",
            metadata={"url": ctx.page_url},
        ))
    else:
        mixed = [u for u in ctx.capture.get("request_urls", [])
                 if u.lower().startswith("http://")][:5]
        if mixed:
            issues.append(add(
                category="security", severity="high",
                title="Mixed content: insecure HTTP resources on an HTTPS page",
                description="Browsers block or degrade these requests: "
                + "; ".join(short_url(u, 80) for u in mixed),
                suggestion="Load every resource over HTTPS.",
                metadata={"examples": mixed},
            ))

    if not has_headers:
        issues.append(add(
            category="security", severity="info",
            title="Response-header checks skipped",
            description="The page took too long to load, so its response headers "
            "were not captured and could not be audited for this pass.",
        ))

    if has_headers:
        if not csp:
            issues.append(add(
                category="security", severity="medium",
                title="Missing Content-Security-Policy header",
                description="CSP mitigates XSS and injection attacks.",
                suggestion="Add a Content-Security-Policy response header.",
            ))
        if is_https and not headers.get("strict-transport-security"):
            issues.append(add(
                category="security", severity="medium",
                title="Missing Strict-Transport-Security (HSTS) header",
                suggestion="Add Strict-Transport-Security: max-age=31536000; includeSubDomains",
            ))
        if not headers.get("x-content-type-options"):
            issues.append(add(
                category="security", severity="low",
                title="Missing X-Content-Type-Options header",
                suggestion="Add X-Content-Type-Options: nosniff",
            ))
        if not (headers.get("x-frame-options") or (csp and "frame-ancestors" in csp)):
            issues.append(add(
                category="security", severity="low",
                title="Missing clickjacking protection",
                description="Neither X-Frame-Options nor CSP frame-ancestors is set.",
                suggestion="Add X-Frame-Options: DENY or a CSP frame-ancestors directive.",
            ))
        if not headers.get("referrer-policy"):
            issues.append(add(
                category="security", severity="low",
                title="Missing Referrer-Policy header",
                suggestion="Add Referrer-Policy: strict-origin-when-cross-origin",
            ))
        if not headers.get("permissions-policy"):
            issues.append(add(
                category="security", severity="info",
                title="Missing Permissions-Policy header",
                suggestion="Declare which browser features the site uses.",
            ))

        server = headers.get("server", "")
        if server and re.search(r"\d+\.\d+", server):
            issues.append(add(
                category="security", severity="info",
                title=f'Server version disclosure: "{server}"',
                suggestion="Remove version numbers from the Server header.",
            ))

    try:
        cookies = await page.context.cookies(ctx.page_url)
    except Exception:
        cookies = []
    for c in cookies:
        name = c.get("name", "?")
        if is_https and not c.get("secure"):
            issues.append(add(
                category="security", severity="medium",
                title=f'Cookie "{name}" lacks the Secure flag',
                suggestion="Set Secure on all cookies over HTTPS.",
                metadata={"cookie": name},
            ))
        if not c.get("httpOnly"):
            issues.append(add(
                category="security", severity="low",
                title=f'Cookie "{name}" is not HttpOnly',
                description="The cookie is readable by JavaScript (XSS risk).",
                metadata={"cookie": name},
            ))
        if not c.get("sameSite"):
            issues.append(add(
                category="security", severity="low",
                title=f'Cookie "{name}" has no SameSite attribute',
                suggestion="Set SameSite=Lax or Strict.",
                metadata={"cookie": name},
            ))

    return issues
