"""Bounded application diagnostics shared by API and worker via DATA_DIR.

Independent transactions keep diagnostic failures from rolling back exam work.
No prompts, transcripts, request bodies, credentials or provider response bodies.
"""
import json
import math
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from .config import settings

MAX_EVENTS = 10000
RETENTION_SECONDS = 7 * 86400
FIELDS = {
    "request_id", "resource_id", "view", "session_id", "exam_id", "attempt_id", "job_id", "user_id",
    "provider", "review_provider", "model", "stage", "status", "code", "exception_type",
    "http_status", "method", "path", "elapsed_seconds", "timeout_seconds", "connect_timeout_seconds",
    "total_duration", "load_duration", "prompt_eval_duration", "eval_duration", "prompt_eval_count",
    "eval_count", "audio_bytes", "gopt_enabled", "frames", "operation_id", "reason_code",
}


def connect():
    folder = Path(settings().data_dir) / "diagnostics"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    conn = sqlite3.connect(folder / "events.sqlite3", timeout=0.25)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at REAL NOT NULL,
        source TEXT NOT NULL, level TEXT NOT NULL, event TEXT NOT NULL, details TEXT NOT NULL)""")
    return conn


def sanitized(details):
    result = {}
    for key, value in details.items():
        if key not in FIELDS:
            continue
        if value is None or isinstance(value, bool):
            result[key] = value
        elif isinstance(value, (int, float)) and math.isfinite(value):
            result[key] = value
        elif isinstance(value, str):
            result[key] = value[:200]
        elif key == "frames" and isinstance(value, list):
            result[key] = [str(frame)[:200] for frame in value[:8]]
    return result


def append(source, level, event, details, *, throttle_user=None):
    try:
        now = time.time()
        with closing(connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            if throttle_user:
                count = conn.execute("SELECT COUNT(*) FROM events WHERE source='WEB' AND created_at>? AND json_extract(details, '$.user_id')=?", (now - 60, throttle_user)).fetchone()[0]
                if count >= 20:
                    return False
            conn.execute("INSERT INTO events(created_at,source,level,event,details) VALUES(?,?,?,?,?)",
                         (now, source, level, event[:80], json.dumps(sanitized(details), ensure_ascii=False)))
            conn.execute("DELETE FROM events WHERE created_at<? OR id <= COALESCE((SELECT id FROM events ORDER BY id DESC LIMIT 1 OFFSET ?),0)", (now - RETENTION_SECONDS, MAX_EVENTS))
        return True
    except (OSError, sqlite3.Error):
        # Logging cannot block submission or grading when disk/storage is unavailable.
        return False


def read(*, source=None, level=None, correlation=None, model=None, before=None, since=None, limit=50):
    clauses, values = ["created_at>=?"], [time.time() - RETENTION_SECONDS]
    for key, value in (("source", source), ("level", level)):
        if value:
            clauses.append(f"{key}=?")
            values.append(value)
    if before is not None:
        clauses.append("id<?")
        values.append(before)
    if since is not None:
        clauses.append("created_at>=?")
        values.append(since)
    if model:
        clauses.append("json_extract(details,'$.model')=?")
        values.append(model)
    if correlation:
        keys = ("resource_id", "request_id", "resource_id", "view", "session_id", "exam_id", "attempt_id", "job_id", "operation_id")
        clauses.append("(" + " OR ".join(f"json_extract(details,'$.{key}')=?" for key in keys) + ")")
        values.extend([correlation] * len(keys))
    with closing(connect()) as conn:
        rows = conn.execute("SELECT * FROM events WHERE " + " AND ".join(clauses) + " ORDER BY id DESC LIMIT ?", [*values, limit + 1]).fetchall()
    items = [dict(row) | {"details": json.loads(row["details"])} for row in rows[:limit]]
    return {"items": items, "next_cursor": items[-1]["id"] if len(rows) > limit else None,
            "retention_days": 7, "max_events": MAX_EVENTS}
