from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import Category, Channel
from database.session import get_session

router = APIRouter()


class CategoryCreate(BaseModel):
    name: str


class CategoryOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[CategoryOut])
async def list_categories(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Category).order_by(Category.name))
    return list(result.scalars().all())


@router.post("", response_model=CategoryOut)
async def create_category(body: CategoryCreate, session: AsyncSession = Depends(get_session)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required")
    existing = await session.execute(select(Category).where(Category.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Category already exists")
    category = Category(name=name)
    session.add(category)
    await session.flush()
    await session.refresh(category)
    return category


@router.delete("/{category_id}")
async def delete_category(category_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    await session.execute(update(Channel).where(Channel.category_id == category_id).values(category_id=None))
    await session.delete(category)
    return {"ok": True}
