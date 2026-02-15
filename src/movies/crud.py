from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.movies.exceptions import (
    AppException,
    CertificationAlreadyExistsException,
    GenreAlreadyExistsException,
    MovieAlreadyExistsException,
    MovieUpdateException,
)
from src.movies.models import CertificationDB, GenreDB, MovieDB


async def get_movie_by_id(db: AsyncSession, movie_id: int) -> MovieDB | None:
    """Get a movie by its integer ID."""
    return await db.get(MovieDB, movie_id)


async def get_movie_with_orders(db: AsyncSession, movie_id: int) -> MovieDB | None:
    """Gets movie AND preloads order_items to check for dependencies."""
    stmt = (
        select(MovieDB)
        .options(selectinload(MovieDB.order_items))
        .where(MovieDB.id == movie_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_movie_by_uuid(db: AsyncSession, movie_uuid) -> MovieDB | None:
    """Get a movie by its UUID."""
    result = await db.execute(select(MovieDB).where(MovieDB.uuid == movie_uuid))
    return result.scalar_one_or_none()


async def create_movie(db: AsyncSession, movie: MovieDB) -> MovieDB:
    """Create a new movie in the database with transaction safety."""
    try:
        db.add(movie)
        await db.commit()
        await db.refresh(movie)
        return movie
    except IntegrityError:
        await db.rollback()
        raise MovieAlreadyExistsException()
    except Exception:
        await db.rollback()
        raise MovieUpdateException()


async def update_movie(db: AsyncSession, movie: MovieDB) -> MovieDB:
    """Update an existing movie in the database with transaction safety."""
    try:
        db.add(movie)
        await db.commit()
        await db.refresh(movie)
        return movie
    except IntegrityError:
        await db.rollback()
        raise MovieUpdateException()
    except Exception:
        await db.rollback()
        raise AppException(
            status_code=500, detail="Unexpected error while updating movie"
        )


async def delete_movie(db: AsyncSession, movie: MovieDB) -> None:
    """Delete a movie from the database with transaction safety."""
    try:
        await db.delete(movie)
        await db.commit()
    except Exception:
        await db.rollback()
        raise AppException(
            status_code=500, detail="Unexpected error while deleting movie"
        )


async def list_movies(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[MovieDB]:
    """Return a list of movies with optional pagination."""
    result = await db.execute(select(MovieDB).offset(skip).limit(limit))
    return result.scalars().all()


async def get_genre_by_id(db: AsyncSession, genre_id: int) -> GenreDB | None:
    """Get a genre by its ID."""
    return await db.get(GenreDB, genre_id)


async def get_genres_by_ids(db: AsyncSession, ids: list[int]) -> list[GenreDB]:
    """Get multiple genres by their IDs."""
    result = await db.execute(select(GenreDB).where(GenreDB.id.in_(ids)))
    return result.scalars().all()


async def get_genre_with_movies(db: AsyncSession, genre_id: int) -> GenreDB | None:
    """Gets genre AND preloads movies to check for usage."""
    stmt = (
        select(GenreDB)
        .options(selectinload(GenreDB.movies))
        .where(GenreDB.id == genre_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_genre(db: AsyncSession, genre: GenreDB) -> GenreDB:
    """Create a new genre with transaction safety."""
    try:
        db.add(genre)
        await db.commit()
        await db.refresh(genre)
        return genre
    except IntegrityError:
        await db.rollback()
        raise GenreAlreadyExistsException()
    except Exception:
        await db.rollback()
        raise AppException(
            status_code=500, detail="Unexpected error while creating genre"
        )


async def list_genres(db: AsyncSession) -> list[GenreDB]:
    """Return all genres."""
    result = await db.execute(select(GenreDB))
    return result.scalars().all()


async def delete_genre(db: AsyncSession, genre: GenreDB) -> None:
    """Delete a genre with transaction safety."""
    try:
        await db.delete(genre)
        await db.commit()
    except Exception:
        await db.rollback()
        raise AppException(
            status_code=500, detail="Unexpected error while deleting genre"
        )


async def get_certification_by_id(
    db: AsyncSession, cert_id: int
) -> CertificationDB | None:
    """Get a certification by its ID."""
    return await db.get(CertificationDB, cert_id)


async def get_certification_with_movies(
    db: AsyncSession, cert_id: int
) -> CertificationDB | None:
    """Gets certification AND preloads movies to check for usage."""
    stmt = (
        select(CertificationDB)
        .options(selectinload(CertificationDB.movies))
        .where(CertificationDB.id == cert_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_certification(
    db: AsyncSession, cert: CertificationDB
) -> CertificationDB:
    """Create a new certification with transaction safety."""
    try:
        db.add(cert)
        await db.commit()
        await db.refresh(cert)
        return cert
    except IntegrityError:
        await db.rollback()
        raise CertificationAlreadyExistsException()
    except Exception:
        await db.rollback()
        raise AppException(
            status_code=500, detail="Unexpected error while creating certification"
        )


async def list_certifications(db: AsyncSession) -> list[CertificationDB]:
    """Return all certifications."""
    result = await db.execute(select(CertificationDB))
    return result.scalars().all()


async def delete_certification(db: AsyncSession, cert: CertificationDB) -> None:
    """Delete a certification with transaction safety."""
    try:
        await db.delete(cert)
        await db.commit()
    except Exception:
        await db.rollback()
        raise AppException(
            status_code=500, detail="Unexpected error while deleting certification"
        )
