from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = (BACKEND_DIR / "data" / "elysia.db").resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Project Elysia"
    app_version: str = "0.4.0"
    environment: str = "development"
    debug: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    frontend_origin: str = "http://localhost:5173"
    database_url: str = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
    log_level: str = "INFO"
    ai_provider: str = "ollama"
    ollama_base_url: AnyHttpUrl = AnyHttpUrl("http://127.0.0.1:11434")
    ollama_model: str = ""
    ollama_connect_timeout_seconds: float = Field(default=3, gt=0, le=30)
    ollama_read_timeout_seconds: float = Field(default=120, gt=0, le=600)
    ollama_keep_alive: str = "5m"
    ollama_temperature: float = Field(default=0.8, ge=0, le=2)
    ollama_top_p: float = Field(default=0.9, gt=0, le=1)
    ollama_top_k: int = Field(default=40, ge=1, le=200)
    ollama_repeat_penalty: float = Field(default=1.1, ge=0.5, le=2)
    ollama_context_size: int = Field(default=4096, ge=512, le=131072)
    ollama_max_output_tokens: int = Field(default=700, ge=32, le=4096)
    ollama_status_cache_ttl_seconds: float = Field(default=10, ge=0, le=300)
    conversation_recent_message_limit: int = Field(default=20, ge=1, le=30)
    conversation_list_default_limit: int = Field(default=20, ge=1, le=100)
    conversation_list_max_limit: int = Field(default=100, ge=1, le=200)
    message_list_default_limit: int = Field(default=50, ge=1, le=200)
    message_list_max_limit: int = Field(default=200, ge=1, le=500)
    message_max_content_length: int = Field(default=10000, ge=1, le=20000)
    conversation_lock_timeout_seconds: float = Field(default=1, gt=0, le=30)
    stream_max_accumulated_characters: int = Field(default=50000, ge=1000, le=200000)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("unsupported log level")
        return level

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme not in {"http", "https"} or value.username or value.password:
            raise ValueError("Ollama URL must use HTTP(S) without credentials")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
