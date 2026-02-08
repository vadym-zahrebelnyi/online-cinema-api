from redis.asyncio import Redis

from src.core.settings import settings


async def get_redis() -> Redis:
    redis = Redis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True
    )
    try:
        yield redis
    finally:
        await redis.close()
