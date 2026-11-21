"""Application configuration.

All settings come from environment variables (or a .env file at the repo root).
Nothing sensitive is ever hardcoded; defaults are non-sensitive.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: apps/api/app/config.py -> parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Core ---
    app_name: str = "Business OS"
    env: str = "development"  # development | test | production
    log_level: str = "INFO"
    api_prefix: str = "/api"

    # --- Database ---
    # SQLite by default (zero setup). PostgreSQL is supported by setting
    # DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'business_os.db'}"

    # --- Knowledge vault ---
    knowledge_dir: Path = REPO_ROOT / "knowledge"

    # --- Security ---
    auth_secret: str = Field(default="change-me-in-production")
    access_token_expire_minutes: int = 60 * 24
    admin_bootstrap: bool = False  # allow the very first user to register

    # --- AI ---
    ai_provider: str = "not-configured"  # "openai-compatible" | "not-configured"
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    ai_timeout_seconds: float = 120.0
    ai_temperature: float = 0.4
    ai_max_tokens: int = 4096
    ai_max_retries: int = 2
    ai_enabled: bool = True

    # --- Automation (n8n) ---
    n8n_enabled: bool = False
    n8n_webhook_base_url: str = ""
    n8n_api_key: str = ""

    # --- CORS (dev) ---
    cors_origins: str = "*"

    @field_validator("knowledge_dir", mode="before")
    @classmethod
    def _expand_vault(cls, v):
        p = Path(v) if not isinstance(v, Path) else v
        if not p.is_absolute():
            p = REPO_ROOT / p
        return p

    @property
    def is_dev(self) -> bool:
        return self.env == "development"

    @property
    def is_ai_configured(self) -> bool:
        return bool(self.ai_base_url and self.ai_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()
