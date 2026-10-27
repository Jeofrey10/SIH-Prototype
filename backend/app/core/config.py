"""AICTE Complaint Dashboard - Application Configuration."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_ENV: str = Field(default="development")
    DATABASE_URL: str = Field(default="postgresql+psycopg://aicte:aicte_dev_pw@localhost:5432/aicte_dashboard")
    TEST_DATABASE_URL: str = Field(default="postgresql+psycopg://aicte:aicte_dev_pw@localhost:5432/aicte_dashboard_test")
    SECRET_KEY: str = Field(default="change-me-in-real-use")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    APP_TIMEZONE: str = Field(default="Asia/Kolkata")
    FRONTEND_ORIGIN: str = Field(default="http://localhost:5173")
    ENABLE_SCHEDULER: bool = Field(default=True)
    OVERDUE_SCAN_INTERVAL_MINUTES: int = Field(default=15)
    DEMO_PASSWORD: str = Field(default="Demo@12345")
    LOG_LEVEL: str = Field(default="INFO")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def app_env(self) -> str:
        return self.APP_ENV

    @property
    def database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://"):]
        if url.startswith("postgresql://") and not url.startswith("postgresql+"):
            return "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @property
    def test_database_url(self) -> str:
        return self.TEST_DATABASE_URL

    @property
    def secret_key(self) -> str:
        return self.SECRET_KEY

    @property
    def access_token_expire_minutes(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def frontend_origin(self) -> str:
        return self.FRONTEND_ORIGIN

    @property
    def enable_scheduler(self) -> bool:
        return self.ENABLE_SCHEDULER

    @property
    def overdue_scan_interval_minutes(self) -> int:
        return self.OVERDUE_SCAN_INTERVAL_MINUTES

    @property
    def demo_password(self) -> str:
        return self.DEMO_PASSWORD

    def validate_production(self) -> None:
        """Refuse to start with insecure defaults in production."""
        if self.APP_ENV == "production":
            if self.SECRET_KEY == "change-me-in-real-use":
                raise RuntimeError("SECRET_KEY must be changed from default in production")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        os.environ.setdefault("ENV_FILE", str(env_path))
    settings = Settings()
    settings.validate_production()
    return settings
