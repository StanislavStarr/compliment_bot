from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session


@lru_cache
def get_celery_engine() -> AsyncEngine:
    """Отдельный engine для Celery-тасков. Каждый вызов таска оборачивается в
    свой `asyncio.run()`, то есть создаёт новый event loop — пул соединений
    обычного `get_engine()` привязан к первому loop и падает с "attached to
    a different loop" на второй задаче. `NullPool` не держит соединения
    между вызовами, поэтому каждый таск просто открывает новое."""
    settings = get_settings()
    return create_async_engine(settings.database_url, poolclass=NullPool)


@lru_cache
def get_celery_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_celery_engine(), expire_on_commit=False)
