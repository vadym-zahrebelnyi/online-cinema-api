from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.movies.models import CertificationDB, GenreDB, MovieDB


async def get_movie_by_id(db: AsyncSession, movie_id: int) -> MovieDB | None:
    return await db.get(MovieDB, movie_id)


async def get_movie_by_uuid(db: AsyncSession, movie_uuid) -> MovieDB | None:
    result = await db.execute(select(MovieDB).where(MovieDB.uuid == movie_uuid))
    return result.scalar_one_or_none()


async def create_movie(db: AsyncSession, movie: MovieDB) -> MovieDB:
    db.add(movie)
    await db.commit()
    await db.refresh(movie)
    return movie


async def update_movie(db: AsyncSession, movie: MovieDB) -> MovieDB:
    db.add(movie)
    await db.commit()
    await db.refresh(movie)
    return movie


async def delete_movie(db: AsyncSession, movie: MovieDB) -> None:
    await db.delete(movie)
    await db.commit()


async def list_movies(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[MovieDB]:
    result = await db.execute(select(MovieDB).offset(skip).limit(limit))
    return result.scalars().all()


async def get_genre_by_id(db: AsyncSession, genre_id: int) -> GenreDB | None:
    return await db.get(GenreDB, genre_id)


async def get_genres_by_ids(db: AsyncSession, ids: list[int]) -> list[GenreDB]:
    result = await db.execute(select(GenreDB).where(GenreDB.id.in_(ids)))
    return result.scalars().all()


async def create_genre(db: AsyncSession, genre: GenreDB) -> GenreDB:
    db.add(genre)
    await db.commit()
    await db.refresh(genre)
    return genre


async def list_genres(db: AsyncSession) -> list[GenreDB]:
    result = await db.execute(select(GenreDB))
    return result.scalars().all()


async def delete_genre(db: AsyncSession, genre: GenreDB) -> None:
    await db.delete(genre)
    await db.commit()


async def get_certification_by_id(
    db: AsyncSession, cert_id: int
) -> CertificationDB | None:
    return await db.get(CertificationDB, cert_id)


async def create_certification(
    db: AsyncSession, cert: CertificationDB
) -> CertificationDB:
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert


async def list_certifications(db: AsyncSession) -> list[CertificationDB]:
    result = await db.execute(select(CertificationDB))
    return result.scalars().all()


async def delete_certification(db: AsyncSession, cert: CertificationDB) -> None:
    await db.delete(cert)
    await db.commit()
