from typing import AsyncGenerator

from redis.asyncio import Redis

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
