"""Application settings (env-overridable).

Environment variables:
  VERISENSE_SECRET   JWT signing secret (HS256)
  VERISENSE_DB       SQLAlchemy URL or path to the SQLite file (default backend/data/verisense.db)
  VERISENSE_STORAGE  directory for uploaded files (default backend/storage)
  VERISENSE_SAMPLES  directory with synthetic samples (default <repo>/samples)
  VERISENSE_AUTOSEED "1" (default) seeds the database on startup if it is empty
  VERISENSE_REFERENCE_DATE optional fixed scrutiny date (YYYY-MM-DD) for reproducible demos
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

VERSION = "0.1.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VERISENSE_", env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    secret: str = "dev-only-change-me-verisense-sih-2026"
    environment: Literal["local", "staging", "production"] = "local"
    demo_mode: bool = True
    db: str = str(BACKEND_DIR / "data" / "verisense.db")
    storage: str = str(BACKEND_DIR / "storage")
    samples: str = str(REPO_DIR / "samples")
    config_dir: str = str(BACKEND_DIR / "config")
    autoseed: bool = True
    frontend_dir: str | None = None
    ocr_threads: int = 1
    ocr_cache: bool = False
    jwt_expiry_hours: int = 8
    # optional fixed "scrutiny date" (YYYY-MM-DD) for reproducible demos; default = today
    reference_date: str | None = None
    cors_origins: str = "http://localhost:5176,http://127.0.0.1:5176"
    # minutes a scrutiny officer typically spends on manual checks (used for effort-saved estimate)
    manual_minutes_per_document: float = 12.0
    manual_minutes_per_application: float = 45.0

    @model_validator(mode="after")
    def deployment_guards(self):
        if self.environment != "local":
            if len(self.secret) < 32 or self.secret in {"dev-only-change-me-verisense-sih-2026", "change-me-to-a-long-random-string"}:
                raise ValueError("Staging/production require an explicit random VERISENSE_SECRET of at least 32 characters")
        if not self.demo_mode and self.autoseed:
            raise ValueError("Autoseed requires explicit demo mode")
        if self.environment == "production" and (self.demo_mode or self.autoseed):
            raise ValueError("Production forbids demo mode and automatic demo seeding")
        if self.jwt_expiry_hours <= 0 or self.jwt_expiry_hours > 24:
            raise ValueError("JWT expiry must be greater than zero and at most 24 hours")
        return self

    @property
    def db_url(self) -> str:
        if "://" in self.db:
            return self.db
        Path(self.db).parent.mkdir(parents=True, exist_ok=True)
        return "sqlite:///" + Path(self.db).as_posix()

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
