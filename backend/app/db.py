"""Veritabanı bağlantısı. Tüm modüller oturumu buradan alır."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    **({"poolclass": NullPool} if _settings.db_pool == "null" else {}),
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
