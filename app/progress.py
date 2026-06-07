from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from app.logging_utils import log_step


@dataclass
class ProgressEvent:
    stage: str
    message: str
    elapsed_ms: float


@dataclass
class ProgressRecord:
    request_id: str
    status: str = "running"
    started_at: float = field(default_factory=time.perf_counter)
    updated_at: float = field(default_factory=time.perf_counter)
    events: list[ProgressEvent] = field(default_factory=list)


_LOCK = Lock()
_PROGRESS: dict[str, ProgressRecord] = {}
_MAX_RECORDS = 200


def start_progress(request_id: str, message: str = "Bắt đầu pipeline.") -> None:
    with _LOCK:
        _PROGRESS[request_id] = ProgressRecord(request_id=request_id)
        _trim_locked()
    add_progress(request_id, "start", message)


def add_progress(request_id: str, stage: str, message: str) -> None:
    with _LOCK:
        record = _PROGRESS.setdefault(request_id, ProgressRecord(request_id=request_id))
        now = time.perf_counter()
        record.updated_at = now
        record.events.append(
            ProgressEvent(
                stage=stage,
                message=message,
                elapsed_ms=round((now - record.started_at) * 1000, 2),
            )
        )
    log_step(request_id, stage, message)


def finish_progress(request_id: str, message: str = "Pipeline hoàn tất.") -> None:
    add_progress(request_id, "done", message)
    with _LOCK:
        if request_id in _PROGRESS:
            _PROGRESS[request_id].status = "done"


def fail_progress(request_id: str, message: str) -> None:
    add_progress(request_id, "error", message)
    with _LOCK:
        if request_id in _PROGRESS:
            _PROGRESS[request_id].status = "error"


def get_progress(request_id: str) -> dict[str, Any]:
    with _LOCK:
        record = _PROGRESS.get(request_id)
        if not record:
            return {"request_id": request_id, "status": "unknown", "events": []}
        return {
            "request_id": record.request_id,
            "status": record.status,
            "events": [event.__dict__ for event in record.events],
        }


def _trim_locked() -> None:
    if len(_PROGRESS) <= _MAX_RECORDS:
        return
    oldest = sorted(_PROGRESS.items(), key=lambda item: item[1].updated_at)
    for request_id, _ in oldest[: len(_PROGRESS) - _MAX_RECORDS]:
        _PROGRESS.pop(request_id, None)
