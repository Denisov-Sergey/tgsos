from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import config
from database.models import Base

engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Миграция: добавить category_id в channels, если ещё нет (для существующих БД)
        def _add_category_id(connection):
            from sqlalchemy import text
            from sqlalchemy.exc import OperationalError
            try:
                connection.execute(text("ALTER TABLE channels ADD COLUMN category_id INTEGER"))
            except OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise
                # колонка уже есть — игнорируем

        await conn.run_sync(lambda c: _add_category_id(c))


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
