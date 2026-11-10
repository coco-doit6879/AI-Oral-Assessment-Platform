import hashlib
import re
import tempfile
import unicodedata
from contextlib import closing
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select

from . import diagnostics, speech, storage
from .models import Upload
from .runtime_settings import settings

FAILURE_MESSAGES = {
    "GOPT_DISABLED": "Dịch vụ chấm phát âm GOPT đang tắt trên worker.",
    "LANGUAGE_UNSUPPORTED": "Chấm phát âm GOPT yêu cầu ngôn ngữ của lượt chấm là tiếng Anh (en).",
    "TRANSCRIPT_EMPTY": "Không có transcript để đối chiếu phát âm với audio.",
    "AUDIO_MISSING": "Không tìm thấy audio gốc đã upload hoàn tất.",
    "AUDIO_TOO_LARGE": "Audio vượt giới hạn dung lượng chấm phát âm.",
    "AUDIO_CHECKSUM_MISMATCH": "Audio tải về không khớp dung lượng hoặc checksum của bản gốc.",
    "AUDIO_READ_FAILED": "Không đọc được audio gốc từ kho lưu trữ.",
    "GOPT_TIMEOUT": "GOPT chưa phản hồi trong thời gian chờ.",
    "GOPT_CONNECTION_FAILED": "Worker không kết nối được tới dịch vụ GOPT.",
    "GOPT_BUSY": "GOPT đang bận xử lý bài khác; chờ hoàn tất rồi chấm lại.",
    "GOPT_INPUT_REJECTED": "GOPT không xử lý/căn chỉnh được audio với transcript tiếng Anh.",
    "GOPT_HTTP_ERROR": "Dịch vụ GOPT trả lỗi HTTP; admin cần kiểm tra log GOPT.",
    "GOPT_INVALID_RESPONSE": "GOPT trả kết quả không hợp lệ với định dạng hoặc thang điểm yêu cầu.",
    "GOPT_FAILED": "Chưa chấm được phát âm; admin cần kiểm tra log GOPT.",
}


class PronunciationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(FAILURE_MESSAGES[code])


def failure_reason(exc, phase):
    if isinstance(exc, PronunciationError):
        return exc.code
    if phase == "audio":
        return "AUDIO_READ_FAILED"
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return "GOPT_TIMEOUT"
    if isinstance(exc, httpx.RequestError):
        return "GOPT_CONNECTION_FAILED"
    if isinstance(exc, httpx.HTTPStatusError):
        return {413: "AUDIO_TOO_LARGE", 422: "GOPT_INPUT_REJECTED", 429: "GOPT_BUSY",
                504: "GOPT_TIMEOUT"}.get(exc.response.status_code, "GOPT_HTTP_ERROR")
    if isinstance(exc, ValidationError) or phase == "response":
        return "GOPT_INVALID_RESPONSE"
    return "GOPT_FAILED"


def failure_message(result):
    code = result.get("reason_code", "GOPT_FAILED")
    return FAILURE_MESSAGES.get(code, FAILURE_MESSAGES["GOPT_FAILED"])


class Scores(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    accuracy: float = Field(ge=0, le=10)
    completeness: float = Field(ge=0, le=10)
    fluency: float = Field(ge=0, le=10)
    prosody: float = Field(ge=0, le=10)
    total: float = Field(ge=0, le=10)


class PronunciationResult(BaseModel):
    status: Literal["COMPLETED"]
    model: Literal["gopt-librispeech"]
    model_revision: str = Field(min_length=1, max_length=100)
    scores: Scores
    segments: int = Field(ge=1, le=200)
    phones: int = Field(ge=1, le=10000)
    reference_source: Literal["transcript"]


def is_criterion(criterion):
    name = "".join(char for char in unicodedata.normalize("NFKD", criterion["name"].casefold())
                   if not unicodedata.combining(char))
    return bool(re.search(r"\b(pronunciation|pronounce|phat\s+am)\b", name))


def assess(db, exam, attempt, transcript, assessment):
    cfg = settings()
    criteria = exam.snapshot.get("criteria", [])
    required = [criterion for criterion in criteria if is_criterion(criterion)]
    if not required or exam.snapshot.get("practice"):
        return assessment
    phase = "policy"
    try:
        if not cfg.gopt_enabled:
            raise PronunciationError("GOPT_DISABLED")
        language = getattr(attempt, "pronunciation_language", None) or speech.exam_policy(db, exam)["language"]
        if language != "en":
            raise PronunciationError("LANGUAGE_UNSUPPORTED")
        if not transcript or not transcript.strip():
            raise PronunciationError("TRANSCRIPT_EMPTY")
        query = select(Upload).where(
            Upload.attempt_id == attempt.id, Upload.kind == "AUDIO", Upload.status == "COMPLETED",
        )
        if getattr(attempt, "pronunciation_audio_id", None):
            query = query.where(Upload.id == attempt.pronunciation_audio_id)
        audio = db.scalar(query.order_by(Upload.created_at, Upload.id))
        limit = cfg.gopt_max_audio_mb * 1024 * 1024
        if not audio or not audio.storage_key:
            raise PronunciationError("AUDIO_MISSING")
        if audio.size > limit:
            raise PronunciationError("AUDIO_TOO_LARGE")
        phase = "audio"
        digest, size = hashlib.sha256(), 0
        with tempfile.TemporaryFile() as target:
            with closing(storage.open_stream(audio.storage_key)) as source:
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    if size > limit:
                        raise PronunciationError("AUDIO_TOO_LARGE")
                    digest.update(chunk)
                    target.write(chunk)
            if size != audio.size or digest.hexdigest() != audio.sha256:
                raise PronunciationError("AUDIO_CHECKSUM_MISMATCH")
            target.seek(0)
            phase = "request"
            with diagnostics.operation("gopt.assess", provider="gopt", model="gopt-librispeech",
                                       timeout_seconds=cfg.gopt_timeout, audio_bytes=size), \
                    httpx.Client(timeout=httpx.Timeout(cfg.gopt_timeout, connect=5), trust_env=False) as client:
                response = client.post(cfg.gopt_url.rstrip("/") + "/assess",
                    data={"transcript": transcript}, files={"audio": ("answer.webm", target, audio.mime_type)})
                response.raise_for_status()
                phase = "response"
                result = PronunciationResult.model_validate(response.json()).model_dump()
        result["audio_sha256"] = audio.sha256
        result["transcript_sha256"] = hashlib.sha256(transcript.encode()).hexdigest()
    except Exception as exc:
        reason = failure_reason(exc, phase)
        diagnostics.failed("gopt.pronunciation", exc, attempt_id=attempt.id, gopt_enabled=cfg.gopt_enabled,
                           provider="gopt", model="gopt-librispeech", code="PRONUNCIATION_FAILED", reason_code=reason)
        result = {"status": "FAILED", "model": "gopt-librispeech", "error_code": "PRONUNCIATION_FAILED",
                  "reason_code": reason, "message": FAILURE_MESSAGES[reason]}
    assessment = assessment | {"pronunciation": result, "rubric_criteria": criteria, "review_required": True}
    if result["status"] == "FAILED":
        return assessment | {"score": None, "status": "FAILED", "error_code": "PRONUNCIATION_FAILED"}
    actual = {criterion["name"]: criterion for criterion in assessment.get("criteria", [])}
    for criterion in required:
        actual[criterion["name"]] = {
            "name": criterion["name"], "score": result["scores"]["total"] / 10 * criterion["max_score"],
            "comment": "Chấm từ audio gốc bằng GOPT; cần giảng viên đối chiếu bản ghi và transcript.",
            "source": "gopt",
        }
    result["applied_criteria"] = [criterion["name"] for criterion in required]
    if set(actual) != {criterion["name"] for criterion in criteria} or assessment.get("status") != "COMPLETED":
        return assessment | {"score": None}
    score = round(10 * sum(actual[criterion["name"]]["score"] / criterion["max_score"] * criterion["weight"]
                           for criterion in criteria) / sum(criterion["weight"] for criterion in criteria), 2)
    return assessment | {"score": score, "criteria": [actual[criterion["name"]] for criterion in criteria]}
