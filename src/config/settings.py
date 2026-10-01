"""
settings.py — load environment variables once, expose them as Python names.

Any module that needs a configuration value imports from here, so the .env
file is read exactly once per process.
"""

from __future__ import annotations

import os
import pathlib

from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "minilms")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me")
SSO_MOCK_BASE_URL = os.getenv("SSO_MOCK_BASE_URL", "http://localhost:8000/mock-sso")


def describe_target() -> str:
    """Human-readable target, safe to print (no password)."""
    return f"{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"