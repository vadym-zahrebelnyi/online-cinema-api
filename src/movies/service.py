from sqlalchemy.ext.asyncio import AsyncSession

from src.movies import crud, models, schemas


async def create_movie(db: AsyncSession, movie_create: schemas.MovieCreateSchema) -> models.MovieDB:
    cert = await db.get(models.CertificationDB, movie_create.certification_id)
    if not cert:
        raise ValueError("Certification not found")

    if movie_create.genre_ids:
        for gid in movie_create.genre_ids:
            if not await db.get(models.GenreDB, gid):
                raise ValueError(f"Genre {gid} not found")

    return await crud.create_movie_db(db, movie_create)


async def update_movie(db: AsyncSession, movie_id: int, movie_update: schemas.MovieUpdateSchema) -> models.MovieDB | None:
    return await crud.update_movie_db(db, movie_id, movie_update)


async def delete_movie(db: AsyncSession, movie_id: int) -> None:
    movie = await crud.get_movie_db(db, movie_id)
    if not movie:
        raise ValueError("Movie not found")

    if movie.order_items:
        raise ValueError("Cannot delete movie with existing orders")

    await crud.delete_movie_db(db, movie_id)


async def get_movies_catalog(db: AsyncSession, skip: int = 0, limit: int = 100, filters: dict = None, sort_by: str = None):
    movies = await crud.get_movies_db(db, skip=skip, limit=limit, **(filters or {}))

    if sort_by == "imdb":
        movies.sort(key=lambda m: m.imdb, reverse=True)
    elif sort_by == "year":
        movies.sort(key=lambda m: m.year, reverse=True)

    return movies


async def get_genres_with_movie_count(db: AsyncSession) -> list[dict]:
    genres = await crud.get_all_genres(db)
    return [{"id": g.id, "name": g.name, "movie_count": len(g.movies)} for g in genres]
