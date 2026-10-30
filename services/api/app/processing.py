"""Committed queue states; row locks exclude concurrent processing and deletion.

A claimed stage survives worker restarts. Expired claims are recovered after five
minutes; a still-running worker holds the job lock, so it cannot be taken over.
Only job metadata is public; provider secrets and raw exceptions never are.
"""
import hashlib
import logging
import tempfile
import time
from pathlib import Path

from sqlalchemy import and_, or_, select

from . import diagnostics, speech, storage
from .models import Attempt, Audit, Exam, ExamSession, ProcessingJob, Upload, uid

log = logging.getLogger("oral.processing")
ACTIVE = {"WAITING_SUBMISSION", "QUEUED_STT", "STT_RUNNING", "QUEUED_GRADING", "GRADING_RUNNING"}
LEASE_SECONDS = 300


def server_policy(db, exam):
    policy = speech.exam_policy(db, exam)
    if policy["provider"] == "local":
        policy["provider"] = "local_server"
    if policy["provider"] == "gemini":
        policy["model"] = speech.settings().gemini_stt_model
    return policy


def job_view(job):
    return {k: getattr(job, k) for k in ("status", "stage", "updated_at", "runs", "error")} | {
        "provider": job.policy["provider"],
        "confidence_source": (job.result or {}).get("confidence_source"),
    }


def summary(db, session_id):
    jobs = db.scalars(select(ProcessingJob).join(Attempt).where(Attempt.session_id == session_id)).all()
    return summarize(jobs)


def summarize(jobs):
    if not jobs:
        return None
    # A running/pending job takes precedence over errors in other answers.
    status = next((state for state in ["STT_RUNNING", "GRADING_RUNNING", "QUEUED_STT",
                  "QUEUED_GRADING", "WAITING_SUBMISSION", "FAILED"]
                   if any(j.status == state for j in jobs)), "COMPLETED")
    return {"status": status, "total": len(jobs),
            "transcribed": sum(j.result is not None for j in jobs),
            "completed": sum(j.status == "COMPLETED" for j in jobs),
            "failed": sum(j.status == "FAILED" for j in jobs)}


def queue_session(db, session_id):
    jobs = db.scalars(select(ProcessingJob).join(Attempt).where(
        Attempt.session_id == session_id, ProcessingJob.status == "WAITING_SUBMISSION",
    )).all()
    for job in jobs:
        job.status, job.updated_at = "QUEUED_STT", time.time()


def tick(factory):
    from .grading import failure
    from .worker import finalize, grade_answer

    with factory() as db:
        job = db.scalar(select(ProcessingJob).join(Attempt).join(ExamSession).where(
            ExamSession.deleted_at.is_(None), ExamSession.status.in_(["SUBMITTED", "REVIEW_REQUIRED"]),
            or_(ProcessingJob.status.in_(["QUEUED_STT", "QUEUED_GRADING"]),
                and_(ProcessingJob.status.in_(["STT_RUNNING", "GRADING_RUNNING"]),
                     ProcessingJob.lease_until <= time.time())),
        ).order_by(ProcessingJob.updated_at, ProcessingJob.id)
          .with_for_update(skip_locked=True, of=ProcessingJob).limit(1))
        if not job:
            return False
        job.stage = "STT" if job.status in {"QUEUED_STT", "STT_RUNNING"} else "GRADING"
        job.status = job.stage + "_RUNNING"
        job.token, job.lease_until, job.updated_at = uid(), time.time() + LEASE_SECONDS, time.time()
        job.runs += 1
        key, token = job.id, job.token
        db.commit()  # Readers can see the running state during the provider call.

    with factory() as db:
        job = db.scalar(select(ProcessingJob).where(ProcessingJob.id == key)
                        .with_for_update(skip_locked=True))
        if not job or job.token != token:
            return True
        attempt = db.scalar(select(Attempt).where(Attempt.id == job.attempt_id).with_for_update())
        session = db.get(ExamSession, attempt.session_id)
        exam = db.get(Exam, session.exam_id)
        with diagnostics.context(job_id=job.id, attempt_id=attempt.id, session_id=session.id, exam_id=exam.id):
            diagnostics.event("submission_started", stage=job.stage)
            try:
                if job.runs > 6:
                    raise RuntimeError("Worker repeatedly interrupted")
                if job.stage == "STT":
                    audio = db.scalar(select(Upload).where(Upload.attempt_id == attempt.id,
                        Upload.kind == "AUDIO", Upload.status == "COMPLETED").order_by(Upload.created_at, Upload.id))
                    if not audio or not audio.storage_key:
                        raise ValueError("Audio unavailable")
                    content = storage.get(audio.storage_key)
                    if hashlib.sha256(content).hexdigest() != audio.sha256:
                        raise ValueError("Audio checksum mismatch")
                    with tempfile.TemporaryDirectory(prefix="oral-submission-") as folder:
                        path = Path(folder) / "answer.webm"
                        path.write_bytes(content)
                        result = speech.transcribe_file(path, job.policy)
                    if not result["transcript"].strip():
                        raise ValueError("No speech")
                    attempt.transcript = result["transcript"]
                    attempt.stt_confidence = result["stt_confidence"]
                    job.result = result
                    job.status = "QUEUED_GRADING"
                else:
                    attempt.assessment = grade_answer(db, exam, session, attempt,
                        attempt.transcript, attempt.stt_confidence or 0)
                    attempt.status, job.status = "GRADED", "COMPLETED"
                job.error = None
                if (attempt.assessment or {}).get("pronunciation", {}).get("status") == "FAILED":
                    job.status = "FAILED"
                    job.error = "PRONUNCIATION_FAILED: Chưa chấm được phát âm. Có thể thử chấm lại."
            except Exception as exc:
                code, message = failure(exc) if job.stage == "GRADING" else (
                    "STT_FAILED", "Nhận dạng audio thất bại. Kiểm tra cấu hình STT, model, quota và bản ghi rồi thử lại.")
                job.status, job.error = "FAILED", f"{code}: {message}"
                attempt.status = "GRADED"
                attempt.assessment = {"score": None, "confidence": None, "review_required": True,
                    "status": "FAILED", "error": code, "error_code": code, "reasoning_summary": message,
                    "criteria": [], "rubric_version": exam.snapshot["rubric_version"],
                    "knowledge_version": exam.snapshot["knowledge_version"]}
                diagnostics.failed("submission." + job.stage, exc)
                log.warning("submission_failed job=%s stage=%s type=%s", key, job.stage, type(exc).__name__)
            diagnostics.event("submission_finished", stage=job.stage, status=job.status)
        job.updated_at, job.lease_until, job.token = time.time(), None, None
        db.add(Audit(event="ANSWER_PROCESSING_" + job.status,
                     details={"attempt_id": attempt.id, "stage": job.stage}))
        db.flush()
        session = db.scalar(select(ExamSession).where(ExamSession.id == session.id).with_for_update())
        finalize(db, session)
        db.commit()
    return True
