from __future__ import annotations

import logging
import re
from typing import List, Optional
from urllib.parse import urljoin

import httpx
from urllib.robotparser import RobotFileParser

from app.utils.urls import normalize_url

log = logging.getLogger("siteprobe.crawler")


class Robots:
    """robots.txt wrapper. If the file is missing/unreadable everything is allowed."""

    def __init__(self) -> None:
        self._parser: Optional[RobotFileParser] = None

    @classmethod
    async def load(cls, client: httpx.AsyncClient, base_url: str) -> "Robots":
        self = cls()
        parser = RobotFileParser()
        try:
            resp = await client.get(urljoin(base_url, "/robots.txt"))
            if resp.status_code == 200 and resp.text:
                parser.parse(resp.text.splitlines())
                self._parser = parser
            else:
                log.info("robots.txt not reachable (HTTP %s)", resp.status_code)
        except Exception as exc:
            log.info("robots.txt fetch failed: %s", exc)
        return self

    def allowed(self, url: str) -> bool:
        return self._parser is None or self._parser.can_fetch("*", url)


async def fetch_sitemap_urls(client: httpx.AsyncClient, base_url: str) -> List[str]:
    """Fetch /sitemap.xml and return absolute URLs found in <loc> entries."""
    try:
        resp = await client.get(urljoin(base_url, "/sitemap.xml"), timeout=10)
    except Exception:
        return []
    if resp.status_code != 200:
        return []
    body = resp.text or ""
    if "xml" not in resp.headers.get("content-type", "") and "<urlset" not in body:
        return []
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
    return [normalize_url(loc) for loc in locs if loc.startswith("http")]


async def extract_page_links(page) -> List[str]:
    """All absolute hrefs of anchors on the current page."""
    hrefs: List[str] = await page.evaluate(
        "() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
    )
    return hrefs
