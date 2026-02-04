from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.core import settings


# POSTGRESQL_DATABASE_URL = (
#     f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@"
#     f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
# )
POSTGRESQL_DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/online_cinema_db"

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
    connect_args={"check_same_thread": False}
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session