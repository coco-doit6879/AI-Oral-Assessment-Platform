import json
import time

import httpx
import pytest
from test_mvp import ok, prepare, start, upload
from test_pronunciation import CRITERIA, RESULT

from app import ai, pronunciation, runtime_settings, speech, worker
from app.config import settings
from app.models import Attempt, Chunk, Exam, ExamSession, ReviewJob, Upload


def ready(env):
    context = prepare(env, 1)
    session = start(env, context)
    student = env[0]["student"]
    attempt_id = session["current_attempt"]["id"]
    ok(student.post(f"/question-attempts/{attempt_id}/start"))
    ok(student.post(f"/question-attempts/{attempt_id}/submit", json={
        "transcript": "Original submitted answer", "stt_confidence": 0.96,
    }, headers={"Idempotency-Key": "full-local-review"}))
    audio, blob = upload(student, attempt_id, "AUDIO")
    upload(student, attempt_id, "VIDEO")
    ok(student.post(f"/exam-sessions/{session['id']}/finish"))
    assert worker.tick()
    return context, session, attempt_id, audio, blob


@pytest.mark.parametrize("pronounce", [False, True])
@pytest.mark.parametrize("threads", [0, 3])
def test_full_local_review_pins_models_avoids_cloud_and_preserves_evidence(env, monkeypatch, pronounce, threads):
    context, session, attempt_id, audio, blob = ready(env)
    with env[1]() as db:
        exam = db.get(Exam, context["exam"]["id"])
        exam.snapshot = exam.snapshot | {"criteria": CRITERIA if pronounce else CRITERIA[:1], "speech_language": "en"}
        before = db.get(Attempt, attempt_id).assessment
        db.commit()
    cfg = settings()
    monkeypatch.setattr(cfg, "local_review_llm_model", "local-test-model")
    monkeypatch.setattr(cfg, "gopt_enabled", True)
    monkeypatch.setattr(cfg, "local_llm_cpu_threads", threads)
    path = f"/admin/attempts/{attempt_id}/local-review"
    body = {"reason": "Regrade everything from original audio"}
    for role in ("teacher", "reviewer", "student", "outsider"):
        assert env[0][role].post(path, json=body).status_code == 403
    job = ok(env[0]["admin"].post(path, json=body), 202)
    assert ok(env[0]["admin"].post(path, json=body), 202)["id"] == job["id"]
    order = []

    def stt(path, policy):
        order.append("stt")
        assert path.read_bytes() == blob
        assert policy["provider"] == "local_server" and policy["language"] == "en"
        assert runtime_settings.settings().stt_model == policy["stt_model"]
        return {"transcript": "Freshly recognized answer", "stt_confidence": 0.98, "preprocessing": "off"}

    def ollama(operation, payload):
        order.append("llm")
        assert operation == "chat" and payload["model"] == "local-test-model"
        assert payload["options"]["num_gpu"] == 0
        if threads:
            assert payload["options"]["num_thread"] == threads
        else:
            assert "num_thread" not in payload["options"]
        assert payload["keep_alive"] == 0
        data = json.loads(payload["messages"][1]["content"])
        assert data["transcript"] == "Freshly recognized answer"
        assert data["rubric"] == CRITERIA[:1]
        assert data["evidence"]
        return {"message": {"content": json.dumps({
            "criteria": [{"name": "Content", "score": 1.6, "comment": "Supported concepts"}],
            "confidence": 0.96, "missing_concepts": [], "reasoning_summary": "Grounded answer",
            "reference_chunk_ids": [chunk["id"] for chunk in data["evidence"]],
        })}}

    def gopt(request):
        order.append("gopt")
        assert blob in request.content and b"Freshly recognized answer" in request.content
        return httpx.Response(200, json=RESULT)

    original_client = httpx.Client
    monkeypatch.setattr(pronunciation.httpx, "Client",
                        lambda **kwargs: original_client(transport=httpx.MockTransport(gopt), **kwargs))
    monkeypatch.setattr(speech, "transcribe_file", stt)
    monkeypatch.setattr(ai, "ollama", ollama)
    monkeypatch.setattr(ai, "gemini", lambda *args: pytest.fail("Cloud is forbidden for local review"))
    monkeypatch.setattr(ai, "embed", lambda *args: pytest.fail("Do not mix frozen cloud embeddings with local embeddings"))
    monkeypatch.setattr(cfg, "local_review_llm_model", "changed-after-queue")
    assert worker.tick()
    assert order == (["stt", "llm", "gopt"] if pronounce else ["stt", "llm"])
    with env[1]() as db:
        review = db.get(ReviewJob, job["id"])
        attempt = db.get(Attempt, attempt_id)
        assert review.status == "COMPLETED", review.error
        assert review.original["assessment"] == before
        assert review.original["audio_id"] == audio["id"]
        assert attempt.transcript == "Original submitted answer"
        assert attempt.stt_confidence == 0.96
        assert attempt.assessment["score"] == (7.88 if pronounce else 8)
        assert attempt.assessment["retrieval"] == "frozen-lexical-v1"
        assert db.get(ExamSession, session["id"]).status == "REVIEW_REQUIRED"
    assert runtime_settings.settings().ai_provider == "demo"
    assert runtime_settings.settings().local_llm_cpu_only is False


@pytest.mark.parametrize("failure_stage", ["stt", "llm", "llm_timeout", "gopt", "checksum"])
def test_local_review_failures_preserve_previous_assessment(env, monkeypatch, caplog, failure_stage):
    context, _, attempt_id, audio, _ = ready(env)
    monkeypatch.setattr(settings(), "local_review_llm_model", "local-test-model")
    with env[1]() as db:
        before = db.get(Attempt, attempt_id).assessment
    job = ok(env[0]["admin"].post(f"/admin/attempts/{attempt_id}/local-review", json={"reason": "Check original audio"}), 202)
    calls = []

    def stt(*args):
        calls.append("stt")
        if failure_stage == "stt":
            raise TimeoutError("private error")
        return {"transcript": "Fresh audio transcript", "stt_confidence": 0.9}

    def grade(*args, **kwargs):
        calls.append("grade")
        if failure_stage == "llm":
            raise ValueError("private error")
        if failure_stage == "llm_timeout":
            raise httpx.ReadTimeout("private error")
        return {"score": None, "pronunciation": {"status": "FAILED"}}

    monkeypatch.setattr(speech, "transcribe_file", stt)
    monkeypatch.setattr(worker, "grade_answer", grade)
    if failure_stage == "checksum":
        with env[1]() as db:
            db.get(Upload, audio["id"]).sha256 = "0" * 64
            db.commit()
    assert worker.tick()
    with env[1]() as db:
        review = db.get(ReviewJob, job["id"])
        assert review.status == "FAILED" and "private error" not in review.error
        assert job["id"] in review.error
        if failure_stage == "llm_timeout":
            assert review.error.startswith("AI_TIMEOUT:")
            assert "chấm lại transcript" not in review.error
        assert db.get(Attempt, attempt_id).assessment == before
        assert db.get(Attempt, attempt_id).transcript == "Original submitted answer"
    assert job["id"] in caplog.text and attempt_id in caplog.text
    assert "private error" not in caplog.text
    if failure_stage in {"stt", "llm", "llm_timeout"}:
        assert ('"stage": "review.stt"' if failure_stage == "stt" else '"stage": "review.grading"') in caplog.text
    if failure_stage == "checksum":
        assert not calls


def test_local_review_requires_configuration_and_rejects_deleted_session(env, monkeypatch):
    _, session, attempt_id, _, _ = ready(env)
    path = f"/admin/attempts/{attempt_id}/local-review"
    body = {"reason": "Check original audio"}
    monkeypatch.setattr(settings(), "local_review_llm_model", "")
    assert env[0]["admin"].post(path, json=body).json()["error"]["code"] == "LOCAL_REVIEW_NOT_CONFIGURED"
    monkeypatch.setattr(settings(), "local_review_llm_model", "local-test-model")
    with env[1]() as db:
        db.get(ExamSession, session["id"]).deleted_at = time.time()
        db.commit()
    assert env[0]["admin"].post(path, json=body).status_code == 404


@pytest.mark.parametrize("problem,reason", [
    ("disabled", "GOPT_DISABLED"), ("language", "LANGUAGE_UNSUPPORTED"),
    ("timeout", "GOPT_TIMEOUT"), ("connect", "GOPT_CONNECTION_FAILED"),
    (422, "GOPT_INPUT_REJECTED"), (429, "GOPT_BUSY"), (503, "GOPT_HTTP_ERROR"),
])
def test_real_pronunciation_failure_visible_in_admin_error_logs(env, monkeypatch, problem, reason):
    context, session, attempt_id, _, _ = ready(env)
    cfg = settings()
    monkeypatch.setattr(cfg, "local_review_llm_model", "local-test-model")
    monkeypatch.setattr(cfg, "gopt_enabled", problem != "disabled")
    with env[1]() as db:
        exam = db.get(Exam, context["exam"]["id"])
        exam.snapshot = exam.snapshot | {"criteria": CRITERIA[1:],
                                        "speech_language": "vi" if problem == "language" else "en"}
        before = db.get(Attempt, attempt_id).assessment
        db.commit()
    client = env[0]["admin"]
    job = ok(client.post(f"/admin/attempts/{attempt_id}/local-review",
                         json={"reason": "Check pronunciation"}), 202)
    monkeypatch.setattr(speech, "transcribe_file", lambda *args: {
        "transcript": "private-student-answer", "stt_confidence": 0.9})

    def gopt(request):
        if problem in {"disabled", "language"}:
            pytest.fail("Preflight must not call GOPT")
        if problem in {"timeout", "connect"}:
            error = httpx.ReadTimeout if problem == "timeout" else httpx.ConnectError
            raise error("private-provider-error", request=request)
        return httpx.Response(problem, json={"detail": "private-provider-error"})

    original_client = httpx.Client
    monkeypatch.setattr(pronunciation.httpx, "Client",
                        lambda **kwargs: original_client(transport=httpx.MockTransport(gopt), **kwargs))
    assert worker.tick()
    with env[1]() as db:
        review = db.get(ReviewJob, job["id"])
        assert review.status == "FAILED"
        assert review.error.startswith("PRONUNCIATION_FAILED:")
        assert pronunciation.FAILURE_MESSAGES[reason] in review.error
        assert job["id"] in review.error
        assert db.get(Attempt, attempt_id).assessment == before
        assert review.result is None
    rows = ok(client.get("/admin/diagnostics", params={
        "correlation": job["id"], "source": "AI", "level": "ERROR", "model": "gopt-librispeech",
    }))["items"]
    failure = next(row for row in rows if row["details"]["stage"] == "gopt.pronunciation")
    assert failure["details"]["code"] == "PRONUNCIATION_FAILED"
    assert failure["details"]["reason_code"] == reason
    assert failure["details"]["session_id"] == session["id"]
    assert failure["details"]["attempt_id"] == attempt_id
    assert "private-" not in str(rows)


def test_local_retrieval_uses_only_frozen_course_and_document_scope(env, monkeypatch):
    context = prepare(env, 1)
    monkeypatch.setattr(ai, "embed", lambda *args: pytest.fail("No embedding provider in local review"))
    with env[1]() as db:
        exam = db.get(Exam, context["exam"]["id"])
        snapshot = exam.snapshot
        question = snapshot["questions"][0]
        allowed = snapshot["topic_chunk_ids"][question["topic_id"]]
        original = db.get(Chunk, allowed[0])
        extra = Chunk(course_id=exam.course_id, document_id=original.document_id,
                      topic_id=original.topic_id, page=1, content="outside-frozen-scope", embedding=[0.0] * 768)
        db.add(extra)
        db.flush()
        rows = ai.retrieve_frozen(db, exam.course_id, "outside-frozen-scope", snapshot["document_ids"], allowed)
        assert rows and extra.id not in {row["id"] for row in rows}
        assert ai.retrieve_frozen(db, "another-course", "answer", snapshot["document_ids"], allowed) == []
        assert ai.retrieve_frozen(db, exam.course_id, "answer", [], allowed) == []
