"""Durable database queue. A transaction lock prevents duplicate workers; rollback permits crash retry."""

import hashlib
import logging
import shutil
import tempfile
import time
from contextlib import closing
from pathlib import Path
from threading import Lock
from types import SimpleNamespace

from sqlalchemy import select, text

from . import ai, diagnostics, media_retention, processing, pronunciation, runtime_settings, speech, storage
from .db import SessionLocal
from .documents import process_document
from .grading import GradingError, check_config, failure, review_question, score_summary
from .models import (
    Attempt,
    Audit,
    Chunk,
    Document,
    Exam,
    ExamSession,
    MediaCleanup,
    ProcessingJob,
    ReviewJob,
    Upload,
)

log = logging.getLogger("oral.worker")
_serial_lock = Lock()


def finalize(db, session):
    if session.status not in {"SUBMITTED", "REVIEW_REQUIRED", "COMPLETED"}:
        return
    attempts = db.scalars(select(Attempt).where(Attempt.session_id == session.id)).all()
    if db.scalar(select(ProcessingJob.id).join(Attempt).where(
        Attempt.session_id == session.id, ProcessingJob.status.in_(processing.ACTIVE),
    ).limit(1)):
        session.status, session.final_score = "SUBMITTED", None
        return
    if not attempts or any(a.assessment is None for a in attempts):
        return
    if db.scalar(
        select(ReviewJob.id)
        .join(Attempt)
        .where(Attempt.session_id == session.id, ReviewJob.status == "PENDING")
        .limit(1)
    ):
        session.status, session.final_score = "REVIEW_REQUIRED", None
        return
    exam = db.get(Exam, session.exam_id)
    summary = score_summary(attempts, len((exam.snapshot or {}).get("questions", [])))
    session.ai_score = summary["total_score"]
    if session.manual_review:
        session.final_score = session.manual_review["score"]
        session.status = "COMPLETED"
        return
    review = any(a.assessment.get("review_required", True) for a in attempts) or session.ai_score is None
    review = review or bool(db.scalar(select(Audit.id).where(Audit.event == "PROCTORING_EVENT",
        Audit.details["session_id"].as_string() == session.id).limit(1)))
    session.final_score = session.ai_score if not review else None
    if session.ai_score is not None and session.ai_score < 5:
        review = True
        session.final_score = None
    session.status = "REVIEW_REQUIRED" if review else "COMPLETED"


def frozen_chunks(db, exam, attempt):
    snapshot = exam.snapshot
    if "topic_chunk_ids" in snapshot:
        return snapshot["topic_chunk_ids"].get(attempt.question["topic_id"], [])
    # Published MVP exams used the legacy fixed topic column, not today's mappings.
    return list(
        db.scalars(
            select(Chunk.id).where(
                Chunk.course_id == exam.course_id,
                Chunk.topic_id == attempt.question["topic_id"],
                Chunk.document_id.in_(snapshot["document_ids"]),
            )
        )
    )


def grade_answer(db, exam, session, attempt, transcript, confidence, local_review=False):
    with diagnostics.context(session_id=getattr(session, "id", None), exam_id=getattr(exam, "id", None),
                             attempt_id=getattr(attempt, "id", None)), \
            diagnostics.operation("ai.grading", provider=runtime_settings.settings().ai_provider,
                                  model=runtime_settings.settings().llm_model):
        return _grade_answer(db, exam, session, attempt, transcript, confidence, local_review)


def _grade_answer(db, exam, session, attempt, transcript, confidence, local_review=False):
    snapshot = exam.snapshot
    if snapshot.get("practice"):
        return {
            "score": None,
            "review_required": True,
            "confidence": None,
            "status": "NOT_GRADED",
            "criteria": [],
            "retrieved_chunks": [],
            "model": "practice",
            "rubric_version": snapshot["rubric_version"],
            "knowledge_version": snapshot["knowledge_version"],
            "reasoning_summary": "Đã hoàn thành câu luyện tập. Bài này không tính điểm chính thức.",
        }
    if not local_review:
        check_config(exam)
    content_criteria = [criterion for criterion in snapshot["criteria"] if not pronunciation.is_criterion(criterion)]
    chunks = []
    if content_criteria:
        chunks = ai.retrieve_frozen(
            db, exam.course_id, attempt.question["text"] + "\n" + (transcript or ""),
            snapshot["document_ids"], frozen_chunks(db, exam, attempt),
        ) if local_review else ai.retrieve(
            db,
            exam.course_id,
            attempt.question["topic_id"],
            attempt.question["text"] + "\n" + (transcript or ""),
            snapshot["document_ids"],
            frozen_chunks(db, exam, attempt),
        )
    assessment = ai.grade(
        attempt.question,
        transcript,
        content_criteria,
        chunks,
        confidence if attempt.finished_at <= session.started_at + exam.time_limit else 0,
    ) if content_criteria else {
        "score": None, "status": "COMPLETED", "criteria": [], "confidence": None,
        "review_required": True, "model": "gopt-librispeech", "prompt_version": ai.PROMPT_VERSION,
        "retrieved_chunks": chunks, "reasoning_summary": "Rubric phát âm được chấm từ audio bằng GOPT.",
    }
    assessment |= {"rubric_version": snapshot["rubric_version"], "knowledge_version": snapshot["knowledge_version"]}
    if local_review:
        assessment |= {"grading_provider": "local", "retrieval": "frozen-lexical-v1", "review_required": True}
    return pronunciation.assess(db, exam, attempt, transcript, assessment)


def process_review(db, job):
    attempt = db.get(Attempt, job.attempt_id)
    session = db.get(ExamSession, attempt.session_id)
    with diagnostics.context(job_id=job.id, attempt_id=job.attempt_id, session_id=session.id,
                             exam_id=session.exam_id, review_provider=job.policy["provider"]):
        diagnostics.event("review_started")
        started = time.monotonic()
        process_review_job(db, job)
        diagnostics.event("review_finished", status=job.status,
                          elapsed_seconds=round(time.monotonic() - started, 3))


def process_review_job(db, job):
    attempt = db.scalar(select(Attempt).where(Attempt.id == job.attempt_id).with_for_update())
    session = db.get(ExamSession, attempt.session_id)
    exam = db.get(Exam, session.exam_id)
    try:
        if job.policy["provider"] == "grading":
            target = db.get(Exam, job.policy["target_exam_id"])
            question = review_question(exam, target, attempt)
            reviewed = SimpleNamespace(id=attempt.id, question=question, finished_at=attempt.finished_at)
            assessment = grade_answer(db, target, session, reviewed,
                                      job.original["transcript"], job.original["stt_confidence"] or 0)
            assessment = assessment | {"grading_exam_id": target.id, "source_exam_id": exam.id,
                                       "review_required": True}
            # A change of grading version always requires human review.
            job.result = {"transcript": job.original["transcript"],
                          "stt_confidence": job.original["stt_confidence"],
                          "preprocessing": "unchanged", "assessment": assessment}
            attempt.assessment = assessment
            job.status = "COMPLETED"
        else:
            process_transcription_review(db, job, exam, session, attempt)
    except Exception as exc:
        job.status = "FAILED"
        code, message = failure(exc)
        job.error = f"{code}: {message} Đánh giá trước được giữ nguyên. Mã tác vụ: {job.id}."
        diagnostics.failed("review", exc, code=code)
    job.completed_at = time.time()
    db.add(Audit(user_id=job.requested_by, event=job.policy["provider"].upper() + "_REVIEW_" + job.status,
                 details={"job_id": job.id, "attempt_id": attempt.id}))
    db.flush()
    session = db.scalar(select(ExamSession).where(ExamSession.id == session.id).with_for_update())
    finalize(db, session)


def process_transcription_review(db, job, exam, session, attempt):
    if job.policy["provider"] == "local_server":
        if job.policy.get("prompt_version") != ai.PROMPT_VERSION:
            raise GradingError("AI_CONFIG_MISMATCH", "Phiên bản chấm local đã đổi; gửi lại yêu cầu chấm từ audio.")
        with runtime_settings.override(ai_provider="local", llm_model=job.policy["llm_model"],
                                       stt_model=job.policy["stt_model"], local_llm_cpu_only=True):
            return transcribe_and_grade(db, job, exam, session, attempt, local_review=True)
    check_config(exam)
    return transcribe_and_grade(db, job, exam, session, attempt)


def transcribe_and_grade(db, job, exam, session, attempt, local_review=False):
    audio = db.get(Upload, job.original["audio_id"])
    if (not audio or audio.sha256 != job.original["audio_sha256"] or audio.status != "COMPLETED"
            or audio.attempt_id != attempt.id or audio.kind != "AUDIO"):
        raise ValueError("Original evidence changed")
    with tempfile.TemporaryDirectory(prefix="oral-review-") as folder:
        path = Path(folder) / "original.webm"
        digest, size = hashlib.sha256(), 0
        limit = runtime_settings.settings().max_media_mb * 1024 * 1024
        with diagnostics.operation("review.audio_download", audio_bytes=audio.size), \
                closing(storage.open_stream(audio.storage_key)) as source, path.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > limit or size > audio.size:
                    raise ValueError("Original audio too large")
                digest.update(chunk)
                target.write(chunk)
        if size != audio.size or digest.hexdigest() != audio.sha256:
            raise ValueError("Original audio checksum mismatch")
        with diagnostics.operation("review.stt", provider=job.policy["provider"],
                                   model=runtime_settings.settings().stt_model, audio_bytes=size):
            transcript = speech.transcribe_file(path, job.policy)
    reviewed = SimpleNamespace(id=attempt.id, question=attempt.question, finished_at=attempt.finished_at,
                               pronunciation_audio_id=audio.id, pronunciation_language=job.policy["language"])
    with diagnostics.operation("review.grading", provider=runtime_settings.settings().ai_provider,
                               model=runtime_settings.settings().llm_model):
        assessment = grade_answer(
            db, exam, session, reviewed, transcript["transcript"], transcript["stt_confidence"], local_review=local_review,
        )
    if assessment.get("pronunciation", {}).get("status") == "FAILED":
        raise GradingError("PRONUNCIATION_FAILED", pronunciation.failure_message(assessment["pronunciation"]))
    job.result = transcript | {"assessment": assessment}
    # The submitted transcript and idempotency payload remain immutable.
    attempt.assessment = assessment
    job.status = "COMPLETED"


@runtime_settings.snapshot()
def tick():
    if not runtime_settings.settings().worker_serial:
        return process_next()
    if not _serial_lock.acquire(blocking=False):
        return False
    try:
        with SessionLocal() as lock_db:
            if lock_db.get_bind().dialect.name == "postgresql":
                if not lock_db.scalar(text("SELECT pg_try_advisory_xact_lock(72627620)")):
                    return False
            return process_next()
    finally:
        _serial_lock.release()


def process_next():
    if media_retention.tick(SessionLocal):
        return True
    if processing.tick(SessionLocal):
        return True
    with SessionLocal() as db:
        cleanup = db.scalar(select(MediaCleanup).where(MediaCleanup.next_attempt_at <= time.time())
                            .order_by(MediaCleanup.created_at).with_for_update(skip_locked=True).limit(1))
        if cleanup:
            try:
                if cleanup.storage_key:
                    storage.delete(cleanup.storage_key)
                root = (Path(runtime_settings.settings().data_dir) / "uploads").resolve()
                folder = (root / cleanup.upload_id).resolve()
                if folder.parent != root:
                    raise ValueError("Invalid cleanup path")
                if folder.exists():
                    shutil.rmtree(folder)
                db.delete(cleanup)
            except Exception as exc:
                cleanup.retries += 1
                cleanup.next_attempt_at = time.time() + min(3600, 2 ** min(cleanup.retries, 12))
                log.warning("media_cleanup_failed id=%s type=%s", cleanup.id, type(exc).__name__)
            db.commit()
            return True
        job = db.scalar(
            select(ReviewJob)
            .where(ReviewJob.status == "PENDING")
            .order_by(ReviewJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job:
            process_review(db, job)
            db.commit()
            return True
        document = db.scalar(
            select(Document)
            .where(Document.status == "PENDING")
            .order_by(Document.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if document:
            try:
                with db.begin_nested():
                    process_document(db, document)
            except Exception as exc:
                document.status = "FAILED"
                document.error = "Xử lý tài liệu thất bại. Kiểm tra định dạng và cấu hình AI rồi thử lại."
                log.warning("document_failed id=%s type=%s", document.id, type(exc).__name__)
            db.commit()
            return True
        attempt = db.scalar(
            select(Attempt)
            .where(Attempt.status == "SUBMITTED", Attempt.assessment.is_(None),
                   ~select(ProcessingJob.id).where(ProcessingJob.attempt_id == Attempt.id).exists())
            .order_by(Attempt.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not attempt:
            return False
        session = db.get(ExamSession, attempt.session_id)
        exam = db.get(Exam, session.exam_id)
        snapshot = exam.snapshot
        try:
            attempt.assessment = grade_answer(
                db, exam, session, attempt, attempt.transcript, attempt.stt_confidence or 0
            )
        except Exception as exc:
            code, message = failure(exc)
            attempt.assessment = {
                "score": None,
                "review_required": True,
                "confidence": None,
                "status": "FAILED",
                "error_code": code,
                "criteria": [],
                "retrieved_chunks": [],
                "model": snapshot["llm_model"],
                "rubric_version": snapshot["rubric_version"],
                "knowledge_version": snapshot["knowledge_version"],
                "prompt_version": snapshot["prompt_version"],
                "reasoning_summary": message,
                "error": type(exc).__name__,
            }
            log.warning("grading_failed attempt=%s code=%s type=%s", attempt.id, code, type(exc).__name__)
        attempt.status = "GRADED"
        db.add(Audit(event="QUESTION_GRADED", details={"attempt_id": attempt.id}))
        # Serialize completion across workers grading different attempts in one session.
        db.flush()
        session = db.scalar(select(ExamSession).where(ExamSession.id == session.id).with_for_update())
        finalize(db, session)
        db.commit()
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            worked = tick()
        except Exception as exc:
            log.error("worker_error type=%s", type(exc).__name__)
            worked = False
        if not worked:
            time.sleep(2)
