from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.movies import models, schemas

# -------------------
# GENRES
# -------------------

async def create_genre(db: AsyncSession, name: str) -> models.GenreDB:
    genre = models.GenreDB(name=name)
    db.add(genre)
    await db.commit()
    await db.refresh(genre)
    return genre

async def get_genre_by_id(db: AsyncSession, genre_id: int) -> models.GenreDB | None:
    return await db.get(models.GenreDB, genre_id)

async def get_genre_by_name(db: AsyncSession, name: str) -> models.GenreDB | None:
    result = await db.execute(select(models.GenreDB).where(models.GenreDB.name == name))
    return result.scalar_one_or_none()

async def get_all_genres(db: AsyncSession) -> list[models.GenreDB]:
    result = await db.execute(select(models.GenreDB))
    return result.scalars().all()

async def update_genre(db: AsyncSession, genre_id: int, new_name: str) -> models.GenreDB | None:
    genre = await db.get(models.GenreDB, genre_id)
    if genre:
        genre.name = new_name
        await db.commit()
        await db.refresh(genre)
    return genre

async def delete_genre(db: AsyncSession, genre_id: int) -> None:
    genre = await db.get(models.GenreDB, genre_id)
    if genre:
        await db.delete(genre)
        await db.commit()

# -------------------
# CERTIFICATIONS
# -------------------

async def create_certification(db: AsyncSession, name: str) -> models.CertificationDB:
    cert = models.CertificationDB(name=name)
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert

async def get_certification_by_id(db: AsyncSession, cert_id: int) -> models.CertificationDB | None:
    return await db.get(models.CertificationDB, cert_id)

async def get_all_certifications(db: AsyncSession) -> list[models.CertificationDB]:
    result = await db.execute(select(models.CertificationDB))
    return result.scalars().all()

async def delete_certification(db: AsyncSession, cert_id: int) -> None:
    cert = await db.get(models.CertificationDB, cert_id)
    if cert:
        await db.delete(cert)
        await db.commit()

# -------------------
# MOVIES
# -------------------

async def create_movie_db(db: AsyncSession, movie_data: schemas.MovieCreateSchema) -> models.MovieDB:
    movie = models.MovieDB(
        name=movie_data.name,
        year=movie_data.year,
        time=movie_data.time,
        imdb=movie_data.imdb,
        votes=movie_data.votes,
        meta_score=movie_data.meta_score,
        gross=movie_data.gross,
        price=movie_data.price,
        description=movie_data.description,
        certification_id=movie_data.certification_id,
    )

    if movie_data.genre_ids:
        result = await db.execute(select(models.GenreDB).where(models.GenreDB.id.in_(movie_data.genre_ids)))
        movie.genres = result.scalars().all()
    if movie_data.star_ids:
        result = await db.execute(select(models.StarDB).where(models.StarDB.id.in_(movie_data.star_ids)))
        movie.stars = result.scalars().all()
    if movie_data.director_ids:
        result = await db.execute(select(models.DirectorDB).where(models.DirectorDB.id.in_(movie_data.director_ids)))
        movie.directors = result.scalars().all()

    db.add(movie)
    await db.commit()
    await db.refresh(movie)
    return movie

async def get_movie_db(db: AsyncSession, movie_id: int) -> models.MovieDB | None:
    return await db.get(models.MovieDB, movie_id)

async def get_movie_by_uuid_db(db: AsyncSession, movie_uuid: UUID) -> models.MovieDB | None:
    result = await db.execute(select(models.MovieDB).where(models.MovieDB.uuid == movie_uuid))
    return result.scalar_one_or_none()

async def get_movies_db(db: AsyncSession, skip: int = 0, limit: int = 100, **filters) -> list[models.MovieDB]:
    query = select(models.MovieDB)

    if filters.get("year_from"):
        query = query.where(models.MovieDB.year >= filters["year_from"])
    if filters.get("year_to"):
        query = query.where(models.MovieDB.year <= filters["year_to"])
    if filters.get("imdb_min"):
        query = query.where(models.MovieDB.imdb >= filters["imdb_min"])
    if filters.get("imdb_max"):
        query = query.where(models.MovieDB.imdb <= filters["imdb_max"])

    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

async def update_movie_db(db: AsyncSession, movie_id: int, movie_update: schemas.MovieUpdateSchema) -> models.MovieDB | None:
    movie = await db.get(models.MovieDB, movie_id)
    if not movie:
        return None

    data = movie_update.dict(exclude_unset=True)
    for field, value in data.items():
        if field in ["genre_ids", "star_ids", "director_ids"]:
            if value is not None:
                if field == "genre_ids":
                    result = await db.execute(select(models.GenreDB).where(models.GenreDB.id.in_(value)))
                    movie.genres = result.scalars().all() if value else []
                if field == "star_ids":
                    result = await db.execute(select(models.StarDB).where(models.StarDB.id.in_(value)))
                    movie.stars = result.scalars().all() if value else []
                if field == "director_ids":
                    result = await db.execute(select(models.DirectorDB).where(models.DirectorDB.id.in_(value)))
                    movie.directors = result.scalars().all() if value else []
        else:
            setattr(movie, field, value)

    await db.commit()
    await db.refresh(movie)
    return movie

async def delete_movie_db(db: AsyncSession, movie_id: int) -> None:
    movie = await db.get(models.MovieDB, movie_id)
    if movie:
        await db.delete(movie)
        await db.commit()
