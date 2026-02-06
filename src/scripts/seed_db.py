import asyncio
from sqlalchemy import select
from src.core.database import SessionLocal
from src.accounts.models import UserGroupDB

async def seed_groups():
    async with SessionLocal() as session:
        groups = ["USER", "MODERATOR", "ADMIN"]
        for group_name in groups:
            query = select(UserGroupDB).where(UserGroupDB.name == group_name)
            result = await session.execute(query)
            if not result.scalars().first():
                session.add(UserGroupDB(name=group_name))
        await session.commit()

if __name__ == "__main__":
    asyncio.run(seed_groups())