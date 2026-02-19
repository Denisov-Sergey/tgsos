"""Shared configuration from environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
TELEGRAM_SESSION_PATH = os.environ.get("TELEGRAM_SESSION_PATH", "telethon_session")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./tgsos.db")

# Ensure sync URL for SQLAlchemy when using aiosqlite (collector may use sync in some paths)
def get_sync_database_url() -> str:
    url = DATABASE_URL
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite", 1)
    return url
