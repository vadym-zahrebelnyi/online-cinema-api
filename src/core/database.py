from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.core.settings import settings


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy declarative models.

    All database models should inherit from this class to be tracked by migrations
    and the ORM.
    """

    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency generator for database sessions.

    Yields an asynchronous database session for the duration of a request.
    Ensures that the session is properly closed after the request is processed,
    even if an error occurs.

    Yields:
        AsyncSession: An active SQLAlchemy asynchronous session.
    """
    async with SessionLocal() as session:
        yield session
