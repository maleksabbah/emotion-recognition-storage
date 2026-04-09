"""
Database setup — async SQLAlchemy engine and session factory.

Engine creation is lazy to allow tests to override DATABASE_URL.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncEngine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine: Optional[AsyncEngine] = None
_async_session: Optional[async_sessionmaker] = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        from app.Config import DATABASE_URL
        _engine = create_async_engine(DATABASE_URL, echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker:
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _async_session


async def get_db():
    """FastAPI dependency — yields an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db():
    """Create all tables on startup."""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)