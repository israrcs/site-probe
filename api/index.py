"""SiteProbe API for Vercel serverless deployment.

Serves the dashboard API (runs, issues, reports, demo data) without importing
Playwright or the scan runner — browser binaries are too large for the 225 MB
Vercel function limit and headless Chromium doesn't work in serverless.

Real scans run locally or in Docker (see Dockerfile); this deployment serves
the dashboard with demo data and any persisted report artifacts.
"""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from pathlib import Path

# Make the server directory importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.models import (
    Run,
    RunOptions,
    RunStatus,
    TERMINAL_STATUSES,
)
from app.seed import seed_demo_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)

# Seed demo data at import time (Vercel functions don't support lifespan hooks)
try:
    seed_demo_data()
    logging.getLogger("siteprobe.seed").info(
        "seeded demo runs into the in-memory store")
except Exception as exc:  # noqa: BLE001
    logging.getLogger("siteprobe.seed").warning(
        "demo seeding failed: %s", exc)

# Import the in-memory store (shares state with demo seeding)
from app.core.store import store  # noqa: E402

app = FastAPI(title="SiteProbe API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _summary(run: Run) -> dict:
    end = run.finished_at or (time.time() if run.started_at else None)
    duration = (round(end - run.started_at, 1)
                if run.started_at and end else None)
    return {
        "id": run.id,
        "url": run.options.url,
        "status": run.status.value,
        "phase": run.phase,
        "pages_done": run.pages_done,
        "pages_total": run.pages_total,
        "issue_counts": run.issue_counts(),
        "total_issues": len(run.issues),
        "overall_score": run.scores.get("overall"),
        "grade": run.scores.get("grade"),
        "created_at": run.created_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "duration_s": duration,
        "error": run.error,
        "is_demo": run.is_demo,
    }


def _get_run(run_id: str) -> Run:
    run = store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "service": "siteprobe", "version": app.version}


@app.get("/api/runs")
async def list_runs() -> list:
    return [_summary(r) for r in store.list()]


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    return _get_run(run_id).model_dump()


@app.get("/api/runs/{run_id}/issues")
async def get_issues(
    run_id: str,
    category: str | None = None,
    severity: str | None = None,
    page_url: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    run = _get_run(run_id)
    items = run.issues
    if category:
        items = [i for i in items if i.category.value == category]
    if severity:
        items = [i for i in items if i.severity.value == severity]
    if page_url:
        items = [i for i in items if i.page_url == page_url]
    total = len(items)
    start = max(0, (page - 1) * page_size)
    return {
        "total": total,
        "page": page,
        "items": [i.model_dump() for i in items[start:start + page_size]],
    }


def _report_file(run: Run, name: str):
    path = settings.runs_dir / run.id / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} not ready yet")
    return path


@app.get("/api/runs/{run_id}/report.json")
async def report_json(run_id: str):
    return FileResponse(_report_file(_get_run(run_id), "report.json"),
                        media_type="application/json",
                        filename=f"siteprobe-{run_id}.json")


@app.get("/api/runs/{run_id}/report.html")
async def report_html(run_id: str):
    return FileResponse(_report_file(_get_run(run_id), "report.html"),
                        media_type="text/html",
                        filename=f"siteprobe-{run_id}.html")


@app.get("/api/runs/{run_id}/site-report.zip")
async def report_zip(run_id: str):
    return FileResponse(_report_file(_get_run(run_id), "site-report.zip"),
                        media_type="application/zip",
                        filename=f"siteprobe-{run_id}.zip")


# Serve scan artifacts (screenshots, reports) if the directory exists
_runs_dir = str(settings.runs_dir)
if os.path.isdir(_runs_dir):
    app.mount(
        "/artifacts",
        StaticFiles(directory=_runs_dir, html=True),
        name="artifacts",
    )
