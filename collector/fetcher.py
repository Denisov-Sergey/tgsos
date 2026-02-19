"""Telethon-based fetcher: reads messages from channels and saves to DB."""
import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient
from telethon.tl.types import Message, MessageMediaDocument, MessageMediaPhoto

import config
from database.models import Channel as ChannelModel, Post


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


async def run_once(limit_per_channel: int = 200) -> None:
    """Load all channels from DB, connect with Telethon, fetch messages for each."""
    from database.session import async_session_maker, init_db

    await init_db()

    client = TelegramClient(
        config.TELEGRAM_SESSION_PATH,
        config.API_ID,
        config.API_HASH,
    )
    await client.start()

    async with async_session_maker() as db:
        result = await db.execute(select(ChannelModel))
        channels = result.scalars().all()

    for ch in channels:
        async with async_session_maker() as db:
            try:
                n = await fetch_channel(client, db, ch, limit=limit_per_channel)
                print(f"Channel {ch.title} (@{ch.username}): {n} posts processed")
            except Exception as e:
                print(f"Channel {ch.title}: error - {e}")

    await client.disconnect()
