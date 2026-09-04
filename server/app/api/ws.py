from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.models import ProgressEvent, TERMINAL_STATUSES
from app.core.store import store

router = APIRouter()


@router.websocket("/ws/{run_id}")
async def run_progress(socket: WebSocket, run_id: str) -> None:
    """Stream live progress events for one run until it reaches a terminal state."""
    await socket.accept()
    if store.get(run_id) is None:
        await socket.close(code=4404)
        return

    queue = store.subscribe(run_id)
    try:
        while True:
            current = store.get(run_id)
            if current is None:
                await socket.close(code=4404)
                return
            try:
                event = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                event = None

            if event is None:
                # No fresh event: if the run is finished, deliver a final snapshot.
                if current.status in TERMINAL_STATUSES:
                    await socket.send_json(ProgressEvent(
                        run_id=current.id, status=current.status,
                        phase=current.phase, pages_done=current.pages_done,
                        pages_total=current.pages_total,
                        current_url=current.current_url,
                        issue_count=len(current.issues),
                    ).model_dump())
                    return
                continue

            await socket.send_json(event)
            if event["status"] in {s.value for s in TERMINAL_STATUSES}:
                return
    except WebSocketDisconnect:
        return
    finally:
        store.unsubscribe(run_id, queue)
