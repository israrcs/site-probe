from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Set

from .models import Run, ProgressEvent, TERMINAL_STATUSES


class Store:
    """In-memory registry of runs + WebSocket subscriber queues.

    Good enough for a single-process deployment; swap with Redis/BullMQ-style
    backend for horizontal scaling."""

    def __init__(self) -> None:
        self.runs: Dict[str, Run] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}

    def add(self, run: Run) -> None:
        self.runs[run.id] = run

    def get(self, run_id: str) -> Optional[Run]:
        return self.runs.get(run_id)

    def list(self) -> List[Run]:
        return sorted(self.runs.values(), key=lambda r: r.created_at, reverse=True)

    # ----------------------------------------------------------- websocket
    def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self.subscribers.setdefault(run_id, set()).add(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        self.subscribers.get(run_id, set()).discard(q)

    def broadcast(self, run: Run) -> None:
        event = ProgressEvent(
            run_id=run.id,
            status=run.status,
            phase=run.phase,
            pages_done=run.pages_done,
            pages_total=run.pages_total,
            current_url=run.current_url,
            issue_count=len(run.issues),
        )
        for q in self.subscribers.get(run.id, set()):
            try:
                q.put_nowait(event.model_dump())
            except asyncio.QueueFull:
                pass  # slow consumer: drop intermediate progress events


store = Store()
