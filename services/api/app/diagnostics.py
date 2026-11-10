import json
import logging
import time
import traceback
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

import httpx

from . import diagnostic_store

log = logging.getLogger("oral.diagnostics")
_context = ContextVar("diagnostic_context", default={})


def event(name, level=logging.INFO, **details):
    values = diagnostic_store.sanitized(_context.get() | details)
    stage = str(values.get("stage", ""))
    source = "AI" if stage.startswith(("ollama.", "gemini.", "gopt.", "speech.", "ai.")) else "WORKER"
    log.log(level, "%s", json.dumps(values | {"event": name}, ensure_ascii=False))
    diagnostic_store.append(source, logging.getLevelName(level), name, values)


def failed(stage, exc, **details):
    frames = traceback.extract_tb(exc.__traceback__)[-8:]
    event("operation_failed", logging.ERROR, stage=stage,
          exception_type=type(exc).__name__,
          http_status=exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None,
          frames=[f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}" for frame in frames],
          **details)


@contextmanager
def context(**details):
    token = _context.set(_context.get() | details)
    try:
        yield
    finally:
        _context.reset(token)


@contextmanager
def operation(stage, **details):
    details = {"operation_id": str(uuid.uuid4()), **details}
    started = time.monotonic()
    event("operation_started", stage=stage, **details)
    metrics = {}
    try:
        yield metrics
    except Exception as exc:
        failed(stage, exc, elapsed_seconds=round(time.monotonic() - started, 3), **details)
        raise
    else:
        event("operation_completed", stage=stage,
              elapsed_seconds=round(time.monotonic() - started, 3), **details, **metrics)
