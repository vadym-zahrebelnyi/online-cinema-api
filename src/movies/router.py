from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.dependencies import allow_admin, allow_moderator
from src.core.database import get_db
from src.movies import schemas, service
from src.movies.exceptions import (
    CertificationNotFoundException,
    GenreNotFoundException,
    MovieNotFoundException,
)
from src.movies.filters import GenreFilter, MovieFilter

DbSession = Annotated[AsyncSession, Depends(get_db)]
router = APIRouter(tags=["Movies"])


@router.post(
    "/",
    response_model=schemas.MovieDetailSchema,
    dependencies=[Depends(allow_moderator)],
    summary="Create movie",
    description="Create a new movie with related entities."
)
async def create_movie(movie_create: schemas.MovieCreateSchema, db: DbSession):
    """Create a movie record."""
    return await service.create_movie(db, movie_create)

@router.get(
    "/{movie_id}",
    response_model=schemas.MovieDetailSchema,
    summary="Get movie",
    description="Retrieve a movie by its ID."
)
async def get_movie(movie_id: int, db: DbSession):
    """Return movie details."""
    movie = await service.get_movie(db, movie_id)
    if not movie:
        raise MovieNotFoundException()
    return movie

@router.get(
    "/",
    response_model=list[schemas.MovieListItemSchema],
    summary="Search movies",
    description=(
        "List movies with filtering.\n\n"
        "Supports partial title search, year range filtering, and sorting."
    ),
)
async def list_movies(
    db: DbSession,
    filters: Annotated[MovieFilter, FilterDepends(MovieFilter)],
):
    """Return filtered movie catalog."""
    return await service.get_movies_catalog(db, filters)

@router.patch(
    "/{movie_id}",
    response_model=schemas.MovieDetailSchema,
    dependencies=[Depends(allow_moderator)],
    summary="Update movie",
    description="Update movie fields and relationships."
)
async def update_movie(movie_id: int, movie_update: schemas.MovieUpdateSchema, db: DbSession):
    """Modify an existing movie."""
    movie = await service.update_movie(db, movie_id, movie_update)
    if not movie:
        raise MovieNotFoundException()
    return movie

@router.delete(
    "/{movie_id}",
    dependencies=[Depends(allow_admin)],
    summary="Delete movie",
    description="Delete a movie if it is not referenced elsewhere."
)
async def delete_movie(movie_id: int, db: DbSession):
    """Remove a movie."""
    await service.delete_movie(db, movie_id)
    return {"detail": "Movie deleted"}

@router.post(
    "/genres/",
    response_model=schemas.GenreReadSchema,
    dependencies=[Depends(allow_moderator)],
    summary="Create genre",
    description="Create a new movie genre."
)
async def create_genre(genre: schemas.GenreCreateSchema, db: DbSession):
    """Create genre record."""
    return await service.create_genre(db, genre)

@router.get(
    "/genres/",
    response_model=list[schemas.GenreReadSchema],
    summary="Search genres",
    description="List genres with partial name filtering and sorting."
)
async def list_genres(
    db: DbSession,
    filters: Annotated[GenreFilter, FilterDepends(GenreFilter)],
):
    """Return filtered genre list."""
    return await service.list_genres(db, filters)

@router.get(
    "/genres/{genre_id}",
    response_model=schemas.GenreReadSchema,
    summary="Get genre",
    description="Retrieve genre by ID."
)
async def get_genre(genre_id: int, db: DbSession):
    """Return genre details."""
    genre = await service.get_genre(db, genre_id)
    if not genre:
        raise GenreNotFoundException()
    return genre

@router.delete(
    "/genres/{genre_id}",
    dependencies=[Depends(allow_admin)],
    summary="Delete genre",
    description="Delete genre if unused by movies."
)
async def delete_genre(genre_id: int, db: DbSession):
    """Remove genre."""
    await service.delete_genre(db, genre_id)
    return {"detail": "Genre deleted"}

@router.post(
    "/certifications/",
    response_model=schemas.CertificationReadSchema,
    dependencies=[Depends(allow_moderator)],
    summary="Create certification",
    description="Create a movie certification rating."
)
async def create_certification(cert: schemas.CertificationCreateSchema, db: DbSession):
    """Create certification."""
    return await service.create_certification(db, cert)

@router.get(
    "/certifications/",
    response_model=list[schemas.CertificationReadSchema],
    summary="List certifications",
    description="Retrieve all certifications."
)
async def list_certifications(db: DbSession):
    """Return certifications."""
    return await service.list_certifications(db)

@router.get(
    "/certifications/{cert_id}",
    response_model=schemas.CertificationReadSchema,
    summary="Get certification",
    description="Retrieve certification by ID."
)
async def get_certification(cert_id: int, db: DbSession):
    """Return certification details."""
    cert = await service.get_certification(db, cert_id)
    if not cert:
        raise CertificationNotFoundException()
    return cert

@router.delete(
    "/certifications/{cert_id}",
    dependencies=[Depends(allow_admin)],
    summary="Delete certification",
    description="Delete certification if unused."
)
async def delete_certification(cert_id: int, db: DbSession):
    """Remove certification."""
    await service.delete_certification(db, cert_id)
    return {"detail": "Certification deleted"}
