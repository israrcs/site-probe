from __future__ import annotations

import hashlib
import re
from typing import Set
from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    """Add a scheme if missing, lowercase host, strip fragment."""
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    parts = urlsplit(url)
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, "")
    )


def domain_of(url: str) -> str:
    return urlsplit(url).netloc.lower()


def same_site(a: str, b: str) -> bool:
    return domain_of(a) == domain_of(b)


def is_web_url(url: str) -> bool:
    return url.lower().startswith(("http://", "https://"))


def strip_fragment(url: str) -> str:
    return urlunsplit((*urlsplit(url)[:4], ""))


def slug_for_url(url: str, used: Set[str]) -> str:
    """Filesystem-safe unique slug for a URL (used for screenshot folders)."""
    parts = urlsplit(url)
    base = parts.path.strip("/").replace("/", "_") or "index"
    base = re.sub(r"[^A-Za-z0-9_.-]", "_", base)[:60] or "index"
    if parts.query:
        base += "_" + hashlib.md5(parts.query.encode()).hexdigest()[:6]
    slug, i = base, 2
    while slug in used:
        slug = f"{base}_{i}"
        i += 1
    used.add(slug)
    return slug
