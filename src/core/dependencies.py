from typing import AsyncGenerator

from fastapi import Query
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import SessionLocal
from src.core.settings import settings


async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    Dependency generator for the Redis client.

    Creates a connection to the Redis server using settings from the environment.
    The client is configured to decode responses (str instead of bytes).
    Ensures the connection is closed after use.

    Yields:
        Redis: An active, asynchronous Redis client.
    """
    redis = Redis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True
    )
    try:
        yield redis
    finally:
        await redis.close()


class PaginationParams(BaseModel):
    limit: int
    offset: int


def get_pagination(
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PaginationParams:
    return PaginationParams(limit=limit, offset=offset)


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
