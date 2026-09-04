"""Debug: full scan of an arbitrary URL, dumping statuses + issues."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.models import Run, RunOptions  # noqa: E402
from app.services.runner import Runner  # noqa: E402

URL = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
MAX_PAGES = int(sys.argv[2]) if len(sys.argv) > 2 else 5

run = Run(options=RunOptions(
    url=URL,
    max_pages=MAX_PAGES,
    viewports=["desktop"],
    follow_robots=False,      # scan without restrictions
    timeout_ms=25000,
))
asyncio.run(Runner(run).execute())

print("STATUS:", run.status.value, run.error)
print("PAGES:", run.pages_done, "/", run.pages_total)
for p in run.pages:
    print(f"  [{p.status}] {p.url}  console={p.console_errors} failed={p.failed_requests}")
print("SCORES:", run.scores)
print(f"ISSUES ({len(run.issues)}):")
for i in run.issues:
    print(f"  [{i.severity.value:<8}] {i.category.value:<11} {i.title[:110]}")
