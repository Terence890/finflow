"""
Application configuration for PinkLedger (Finflow).

Provides a simple `Config` class that reads common Flask settings from the
environment with sensible defaults for local development (SQLite).
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration."""

    # Secret key for session signing — override in production with an env var.
    SECRET_KEY: str = os.environ.get("FLASK_SECRET", "dev-secret-key-change-me")

    # Database: default to a local SQLite file in the project root.
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'database.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Security & session settings
    SESSION_COOKIE_HTTPONLY: bool = True
    REMEMBER_COOKIE_HTTPONLY: bool = True
    SESSION_PERMANENT: bool = True
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(
        seconds=int(os.environ.get("SESSION_LIFETIME_SECS", 60 * 60 * 24))
    )

    # CSRF (used by Flask-WTF if installed)
    WTF_CSRF_ENABLED: bool = bool(int(os.environ.get("WTF_CSRF_ENABLED", "1")))

    # Feature toggles / environment
    ENV: str = os.environ.get("FLASK_ENV", "development")
    DEBUG: bool = bool(int(os.environ.get("FLASK_DEBUG", "0")))

    # Other application-specific defaults
    APP_NAME: str = "PinkLedger"
    DEFAULT_PAGE_SIZE: int = int(os.environ.get("PAGE_SIZE", 20))


def get_config() -> Config:
    """Return the Config class (keeps compatibility with app factories)."""
    return Config()
