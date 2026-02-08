from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.movies import schemas, service
from src.movies.exceptions import (
    CertificationNotFoundException,
    GenreNotFoundException,
    MovieNotFoundException,
)

DbSession = Annotated[AsyncSession, Depends(get_db)]
router = APIRouter()

@router.post("/movies/", response_model=schemas.MovieDetailSchema, tags=["movies"])
async def create_movie(movie_create: schemas.MovieCreateSchema, db: DbSession):
    return await service.create_movie(db, movie_create)

@router.get("/movies/{movie_id}", response_model=schemas.MovieDetailSchema, tags=["movies"])
async def get_movie(movie_id: int, db: DbSession):
    movie = await service.get_movie(db, movie_id)
    if not movie:
        raise MovieNotFoundException()
    return movie

@router.get("/movies/", response_model=schemas.MovieListResponseSchema, tags=["movies"])
async def list_movies(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort_by: str | None = None,
    db: DbSession = None,
):
    movies = await service.get_movies_catalog(
        db,
        skip=(page - 1) * size,
        limit=size,
        filters={},  # тут можна додати фільтри з query params
        sort_by=sort_by,
    )
    return schemas.MovieListResponseSchema(total=len(movies), page=page, size=size, items=movies)

@router.patch("/movies/{movie_id}", response_model=schemas.MovieDetailSchema, tags=["movies"])
async def update_movie(movie_id: int, movie_update: schemas.MovieUpdateSchema, db: DbSession):
    movie = await service.update_movie(db, movie_id, movie_update)
    if not movie:
        raise MovieNotFoundException()
    return movie

@router.delete("/movies/{movie_id}", tags=["movies"])
async def delete_movie(movie_id: int, db: DbSession):
    await service.delete_movie(db, movie_id)
    return {"detail": "Movie deleted"}

@router.post("/genres/", response_model=schemas.GenreReadSchema, tags=["genres"])
async def create_genre(genre: schemas.GenreCreateSchema, db: DbSession):
    return await service.create_genre(db, genre)

@router.get("/genres/", response_model=list[schemas.GenreReadSchema], tags=["genres"])
async def list_genres(db: DbSession):
    return await service.list_genres(db)

@router.get("/genres/{genre_id}", response_model=schemas.GenreReadSchema, tags=["genres"])
async def get_genre(genre_id: int, db: DbSession):
    genre = await service.get_genre(db, genre_id)
    if not genre:
        raise GenreNotFoundException()
    return genre

@router.delete("/genres/{genre_id}", tags=["genres"])
async def delete_genre(genre_id: int, db: DbSession):
    await service.delete_genre(db, genre_id)
    return {"detail": "Genre deleted"}

@router.post("/certifications/", response_model=schemas.CertificationReadSchema, tags=["certifications"])
async def create_certification(cert: schemas.CertificationCreateSchema, db: DbSession):
    return await service.create_certification(db, cert)

@router.get("/certifications/", response_model=list[schemas.CertificationReadSchema], tags=["certifications"])
async def list_certifications(db: DbSession):
    return await service.list_certifications(db)

@router.get("/certifications/{cert_id}", response_model=schemas.CertificationReadSchema, tags=["certifications"])
async def get_certification(cert_id: int, db: DbSession):
    cert = await service.get_certification(db, cert_id)
    if not cert:
        raise CertificationNotFoundException()
    return cert

@router.delete("/certifications/{cert_id}", tags=["certifications"])
async def delete_certification(cert_id: int, db: DbSession):
    await service.delete_certification(db, cert_id)
    return {"detail": "Certification deleted"}
