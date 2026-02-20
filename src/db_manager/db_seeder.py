import csv
import logging
import os
from datetime import datetime
from decimal import Decimal

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import UserDB, UserGroupDB, UserProfileDB
from src.movies.models import CertificationDB, DirectorDB, GenreDB, MovieDB, StarDB

logger = logging.getLogger(__name__)


class DatabaseSeeder:
    """
    A comprehensive seeder class for populating the online-cinema-api database.
    It combines logic for seeding user groups, initial users, and movie data from a CSV file.
    """

    def __init__(self, session: AsyncSession, movies_csv_path: str | None = None):
        self.session = session
        self.movies_csv_path = movies_csv_path
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        logger.info(
            f"DatabaseSeeder initialized. Movies CSV path: {self.movies_csv_path or 'Not provided'}"
        )

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    async def get_or_create(self, model, **kwargs):
        """
        Helper function to get an instance of a model or create it if it doesn't exist.
        """
        stmt = select(model).filter_by(**kwargs)
        result = await self.session.execute(stmt)
        instance = result.scalars().first()
        if instance:
            return instance
        else:
            instance = model(**kwargs)
            self.session.add(instance)
            await self.session.flush()
            return instance

    async def seed_user_groups_and_default_users(self):
        """
        Ensures default user groups are present and seeds initial admin/moderator users
        from environment variables.
        """
        logger.info("Ensuring user groups are present and seeding default users...")
        group_mapping = {}
        groups = ["USER", "MODERATOR", "ADMIN"]

        for group_name in groups:
            group = await self.get_or_create(UserGroupDB, name=group_name)
            group_mapping[group_name] = group.id
            logger.info(f"  User group '{group_name}' (ID: {group.id}) ensured.")

        users_to_create = [
            {
                "email": os.getenv("ADMIN_EMAIL", "admin@cinema.com"),
                "password": os.getenv("ADMIN_PASSWORD", "!Sadmin_p@ss123"),
                "first_name": "Super",
                "last_name": "Admin",
                "group_id": group_mapping["ADMIN"],
            },
            {
                "email": os.getenv("MOD_EMAIL", "moderator@cinema.com"),
                "password": os.getenv("MOD_PASSWORD", "!Smoderator_p@ss123"),
                "first_name": "Cinema",
                "last_name": "Moderator",
                "group_id": group_mapping["MODERATOR"],
            },
            {
                "email": os.getenv("USER_EMAIL", "user@cinema.com"),
                "password": os.getenv("USER_PASSWORD", "!Suser_p@ss123"),
                "first_name": "Cinema",
                "last_name": "User",
                "group_id": group_mapping["USER"],
            },
        ]

        for user_data in users_to_create:
            stmt = select(UserDB).where(UserDB.email == user_data["email"])
            result = await self.session.execute(stmt)
            existing_user = result.scalars().first()

            if not existing_user:
                new_user = UserDB(
                    email=user_data["email"],
                    hashed_password=self.get_password_hash(user_data["password"]),
                    is_active=True,
                    group_id=user_data["group_id"],
                )
                self.session.add(new_user)
                await self.session.flush()
                await self.session.refresh(new_user)

                new_profile = UserProfileDB(
                    user_id=new_user.id,
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                )
                self.session.add(new_profile)
                logger.info(f"  Added default user: '{new_user.email}'")
            else:
                logger.info(
                    f"  Default user '{user_data['email']}' already exists. Skipping."
                )

        await self.session.commit()
        logger.info("Default user groups and users seeding completed.")

    async def create_superuser(
        self, email: str, password: str, first_name: str, last_name: str
    ) -> UserDB | None:
        """
        Creates a superuser (admin) with the given credentials.
        Ensures ADMIN group exists.
        Returns the created UserDB object or None if user already exists or an error occurs.
        """
        logger.info(f"Attempting to create superuser: {email}...")
        try:
            admin_group = await self.get_or_create(UserGroupDB, name="ADMIN")
            if not admin_group:
                logger.error(
                    "Error: Could not ensure ADMIN group exists for superuser creation."
                )
                return None

            stmt = select(UserDB).where(UserDB.email == email)
            result = await self.session.execute(stmt)
            existing_user = result.scalars().first()

            if existing_user:
                logger.info(f"Superuser '{email}' already exists. Skipping creation.")
                return None

            new_user = UserDB(
                email=email,
                hashed_password=self.get_password_hash(password),
                is_active=True,
                group_id=admin_group.id,
            )
            self.session.add(new_user)
            await self.session.flush()
            await self.session.refresh(new_user)

            new_profile = UserProfileDB(
                user_id=new_user.id,
                first_name=first_name,
                last_name=last_name,
            )
            self.session.add(new_profile)

            await self.session.commit()
            logger.info(f"Superuser '{email}' created successfully.")
            return new_user
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Database error creating superuser '{email}': {e}")
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating superuser '{email}': {e}")
            raise

    async def seed_movies_from_csv(self):
        """
        Seeds movie data from the specified CSV file into the database.
        """
        if not self.movies_csv_path:
            logger.info("Movies CSV path not provided. Skipping movie seeding.")
            return

        logger.info(f"Seeding movies from: {self.movies_csv_path}...")

        if not os.path.exists(self.movies_csv_path):
            logger.error(
                f"Error: CSV file not found at {self.movies_csv_path}. Skipping movie seeding."
            )
            return

        default_certification = await self.get_or_create(
            CertificationDB, name="Not Rated"
        )
        logger.info(
            f"  Default certification '{default_certification.name}' (ID: {default_certification.id}) ensured."
        )

        with open(self.movies_csv_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    name = row.get("names") or row.get("orig_title")
                    if not name:
                        logger.warning(f"  Skipping row due to missing name: {row}")
                        continue

                    year = None
                    date_x = row.get("date_x")
                    if date_x:
                        try:
                            year = datetime.strptime(date_x, "%Y-%m-%d").year
                        except ValueError:
                            logger.warning(
                                f"  Warning: Could not parse year from date_x '{date_x}' for movie '{name}'. Skipping movie."
                            )
                            continue

                    score_str = row.get("score")
                    imdb_score = Decimal(score_str) if score_str else Decimal("0")

                    description = row.get("overview", "")
                    revenue_str = row.get("revenue")
                    gross = None
                    if revenue_str and revenue_str != "0.0":
                        try:
                            gross = Decimal(revenue_str)
                        except Exception:
                            logger.warning(
                                f"  Warning: Could not parse revenue '{revenue_str}' for movie '{name}'. Setting gross to None."
                            )

                    movie_genres_list: list[GenreDB] = []
                    genre_str = row.get("genre")
                    if genre_str:
                        for g_name in genre_str.split(","):
                            stripped_g_name = g_name.strip()
                            if stripped_g_name:
                                genre_obj = await self.get_or_create(
                                    GenreDB, name=stripped_g_name
                                )
                                movie_genres_list.append(genre_obj)

                    movie_stars_list: list[StarDB] = []
                    movie_directors_list: list[DirectorDB] = []
                    crew_str = row.get("crew")
                    if crew_str:
                        for c_name in crew_str.split(","):
                            stripped_c_name = c_name.strip()
                            if stripped_c_name:
                                star_obj = await self.get_or_create(
                                    StarDB, name=stripped_c_name
                                )
                                movie_stars_list.append(star_obj)

                                director_obj = await self.get_or_create(
                                    DirectorDB, name=stripped_c_name
                                )
                                movie_directors_list.append(director_obj)

                    time_placeholder = 120
                    votes_placeholder = 0
                    meta_score_placeholder = None
                    price_placeholder = Decimal(9.99)

                    stmt = select(MovieDB).where(
                        MovieDB.name == name, MovieDB.year == year
                    )
                    existing_movie = await self.session.execute(stmt)
                    if existing_movie.scalars().first():
                        logger.info(f"  Skipping existing movie: '{name}' ({year})")
                        continue

                    new_movie = MovieDB(
                        name=name,
                        year=year,
                        time=time_placeholder,
                        imdb=imdb_score,
                        votes=votes_placeholder,
                        meta_score=meta_score_placeholder,
                        gross=gross,
                        price=price_placeholder,
                        description=description,
                        certification_id=default_certification.id,
                        genres=movie_genres_list,
                        stars=movie_stars_list,
                        directors=movie_directors_list,
                    )
                    self.session.add(new_movie)
                    await self.session.flush()

                    logger.info(f"  Added movie: '{new_movie.name}' ({new_movie.year})")

                except Exception as e:
                    logger.error(
                        f"  Error processing row for movie '{row.get('names') or row.get('orig_title')}': {e}"
                    )
            await self.session.commit()
        logger.info("Movie seeding completed.")

    async def seed_all(self):
        """
        Orchestrates the entire database seeding process.
        """
        logger.info("Starting full database seeding process...")
        await self.seed_user_groups_and_default_users()
        await self.seed_movies_from_csv()
        logger.info("Full database seeding process completed.")
