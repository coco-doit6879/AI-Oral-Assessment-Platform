import sqlite3
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from test_mvp import ok

from app import diagnostic_store, diagnostics
from app.main import app


@pytest.fixture
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(diagnostic_store, "settings", lambda: SimpleNamespace(data_dir=str(tmp_path)))
    return diagnostic_store


def test_admin_only_logs_and_request_correlation(env, store):
    clients, _ = env
    for role in ("teacher", "reviewer", "student", "outsider"):
        assert clients[role].get("/admin/diagnostics").status_code == 403
    with TestClient(app) as anonymous:
        assert anonymous.get("/admin/diagnostics").status_code == 401
        assert anonymous.post("/diagnostics/client", json={"event": "client_error"}).status_code == 401
    response = clients["admin"].get("/admin/courses?private=secret-value")
    rows = ok(clients["admin"].get("/admin/diagnostics", params={"correlation": response.headers["X-Request-ID"]}))["items"]
    assert len(rows) == 1
    assert rows[0]["details"]["path"] == "/admin/courses"
    assert rows[0]["source"] == "API"
    assert "secret-value" not in str(rows)
    before = store.read()["items"]
    ok(clients["admin"].get("/admin/diagnostics"))
    assert store.read()["items"] == before  # Polling doesn't fill its own log.
    assert clients["admin"].get("/admin/diagnostics?limit=101").status_code == 422


def test_operations_safe_metadata_and_cursor_filter(store):
    with diagnostics.context(session_id="sitting", job_id="job"):
        with pytest.raises(ValueError), diagnostics.operation("ai.structured", model="model", provider="local"):
            raise ValueError("private answer and API key")
    diagnostics.event("unrelated", stage="worker.other", transcript="private transcript")
    first = store.read(correlation="sitting", source="AI", model="model", limit=1)
    assert first["items"][0]["event"] == "operation_failed"
    assert first["items"][0]["details"]["exception_type"] == "ValueError"
    second = store.read(correlation="job", before=first["next_cursor"], limit=1)
    assert second["items"][0]["event"] == "operation_started"
    assert second["next_cursor"] is None
    assert first["items"][0]["details"]["operation_id"] == second["items"][0]["details"]["operation_id"]
    assert "private" not in str(store.read())
    assert store.read(level="ERROR")["items"][0]["id"] == first["items"][0]["id"]
    assert store.read(since=time.time() + 60)["items"] == []
    assert "session_id" not in store.read()["items"][0]["details"]


def test_client_events_safe_routes_and_rate_limit(env, store):
    clients, _ = env
    client = clients["student"]
    body = {"event": "request_failed", "path": "/admin/results/private-student-id?api_key=secret",
            "http_status": 503, "view": "results", "exception_type": "TypeError"}
    for _ in range(25):
        assert client.post("/diagnostics/client", json=body).status_code == 204
    rows = store.read(source="WEB")["items"]
    assert len(rows) == 20
    assert rows[0]["details"]["path"] == "/admin/results/{key}"
    assert rows[0]["details"]["view"] == "results"
    assert "secret" not in str(rows) and "private-student-id" not in str(rows)
    assert client.post("/diagnostics/client", json=body | {"message": "secret"}).status_code == 422
    assert client.post("/diagnostics/client", json=body | {"exception_type": "secret"}).status_code == 422


def test_store_retention_capacity_and_unavailable(env, store, monkeypatch):
    monkeypatch.setattr(store, "MAX_EVENTS", 3)
    for n in range(5):
        assert store.append("API", "INFO", "test", {"http_status": n})
    assert [row["details"]["http_status"] for row in store.read()["items"]] == [4, 3, 2]
    with store.connect() as conn:
        conn.execute("UPDATE events SET created_at=?", (time.time() - store.RETENTION_SECONDS - 10,))
    assert store.read()["items"] == []
    assert store.append("AI", "INFO", "new", {})
    with store.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1

    def broken():
        raise sqlite3.OperationalError("disk unavailable")
    monkeypatch.setattr(store, "connect", broken)
    assert store.append("AI", "ERROR", "failed", {}) is False
    clients, _ = env
    assert clients["admin"].get("/admin/diagnostics").status_code == 503
    assert clients["admin"].get("/admin/courses").status_code == 200


def test_processing_logs_link_request_job_and_sitting_without_answer(env, store, monkeypatch):
    from test_server_processing import submitted, success_stt

    from app import speech, worker

    _, sitting, _ = submitted(env)
    monkeypatch.setattr(speech, "_transcribe_file", success_stt)
    assert worker.tick()
    assert worker.tick()
    client = env[0]["admin"]
    response = client.get(f"/admin/results/{sitting['id']}")
    assert response.status_code == 200
    rows = ok(client.get("/admin/diagnostics", params={"correlation": sitting["id"], "limit": 100}))["items"]
    assert any(row["source"] == "API" and row["details"]["request_id"] == response.headers["X-Request-ID"] for row in rows)
    stt = [row for row in rows if row["details"].get("stage") == "speech.transcribe"]
    assert len(stt) == 2 and all(row["details"].get("job_id") for row in stt)
    assert any(row["details"].get("stage") == "ai.grading" for row in rows)
    assert "My original spoken answer" not in str(rows)
