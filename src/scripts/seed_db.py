import asyncio
import os
from passlib.context import CryptContext
from sqlalchemy import select
from src.accounts.models import UserGroupDB, UserDB, UserProfileDB
from src.core.database import SessionLocal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def seed_db():
    async with SessionLocal() as session:
        print("Seeding database...")

        group_mapping = {}
        groups = ["USER", "MODERATOR", "ADMIN"]

        for group_name in groups:
            stmt = select(UserGroupDB).where(UserGroupDB.name == group_name)
            result = await session.execute(stmt)
            group = result.scalars().first()

            if not group:
                print(f"   Creating group: {group_name}")
                group = UserGroupDB(name=group_name)
                session.add(group)
                await session.flush()
                await session.refresh(group)

            group_mapping[group_name] = group.id

        users_to_create = [
            {
                "email": os.getenv("ADMIN_EMAIL", "admin@cinema.com"),
                "password": os.getenv("ADMIN_PASSWORD", "!Sadmin123"),
                "first_name": "Super",
                "last_name": "Admin",
                "group_id": group_mapping["ADMIN"]
            },
            {
                "email": os.getenv("MOD_EMAIL", "moderator@cinema.com"),
                "password": os.getenv("MOD_PASSWORD", "!Smoderator123"),
                "first_name": "Cinema",
                "last_name": "Moderator",
                "group_id": group_mapping["MODERATOR"]
            }
        ]

        for user_data in users_to_create:
            stmt = select(UserDB).where(UserDB.email == user_data["email"])
            result = await session.execute(stmt)
            existing_user = result.scalars().first()

            if not existing_user:
                print(f"   Creating user: {user_data['email']}")

                new_user = UserDB(
                    email=user_data["email"],
                    hashed_password=get_password_hash(user_data["password"]),
                    is_active=True,
                    group_id=user_data["group_id"]
                )
                session.add(new_user)
                await session.flush()
                await session.refresh(new_user)

                new_profile = UserProfileDB(
                    user_id=new_user.id,
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"]
                )
                session.add(new_profile)
            else:
                print(
                    f"   User {user_data['email']} already exists. Skipping.")

        await session.commit()
        print("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_db())
