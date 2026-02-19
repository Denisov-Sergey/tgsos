from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import Channel, Post, Category
from database.session import get_session

router = APIRouter()


class PostOut(BaseModel):
    id: int
    channel_id: int
    message_id: int
    text: Optional[str]
    date: datetime
    raw_link: Optional[str]
    media_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PostWithChannel(PostOut):
    channel_title: str
    channel_username: Optional[str] = None
    category_name: Optional[str] = None


class PostsPage(BaseModel):
    items: list[PostWithChannel]
    total: int
    page: int
    page_size: int


@router.get("", response_model=PostsPage)
async def list_posts(
    channel_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    q = select(Post).join(Channel).order_by(Post.date.desc())
    count_q = select(func.count()).select_from(Post).join(Channel)
    if channel_id is not None:
        q = q.where(Post.channel_id == channel_id)
        count_q = count_q.where(Post.channel_id == channel_id)
    if category_id is not None:
        q = q.where(Channel.category_id == category_id)
        count_q = count_q.where(Channel.category_id == category_id)
    if from_date is not None:
        q = q.where(Post.date >= from_date)
        count_q = count_q.where(Post.date >= from_date)
    if to_date is not None:
        q = q.where(Post.date <= to_date)
        count_q = count_q.where(Post.date <= to_date)
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.where(Post.text.isnot(None), Post.text.ilike(term))
        count_q = count_q.where(Post.text.isnot(None), Post.text.ilike(term))

    total_result = await session.execute(count_q)
    total = total_result.scalar() or 0

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    posts = result.scalars().all()
    channel_ids = list({p.channel_id for p in posts})
    channels_map = {}
    category_ids = set()
    if channel_ids:
        ch_result = await session.execute(select(Channel).where(Channel.id.in_(channel_ids)))
        for ch in ch_result.scalars().all():
            channels_map[ch.id] = ch
            if ch.category_id:
                category_ids.add(ch.category_id)
    categories_map = {}
    if category_ids:
        cat_result = await session.execute(select(Category).where(Category.id.in_(category_ids)))
        for c in cat_result.scalars().all():
            categories_map[c.id] = c.name

    items = []
    for p in posts:
        ch = channels_map.get(p.channel_id)
        cat_name = categories_map.get(ch.category_id) if ch and ch.category_id else None
        items.append(PostWithChannel(
            **{k: getattr(p, k) for k in PostOut.model_fields},
            channel_title=ch.title if ch else "",
            channel_username=ch.username if ch else None,
            category_name=cat_name,
        ))
    return PostsPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{post_id}", response_model=PostWithChannel)
async def get_post(post_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Post not found")
    ch_result = await session.execute(select(Channel).where(Channel.id == post.channel_id))
    ch = ch_result.scalar_one_or_none()
    category_name = None
    if ch and ch.category_id:
        c_result = await session.execute(select(Category).where(Category.id == ch.category_id))
        cat = c_result.scalar_one_or_none()
        category_name = cat.name if cat else None
    return PostWithChannel(
        **{k: getattr(post, k) for k in PostOut.model_fields},
        channel_title=ch.title if ch else "",
        channel_username=ch.username if ch else None,
        category_name=category_name,
    )
