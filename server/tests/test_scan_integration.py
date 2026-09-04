"""End-to-end scan against a deliberately broken local fixture site."""

import asyncio
import socket
import subprocess
import sys
import time
import urllib.request
from functools import lru_cache

import pytest

from app.core.config import settings
from app.core.models import Run, RunOptions
from app.services.runner import Runner

FIXTURES = Path = __import__("pathlib").Path(__file__).parent / "fixture_site"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def fixture_server():
    # generate a 4 MB asset so the performance engine raises a "heavy page"
    # issue (fetched via JS: browsers abort early on invalid image payloads)
    big_asset = FIXTURES / "big.bin"
    big_asset.write_bytes(b"0" * (4 * 1024 * 1024))

    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port),
         "--bind", "127.0.0.1", "--directory", str(FIXTURES)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "/index.html", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    yield base
    proc.terminate()
    proc.wait(timeout=5)
    big_asset.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def scan(fixture_server):
    base = fixture_server
    opts = RunOptions(
        url=base + "/index.html",
        max_pages=3,
        viewports=["desktop", "mobile"],
        delay_ms=0,
        timeout_ms=15000,
    )
    run = Run(options=opts)
    asyncio.run(Runner(run).execute())
    return run


def test_run_completed(scan):
    assert scan.status.value == "completed", scan.error
    assert scan.pages_done == 3
    assert scan.pages_total >= 3


def test_all_engine_categories_reported(scan):
    cats = {i.category.value for i in scan.issues}
    assert {"functional", "console", "network", "a11y", "seo",
            "security", "performance"} <= cats


def test_specific_issues_found(scan):
    titles = [i.title for i in scan.issues]
    assert any("Broken image" in t for t in titles)
    assert any(t.startswith("Console error") for t in titles)
    assert any("Unhandled JavaScript exception" in t for t in titles)
    assert any("HTTP 404" in t for t in titles)
    assert any("Page returned HTTP 404" in t for t in titles)
    assert any("Missing meta description" in t for t in titles)
    assert any("exactly one <h1>" in t for t in titles)
    assert any("Duplicate page title" in t for t in titles)
    assert any("Missing Content-Security-Policy" in t for t in titles)
    assert any("Missing viewport meta tag" in t for t in titles)
    assert any("Horizontal overflow" in t for t in titles)
    assert any('Broken in-page anchor "#nonexistent-fragment"' in t
               for t in titles)
    assert any('"javascript:" URL' in t for t in titles)
    assert any("Broken external link" in t for t in titles)
    assert any("alt" in t and "missing" in t.lower() for t in titles)


def test_performance_metrics_recorded(scan):
    home = [p for p in scan.pages if p.url.endswith("index.html")]
    assert home, "home page result missing"
    metrics = home[0].metrics
    assert "ttfb" in metrics and metrics["ttfb"] is not None
    assert "domNodes" in metrics


def test_scores_computed(scan):
    assert 0 <= scan.scores.get("overall", -1) <= 100
    assert scan.scores.get("grade") in list("ABCDF")
    assert "a11y" in scan.scores.get("categories", {})


def test_screenshots_and_annotations_on_disk(scan):
    run_dir = settings.runs_dir / scan.id
    full_pages = list((run_dir / "screenshots").rglob("fullpage.png"))
    # 3 pages x 2 viewports (the 404 ghost page still renders a 404 page)
    assert len(full_pages) >= 6, f"expected >=6 fullpage shots, got {len(full_pages)}"

    annotated = [i for i in scan.issues if i.screenshot.get("annotated")]
    assert annotated, "expected at least one annotated issue screenshot"
    for issue in annotated[:3]:
        assert (run_dir / issue.screenshot["annotated"]).exists()
        assert (run_dir / issue.screenshot["element"]).exists()


def test_report_artifacts(scan):
    run_dir = settings.runs_dir / scan.id
    assert (run_dir / "report.json").exists()
    assert (run_dir / "report.html").exists()
    assert (run_dir / "site-report.zip").exists()
    html = (run_dir / "report.html").read_text(encoding="utf-8")
    assert "SiteProbe report" in html
