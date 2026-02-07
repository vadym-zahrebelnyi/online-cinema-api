from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.movies import schemas, service, crud

router = APIRouter()


@router.post("/movies/", response_model=schemas.MovieDetailSchema, tags=["movies"])
async def create_movie(movie_create: schemas.MovieCreateSchema, db: AsyncSession = Depends(get_db)):
    try:
        return await service.create_movie(db, movie_create)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/movies/{movie_id}", response_model=schemas.MovieDetailSchema, tags=["movies"])
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await service.get_movie(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie

@router.get("/movies/", response_model=schemas.MovieListResponseSchema, tags=["movies"])
async def list_movies(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    year_from: int | None = None,
    year_to: int | None = None,
    imdb_min: float | None = None,
    imdb_max: float | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    genre_id: int | None = None,
    star_id: int | None = None,
    director_id: int | None = None,
    sort_by: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    filters = {
        "year_from": year_from,
        "year_to": year_to,
        "imdb_min": imdb_min,
        "imdb_max": imdb_max,
        "price_min": price_min,
        "price_max": price_max,
        "genre_id": genre_id,
        "star_id": star_id,
        "director_id": director_id,
    }
    movies = await service.get_movies_catalog(db, skip=(page - 1) * size, limit=size, filters=filters, sort_by=sort_by)
    return schemas.MovieListResponseSchema(total=len(movies), page=page, size=size, items=movies)

@router.patch("/movies/{movie_id}", response_model=schemas.MovieDetailSchema, tags=["movies"])
async def update_movie(movie_id: int, movie_update: schemas.MovieUpdateSchema, db: AsyncSession = Depends(get_db)):
    movie = await service.update_movie(db, movie_id, movie_update)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie

@router.delete("/movies/{movie_id}", tags=["movies"])
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await service.delete_movie(db, movie_id)
        return {"detail": "Movie deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/genres/", response_model=schemas.GenreReadSchema, tags=["genres"])
async def create_genre(genre: schemas.GenreCreateSchema, db: AsyncSession = Depends(get_db)):
    return await crud.create_genre(db, genre.name)

@router.get("/genres/", response_model=list[schemas.GenreReadSchema], tags=["genres"])
async def list_genres(db: AsyncSession = Depends(get_db)):
    return await crud.get_all_genres(db)

@router.delete("/genres/{genre_id}", tags=["genres"])
async def delete_genre(genre_id: int, db: AsyncSession = Depends(get_db)):
    await crud.delete_genre(db, genre_id)
    return {"detail": "Genre deleted"}


@router.post("/certifications/", response_model=schemas.CertificationReadSchema, tags=["certifications"])
async def create_certification(cert: schemas.CertificationCreateSchema, db: AsyncSession = Depends(get_db)):
    return await crud.create_certification(db, cert.name)

@router.get("/certifications/", response_model=list[schemas.CertificationReadSchema], tags=["certifications"])
async def list_certifications(db: AsyncSession = Depends(get_db)):
    return await crud.get_all_certifications(db)

@router.delete("/certifications/{cert_id}", tags=["certifications"])
async def delete_certification(cert_id: int, db: AsyncSession = Depends(get_db)):
    await crud.delete_certification(db, cert_id)
    return {"detail": "Certification deleted"}
