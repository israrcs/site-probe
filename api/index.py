from __future__ import annotations

import logging
import os
import sys

# Make the server directory importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import routes_runs
from app.core.config import settings
from app.seed import seed_demo_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)


# Vercel Functions don't support lifespan hooks reliably; seed at import time
try:
    seed_demo_data()
    logging.getLogger("siteprobe.seed").info(
        "seeded demo runs into the in-memory store")
except Exception as exc:  # noqa: BLE001
    logging.getLogger("siteprobe.seed").warning(
        "demo seeding failed: %s", exc)


app = FastAPI(title="SiteProbe API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_runs.router)

# Serve scan artifacts (screenshots, reports) if the directory exists
_runs_dir = str(settings.runs_dir)
if os.path.isdir(_runs_dir):
    app.mount(
        "/artifacts",
        StaticFiles(directory=_runs_dir, html=True),
        name="artifacts",
    )


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "service": "siteprobe", "version": app.version}
