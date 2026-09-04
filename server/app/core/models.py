from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Viewport(str, Enum):
    desktop = "desktop"
    tablet = "tablet"
    mobile = "mobile"


VIEWPORT_SIZES: Dict[str, Dict[str, int]] = {
    "desktop": {"width": 1280, "height": 800},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 390, "height": 844},
}


class Category(str, Enum):
    functional = "functional"
    console = "console"
    network = "network"
    a11y = "a11y"
    seo = "seo"
    security = "security"
    performance = "performance"


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


SEVERITY_WEIGHT: Dict[str, int] = {
    "critical": 25,
    "high": 12,
    "medium": 6,
    "low": 2,
    "info": 0,
}


class RunOptions(BaseModel):
    url: str
    max_pages: int = Field(default=10, ge=1, le=500)
    viewports: List[Viewport] = Field(default_factory=lambda: [Viewport.desktop])
    engines: List[Category] = Field(default_factory=lambda: list(Category))
    follow_robots: bool = False  # unrestricted scanning by default
    delay_ms: int = Field(default=0, ge=0, le=10000)
    timeout_ms: int = Field(default=60000, ge=5000, le=180000)
    user_agent: Optional[str] = None


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class Issue(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    run_id: str = ""
    page_url: str = ""
    category: Category
    severity: Severity
    title: str
    description: str = ""
    suggestion: str = ""
    selector: Optional[str] = None
    html_snippet: Optional[str] = None
    bounding_box: Optional[BoundingBox] = None
    # relative paths inside the run directory: {"annotated": ..., "element": ..., "fullPage": ...}
    screenshot: Dict[str, str] = Field(default_factory=dict)
    viewport: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PageResult(BaseModel):
    url: str
    final_url: Optional[str] = None  # after redirects (detects login walls)
    status: Optional[int] = None
    title: Optional[str] = None
    screenshots: Dict[str, str] = Field(default_factory=dict)  # viewport -> rel path
    console_errors: int = 0
    failed_requests: int = 0
    metrics: Dict[str, Any] = Field(default_factory=dict)


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


TERMINAL_STATUSES = {RunStatus.completed, RunStatus.failed, RunStatus.cancelled}


class Run(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    options: RunOptions
    status: RunStatus = RunStatus.queued
    phase: str = "queued"
    pages_done: int = 0
    pages_total: int = 0
    current_url: Optional[str] = None
    issues: List[Issue] = Field(default_factory=list)
    pages: List[PageResult] = Field(default_factory=list)
    scores: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    is_demo: bool = False  # seeded demo data (never affects real scans)
    created_at: float = Field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    def issue_counts(self) -> Dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for issue in self.issues:
            counts[issue.severity.value] += 1
        return counts


class ProgressEvent(BaseModel):
    run_id: str
    status: RunStatus
    phase: str
    pages_done: int = 0
    pages_total: int = 0
    current_url: Optional[str] = None
    issue_count: int = 0
