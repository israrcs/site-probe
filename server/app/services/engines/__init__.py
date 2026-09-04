"""Test engines. Each engine inspects one page and returns a list of Issues."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

import httpx

from app.core.models import Issue

# --------------------------------------------------------------------------
# Shared JS: describe a DOM element (unique-ish CSS selector, HTML snippet,
# bounding box in *document* coordinates so it aligns with full-page shots).
# --------------------------------------------------------------------------
ELEMENT_INFO_JS = """el => {
  if (!el || el.nodeType !== 1 || typeof el.getBoundingClientRect !== 'function') {
    return { selector: '', html: '', box: null, text: '' };
  }
  const r = el.getBoundingClientRect();
  const segs = [];
  let cur = el;
  while (cur && cur.nodeType === 1 && segs.length < 5) {
    let seg = cur.tagName.toLowerCase();
    if (cur.id) { segs.unshift(seg + '#' + cur.id); break; }
    const parent = cur.parentElement;
    if (parent) {
      const same = Array.from(parent.children).filter(c => c.tagName === cur.tagName);
      if (same.length > 1) {
        seg += ':nth-of-type(' + (Array.prototype.indexOf.call(same, cur) + 1) + ')';
      }
    }
    segs.unshift(seg);
    cur = cur.parentElement;
  }
  return {
    selector: segs.join(' > '),
    html: el.outerHTML ? el.outerHTML.slice(0, 400) : '',
    box: {
      x: Math.round(r.x + window.scrollX),
      y: Math.round(r.y + window.scrollY),
      width: Math.round(r.width),
      height: Math.round(r.height)
    },
    text: (el.textContent || '').trim().slice(0, 120)
  };
}"""


def collect_js(selector: str, cap: int, extra_props: str = "") -> str:
    """Build a JS expression collecting element info for up to `cap` matches."""
    if extra_props:
        mapper = f"el => Object.assign(({ELEMENT_INFO_JS})(el), {{{extra_props}}})"
    else:
        mapper = f"el => ({ELEMENT_INFO_JS})(el)"
    return (
        "([sel, cap]) => Array.from(document.querySelectorAll(sel))"
        f".slice(0, cap).map({mapper})"
    )


def short_url(url: str, max_len: int = 120) -> str:
    return url if len(url) <= max_len else url[: max_len - 1] + "…"


@dataclass
class EngineContext:
    """Everything an engine may need while scanning one page."""

    run_id: str
    page_url: str
    viewport: str
    http: httpx.AsyncClient
    capture: Dict[str, Any]
    new_issue: Callable[..., Issue]
    extra: Dict[str, Any] = field(default_factory=dict)


def issue_count_cap(issues: List[Issue], cap: int, note: str) -> List[Issue]:
    """Trim an issue list to `cap`, appending an informational marker if cut."""
    if len(issues) <= cap:
        return issues
    trimmed = issues[:cap]
    trimmed.append(
        issues[0].model_copy(
            update={
                "id": issues[0].id + "-cap",
                "severity": "info",
                "title": f"Additional issues suppressed ({note})",
                "description": f"More than {cap} issues of this kind were found on "
                "this page; showing the first "
                f"{cap}.",
                "bounding_box": None,
                "selector": None,
                "html_snippet": None,
                "screenshot": {},
            }
        )
    )
    return trimmed
