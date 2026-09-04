from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.models import Run, RunOptions, RunStatus
from app.core.store import store
from app.services.runner import Runner
from app.utils.urls import normalize_url

router = APIRouter(prefix="/api/runs", tags=["runs"])


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


@router.post("")
async def start_run(options: RunOptions) -> dict:
    options.url = normalize_url(options.url)
    run = Run(options=options)
    store.add(run)
    task = asyncio.create_task(Runner(run).execute(), name=f"run-{run.id}")
    store.tasks[run.id] = task
    return {"id": run.id, "status": run.status.value}


@router.get("")
async def list_runs() -> list:
    return [_summary(r) for r in store.list()]


@router.get("/{run_id}")
async def get_run(run_id: str) -> dict:
    return _get_run(run_id).model_dump()


@router.get("/{run_id}/issues")
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


@router.delete("/{run_id}")
async def cancel_run(run_id: str) -> dict:
    run = _get_run(run_id)
    task = store.tasks.get(run_id)
    if task and not task.done() and run.status == RunStatus.running:
        task.cancel()
    run.status = RunStatus.cancelled
    run.finished_at = time.time()
    store.broadcast(run)
    return {"id": run_id, "status": run.status.value}


def _report_file(run: Run, name: str):
    path = settings.runs_dir / run.id / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} not ready yet")
    return path


@router.get("/{run_id}/report.json")
async def report_json(run_id: str):
    return FileResponse(_report_file(_get_run(run_id), "report.json"),
                        media_type="application/json",
                        filename=f"siteprobe-{run_id}.json")


@router.get("/{run_id}/report.html")
async def report_html(run_id: str):
    return FileResponse(_report_file(_get_run(run_id), "report.html"),
                        media_type="text/html",
                        filename=f"siteprobe-{run_id}.html")


@router.get("/{run_id}/site-report.zip")
async def report_zip(run_id: str):
    return FileResponse(_report_file(_get_run(run_id), "site-report.zip"),
                        media_type="application/zip",
                        filename=f"siteprobe-{run_id}.zip")
