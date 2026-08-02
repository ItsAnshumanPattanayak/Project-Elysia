from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
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
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    frontend_origin: str = "http://localhost:5173"
    database_url: str = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("unsupported log level")
        return level


@lru_cache
def get_settings() -> Settings:
    return Settings()
