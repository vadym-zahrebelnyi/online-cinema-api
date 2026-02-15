import argparse
import asyncio
import logging
import os
import re
import sys
from getpass import getpass

from sqlalchemy.exc import SQLAlchemyError

from src.core.database import SessionLocal
from src.db_manager.db_seeder import DatabaseSeeder

logger = logging.getLogger(__name__)


async def create_superuser_cli():
    """
    Interactively prompts for superuser credentials and creates a superuser.
    """
    logger.info("\n--- Create Superuser ---")

    email = input("Email: ").strip()
    if not email:
        logger.error("Email cannot be empty. Aborting.")
        sys.exit(1)

    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()

    while True:
        password = getpass("Password: ")
        password_confirm = getpass("Confirm Password: ")

        if password != password_confirm:
            logger.warning("Passwords do not match. Please try again.")
            continue

        if (
            len(password) < 8
            or not re.search(r"[A-Z]", password)
            or not re.search(r"[a-z]", password)
            or not re.search(r"\d", password)
        ):
            logger.warning(
                "Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, and one digit."
            )
            continue
        break

    async with SessionLocal() as session:
        seeder = DatabaseSeeder(session=session)
        try:
            await (
                seeder.seed_user_groups_and_default_users()
            )  # Ensure roles are present

            superuser = await seeder.create_superuser(
                email, password, first_name, last_name
            )
            if superuser:
                logger.info(f"Superuser '{email}' successfully created.")
            else:
                logger.info("Superuser creation skipped (user might already exist).")
        except SQLAlchemyError:
            logger.error("A database error occurred. Changes have been rolled back.")
            sys.exit(1)
        except Exception as e:
            logger.error(
                f"An unexpected error occurred: {e}. Changes have been rolled back."
            )
            sys.exit(1)


async def seed_db_cli(seed_default_users: bool, seed_movies_flag: bool):
    """
    Runs the full database seeding process including default users/groups and optionally movies.
    """
    logger.info("\n--- Database Seeding ---")
    async with SessionLocal() as session:
        movies_csv_path = None
        if seed_movies_flag:
            movies_csv_path = os.path.join(os.path.dirname(__file__), "imdb_movies.csv")
            if not os.path.exists(movies_csv_path):
                logger.warning(
                    f"Warning: Movies CSV file not found at {movies_csv_path}. Movie seeding will be skipped."
                )

        seeder = DatabaseSeeder(session=session, movies_csv_path=movies_csv_path)
        try:
            if seed_default_users:
                await seeder.seed_user_groups_and_default_users()
            if seed_movies_flag and movies_csv_path:
                await seeder.seed_movies_from_csv()

            logger.info("\nDatabase seeding process completed successfully.")
        except SQLAlchemyError as e:
            logger.error(
                f"A database error occurred during seeding: {e}. Changes have been rolled back."
            )
            sys.exit(1)
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during seeding: {e}. Changes have been rolled back."
            )
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Online Cinema API CLI for database seeding operations.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--su", action="store_true", help="Interactively create a superuser."
    )
    group.add_argument(
        "--movies", action="store_true", help="Seed movie data from 'imdb_movies.csv'."
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Seed all: default users (one per role) and all movies.",
    )

    args = parser.parse_args()

    if args.su:
        asyncio.run(create_superuser_cli())
    elif args.movies:
        asyncio.run(seed_db_cli(seed_default_users=False, seed_movies_flag=True))
    elif args.all:
        asyncio.run(seed_db_cli(seed_default_users=True, seed_movies_flag=True))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()
