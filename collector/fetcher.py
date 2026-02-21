"""Telethon-based fetcher: reads messages from channels and saves to DB."""
import asyncio
import logging
import sys
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient
from telethon import errors as telethon_errors
from telethon.tl.types import Message, MessageMediaDocument, MessageMediaPhoto

import config
from database.models import Channel as ChannelModel, Post

logger = logging.getLogger(__name__)


def _message_media_type(msg: Message) -> Optional[str]:
    if msg.media is None:
        return None
    if isinstance(msg.media, MessageMediaPhoto):
        return "photo"
    if isinstance(msg.media, MessageMediaDocument):
        return "document"
    return "other"


def _build_post_link(channel_username: Optional[str], channel_telegram_id: Optional[int], message_id: int) -> str:
    if channel_username:
        return f"https://t.me/{channel_username}/{message_id}"
    if channel_telegram_id:
        return f"https://t.me/c/{str(channel_telegram_id).replace('-100', '')}/{message_id}"
    return ""


def normalize_auth_error(exc: Exception) -> dict[str, str]:
    """Normalize Telethon auth/runtime errors into user-friendly diagnostics."""
    name = type(exc).__name__
    raw_message = str(exc) or name
    message_lc = raw_message.lower()

    if name in {"ApiIdInvalidError", "ApiIdPublishedFloodError"} or "api_id" in message_lc:
        return {
            "code": "invalid_api_credentials",
            "message": "API_ID/API_HASH невалидны или заблокированы.",
            "hint": "Проверьте значения API_ID и API_HASH в .env (my.telegram.org), затем перезапустите контейнеры.",
        }
    if name == "PhoneNumberInvalidError":
        return {
            "code": "invalid_phone",
            "message": "Некорректный номер телефона.",
            "hint": "Введите номер в международном формате, например +79991234567.",
        }
    if name in {"PhoneCodeInvalidError", "CodeInvalidError"}:
        return {
            "code": "invalid_code",
            "message": "Неверный код подтверждения Telegram.",
            "hint": "Запросите новый код и введите последние 5 цифр из сообщения Telegram.",
        }
    if name in {"PhoneCodeExpiredError", "CodeExpiredError"}:
        return {
            "code": "expired_code",
            "message": "Код подтверждения истёк.",
            "hint": "Запустите отправку кода повторно и введите свежий код.",
        }
    if name in {"SessionPasswordNeededError"}:
        return {
            "code": "password_required",
            "message": "Для аккаунта включена двухфакторная защита Telegram.",
            "hint": "Введите пароль 2FA после проверки кода.",
        }
    if name in {"PasswordHashInvalidError"}:
        return {
            "code": "invalid_password",
            "message": "Неверный пароль 2FA.",
            "hint": "Проверьте пароль двухфакторной аутентификации и попробуйте снова.",
        }
    if name in {"FloodWaitError", "PhoneNumberFloodError"}:
        seconds = getattr(exc, "seconds", None)
        wait_note = f" Подождите {seconds} сек." if seconds else ""
        return {
            "code": "flood_wait",
            "message": f"Telegram временно ограничил попытки входа.{wait_note}".strip(),
            "hint": "Подождите и повторите позже. Частые повторы входа могут увеличивать блокировку.",
        }
    if name in {"TimeoutError"} or "timeout" in message_lc:
        return {
            "code": "network_timeout",
            "message": "Таймаут подключения к Telegram.",
            "hint": "Проверьте интернет/прокси/DNS и повторите попытку.",
        }
    if isinstance(exc, telethon_errors.RPCError):
        return {
            "code": "telegram_rpc_error",
            "message": f"Ошибка Telegram API: {raw_message}",
            "hint": "Повторите попытку позже. Если ошибка сохраняется, включите debug-логи и проверьте ограничения Telegram.",
        }
    return {
        "code": "unknown_error",
        "message": raw_message,
        "hint": "Проверьте логи collector и параметры .env, затем повторите попытку.",
    }


async def fetch_channel(
    client: TelegramClient,
    db: AsyncSession,
    channel_model: ChannelModel,
    limit: int = 200,
) -> int:
    """
    Fetch up to `limit` messages from the channel and upsert into posts.
    Returns number of new/updated posts.
    """
    count = 0
    channel_entity = await client.get_entity(channel_model.telegram_id or channel_model.username or channel_model.id)
    username = getattr(channel_entity, "username", None) or channel_model.username
    telegram_id = getattr(channel_entity, "id", None)
    # Persist telegram_id/username for next runs
    if telegram_id and channel_model.telegram_id != telegram_id:
        channel_model.telegram_id = telegram_id
    if username and channel_model.username != username:
        channel_model.username = username
    await db.flush()

    async for message in client.iter_messages(channel_entity, limit=limit):
        if not isinstance(message, Message):
            continue
        text = message.message or ""
        msg_date = message.date
        media_type = _message_media_type(message)
        raw_link = _build_post_link(username, telegram_id, message.id)

        stmt = sqlite_upsert(Post).values(
            channel_id=channel_model.id,
            message_id=message.id,
            text=text or None,
            date=msg_date,
            raw_link=raw_link or None,
            media_type=media_type,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["channel_id", "message_id"],
            set_={
                "text": text or None,
                "date": msg_date,
                "raw_link": raw_link or None,
                "media_type": media_type,
            },
        )
        await db.execute(stmt)
        count += 1

    await db.commit()
    return count


async def check_session_authorized() -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Проверяет, авторизована ли сессия Telegram (без интерактивного ввода).
    Возвращает:
      (authorized, error_message, error_code, error_hint).
    error_* заполнены при authorized=False.
    """
    from database.session import init_db

    await init_db()
    client = TelegramClient(
        config.TELEGRAM_SESSION_PATH,
        config.API_ID,
        config.API_HASH,
    )
    logger.info("Session check started (path=%s)", config.TELEGRAM_SESSION_PATH)
    try:
        logger.info("Connecting Telegram client for session check")
        await client.connect()
        logger.info("Telegram client connected for session check")
        if await client.is_user_authorized():
            logger.info("Session is authorized")
            return True, None, None, None
        logger.warning("Session is not authorized")
        return (
            False,
            "Сессия не авторизована. Выполните вход через UI или один раз: docker compose run --rm -it collector",
            "session_not_authorized",
            "Сделайте вход в Telegram и повторите запуск сборщика.",
        )
    except Exception as e:
        diag = normalize_auth_error(e)
        logger.exception("Session check failed: code=%s message=%s", diag["code"], diag["message"])
        return False, diag["message"], diag["code"], diag["hint"]
    finally:
        try:
            logger.info("Disconnecting Telegram client for session check")
            await client.disconnect()
        except Exception:
            logger.exception("Failed to disconnect Telegram client after session check")
            pass


async def run_once(limit_per_channel: int = 200) -> None:
    """Load all channels from DB, connect with Telethon, fetch messages for each."""
    from database.session import async_session_maker, init_db

    await init_db()

    client = TelegramClient(
        config.TELEGRAM_SESSION_PATH,
        config.API_ID,
        config.API_HASH,
    )
    logger.info("Collector started (limit_per_channel=%s)", limit_per_channel)
    if sys.stdin.isatty():
        logger.info("Interactive terminal detected, starting Telegram interactive auth flow")
        print(
            "\n--- Авторизация Telegram ---\n"
            "Код придёт только в приложение Telegram (на телефон или другой уже войдящий клиент),\n"
            "не по SMS. Откройте Telegram и проверьте уведомление или чат «Telegram» с кодом.\n"
        )
        try:
            await client.start()
            logger.info("Interactive auth flow finished successfully")
        except Exception as e:
            diag = normalize_auth_error(e)
            logger.exception("Interactive auth failed: code=%s message=%s", diag["code"], diag["message"])
            raise RuntimeError(f"{diag['message']} {diag['hint']}") from e
    else:
        logger.info("Non-interactive mode, checking existing Telegram session")
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            logger.warning("Collector run aborted: session is not authorized")
            raise RuntimeError(
                "Сессия Telegram не авторизована. Выполните вход через UI или один раз запустите "
                "сборщик в интерактивном режиме: docker compose run --rm -it collector"
            )

    async with async_session_maker() as db:
        result = await db.execute(select(ChannelModel))
        channels = result.scalars().all()
    logger.info("Channels loaded for collection: %s", len(channels))

    for ch in channels:
        async with async_session_maker() as db:
            try:
                n = await fetch_channel(client, db, ch, limit=limit_per_channel)
                print(f"Channel {ch.title} (@{ch.username}): {n} posts processed")
                logger.info("Channel processed: id=%s title=%s posts=%s", ch.id, ch.title, n)
            except Exception as e:
                print(f"Channel {ch.title}: error - {e}")
                logger.exception("Channel processing failed: id=%s title=%s", ch.id, ch.title)

    await client.disconnect()
    logger.info("Collector finished")


async def get_telegram_client() -> TelegramClient:
    """Factory for auth API and collector to keep init consistent."""
    client = TelegramClient(
        config.TELEGRAM_SESSION_PATH,
        config.API_ID,
        config.API_HASH,
    )
    return client
