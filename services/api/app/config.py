from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./.data/app.db"
    jwt_secret: str = Field(min_length=32)
    access_minutes: int = 15
    refresh_days: int = 7
    cookie_secure: bool = False
    allowed_origins: str = "http://localhost:3000"
    storage_backend: str = "local"
    data_dir: str = ".data"
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "oral-assessment"
    redis_url: str = ""
    ai_provider: str = "demo"
    ai_config_source: Literal["env", "admin"] = "env"
    gemini_api_key: str = ""
    gemini_timeout: int = Field(default=180, ge=10, le=900)
    gemini_stt_model: str = "gemini-2.5-flash"
    local_llm_url: str = "http://127.0.0.1:11434"
    local_llm_timeout: int = Field(default=600, ge=10, le=900)
    local_review_llm_model: str = Field(default="", max_length=150, pattern=r"^[a-zA-Z0-9._:/-]*$")
    local_llm_cpu_only: bool = False
    local_llm_cpu_threads: int = Field(default=0, ge=0)
    llm_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-001"
    top_k: int = Field(default=5, ge=1, le=20)
    confidence_threshold: float = Field(default=0.85, ge=0, le=1)
    stt_provider: Literal["local", "local_server", "google", "gemini"] = "local_server"
    stt_model: str = "base"
    stt_language: str = "vi"
    stt_cpu_threads: int = Field(default=0, ge=0)
    worker_serial: bool = True
    gopt_enabled: bool = False
    gopt_url: str = "http://gopt:8000"
    gopt_timeout: int = Field(default=960, ge=30, le=3600)
    gopt_max_audio_mb: int = Field(default=24, ge=1, le=200)
    google_stt_credentials_file: str = ""
    google_login_enabled: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""
    public_origin: str = "http://localhost:3000"
    max_document_mb: int = 20
    max_textbook_mb: int = 100
    media_chunk_bytes: int = 4 * 1024 * 1024
    max_media_mb: int = 200
    bootstrap_admin: str = "admin"
    bootstrap_password: str = ""
    exam_screen_required: bool = True

    @model_validator(mode="after")
    def validate_provider(self):
        if self.ai_provider not in {"demo", "gemini", "local"}:
            raise ValueError("AI_PROVIDER must be demo, gemini or local (Ollama)")
        if self.ai_provider == "gemini" and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required")
        if self.storage_backend not in {"local", "s3"}:
            raise ValueError("STORAGE_BACKEND must be local or s3")
        return self


@lru_cache
def settings() -> Settings:
    return Settings()
