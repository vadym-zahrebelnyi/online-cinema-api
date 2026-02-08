from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.movies import crud, models, schemas
from src.movies.exceptions import (
    CertificationInUseException,
    CertificationNotFoundException,
    GenreInUseException,
    GenreNotFoundException,
    MovieHasOrdersException,
    MovieNotFoundException,
)


async def create_movie(db: AsyncSession, data: schemas.MovieCreateSchema) -> models.MovieDB:
    cert = await crud.get_certification_by_id(db, data.certification_id)
    if not cert:
        raise CertificationNotFoundException()

    movie = models.MovieDB(
        name=data.name,
        year=data.year,
        time=data.time,
        imdb=data.imdb,
        votes=data.votes,
        meta_score=data.meta_score,
        gross=data.gross,
        price=data.price,
        description=data.description,
        certification_id=data.certification_id,
    )

    if data.genre_ids:
        movie.genres = await crud.get_genres_by_ids(db, data.genre_ids)
    if data.star_ids:
        result = await db.execute(select(models.StarDB).where(models.StarDB.id.in_(data.star_ids)))
        movie.stars = result.scalars().all()
    if data.director_ids:
        result = await db.execute(select(models.DirectorDB).where(models.DirectorDB.id.in_(data.director_ids)))
        movie.directors = result.scalars().all()

    return await crud.create_movie(db, movie)


async def update_movie(db: AsyncSession, movie_id: int, data: schemas.MovieUpdateSchema) -> models.MovieDB | None:
    movie = await crud.get_movie_by_id(db, movie_id)
    if not movie:
        return None

    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "genre_ids":
            movie.genres = await crud.get_genres_by_ids(db, value) if value else []
        elif field == "star_ids":
            result = await db.execute(select(models.StarDB).where(models.StarDB.id.in_(value)))
            movie.stars = result.scalars().all() if value else []
        elif field == "director_ids":
            result = await db.execute(select(models.DirectorDB).where(models.DirectorDB.id.in_(value)))
            movie.directors = result.scalars().all() if value else []
        else:
            setattr(movie, field, value)

    return await crud.update_movie(db, movie)


async def delete_movie(db: AsyncSession, movie_id: int) -> None:
    movie = await crud.get_movie_by_id(db, movie_id)
    if not movie:
        raise MovieNotFoundException()
    if movie.order_items:
        raise MovieHasOrdersException()
    await crud.delete_movie(db, movie)


async def get_movies_catalog(db: AsyncSession, skip: int, limit: int, filters: dict, sort_by: str | None):
    movies = await crud.list_movies(db, skip=skip, limit=limit)
    if sort_by == "imdb":
        movies.sort(key=lambda m: m.imdb, reverse=True)
    elif sort_by == "year":
        movies.sort(key=lambda m: m.year, reverse=True)
    return movies

async def get_movie(db: AsyncSession, movie_id: int) -> models.MovieDB | None:
    return await crud.get_movie_by_id(db, movie_id)

async def create_genre(db: AsyncSession, data: schemas.GenreCreateSchema) -> models.GenreDB:
    genre = models.GenreDB(name=data.name)
    return await crud.create_genre(db, genre)

async def list_genres(db: AsyncSession) -> list[models.GenreDB]:
    return await crud.list_genres(db)

async def get_genre(db: AsyncSession, genre_id: int) -> models.GenreDB | None:
    return await crud.get_genre_by_id(db, genre_id)

async def delete_genre(db: AsyncSession, genre_id: int) -> None:
    genre = await crud.get_genre_by_id(db, genre_id)
    if not genre:
        raise GenreNotFoundException()
    if genre.movies:
        raise GenreInUseException()
    await crud.delete_genre(db, genre)

async def create_certification(db: AsyncSession, data: schemas.CertificationCreateSchema) -> models.CertificationDB:
    cert = models.CertificationDB(name=data.name)
    return await crud.create_certification(db, cert)

async def list_certifications(db: AsyncSession) -> list[models.CertificationDB]:
    return await crud.list_certifications(db)

async def get_certification(db: AsyncSession, cert_id: int) -> models.CertificationDB | None:
    return await crud.get_certification_by_id(db, cert_id)

async def delete_certification(db: AsyncSession, cert_id: int) -> None:
    cert = await crud.get_certification_by_id(db, cert_id)
    if not cert:
        raise CertificationNotFoundException()
    if cert.movies:
        raise CertificationInUseException()
    await crud.delete_certification(db, cert)
