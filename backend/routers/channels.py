import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Channel
from database.session import get_session

router = APIRouter()


def _normalize_username(identifier: str) -> str:
    s = identifier.strip()
    s = re.sub(r"^https://t\.me/", "", s)
    s = re.sub(r"^@", "", s)
    return s


class ChannelCreate(BaseModel):
    username: str
    title: str | None = None
    category_id: int | None = None


class ChannelOut(BaseModel):
    id: int
    username: str | None
    title: str
    telegram_id: int | None
    category_id: int | None
    added_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[ChannelOut])
async def list_channels(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Channel).order_by(Channel.added_at.desc()))
    channels = result.scalars().all()
    return list(channels)


@router.post("", response_model=ChannelOut)
async def add_channel(body: ChannelCreate, session: AsyncSession = Depends(get_session)):
    username = _normalize_username(body.username)
    if not username:
        raise HTTPException(status_code=400, detail="Invalid channel username or link")
    existing = await session.execute(select(Channel).where(Channel.username == username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Channel already added")
    channel = Channel(username=username, title=body.title or username, category_id=body.category_id)
    session.add(channel)
    await session.flush()
    await session.refresh(channel)
    return channel


class ChannelUpdate(BaseModel):
    title: str | None = None
    category_id: int | None = None


@router.patch("/{channel_id}", response_model=ChannelOut)
async def update_channel(channel_id: int, body: ChannelUpdate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if body.title is not None:
        channel.title = body.title
    if body.category_id is not None:
        channel.category_id = body.category_id
    await session.flush()
    await session.refresh(channel)
    return channel


@router.delete("/{channel_id}")
async def delete_channel(channel_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    await session.delete(channel)
    return {"ok": True}
