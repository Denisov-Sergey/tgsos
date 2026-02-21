"""Shared configuration from environment."""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
TELEGRAM_SESSION_PATH = os.environ.get("TELEGRAM_SESSION_PATH", "telethon_session")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./tgsos.db")
# Интервал автозапуска сборщика в минутах (0 = выключено)
SCHEDULER_INTERVAL_MINUTES = int(os.environ.get("SCHEDULER_INTERVAL_MINUTES", "0"))


def validate_telegram_config() -> None:
    """Проверяет наличие API_ID и API_HASH. При невалидных значениях логирует предупреждение."""
    if not API_ID or not (isinstance(API_HASH, str) and API_HASH.strip() and "your_api" not in API_HASH.lower()):
        logger.warning(
            "API_ID или API_HASH не заданы или заданы заглушками. "
            "Получите ключи на https://my.telegram.org и укажите в .env. "
            "Сборщик и кнопка «Запустить сбор» не будут работать."
        )

# Ensure sync URL for SQLAlchemy when using aiosqlite (collector may use sync in some paths)
def get_sync_database_url() -> str:
    url = DATABASE_URL
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite", 1)
    return url
