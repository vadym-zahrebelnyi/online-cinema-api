from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.movies import models, schemas, service
from src.movies.exceptions import MovieHasOrdersException, MovieNotFoundException

pytestmark = pytest.mark.asyncio


@patch("src.movies.service.crud.get_certification_by_id", new_callable=AsyncMock)
@patch("src.movies.service.crud.get_genres_by_ids", new_callable=AsyncMock)
@patch("src.movies.service.crud.create_movie", new_callable=AsyncMock)
async def test_create_movie_success(
    mock_create_movie, mock_get_genres, mock_get_certification
):
    """Ensure create_movie calls CRUD methods and returns created movie."""
    mock_get_certification.return_value = models.CertificationDB(id=1, name="PG-13")
    mock_get_genres.return_value = [models.GenreDB(id=1, name="Action")]
    mock_create_movie.return_value = "created_movie"

    movie_data = schemas.MovieCreateSchema(
        name="Test Movie",
        year=2023,
        time=120,
        imdb=8.5,
        votes=1000,
        meta_score=80,
        gross=Decimal("1000000"),
        price=Decimal("10.0"),
        description="Test desc",
        certification_id=1,
        genre_ids=[1],
        star_ids=[],
        director_ids=[],
    )

    result = await service.create_movie(AsyncMock(), movie_data)

    mock_get_certification.assert_awaited_once()
    mock_get_genres.assert_awaited_once()
    mock_create_movie.assert_awaited_once()
    assert result == "created_movie"


@patch("src.movies.service.crud.get_movie_with_orders", new_callable=AsyncMock)
async def test_delete_movie_not_found(mock_get_movie):
    """Ensure deleting non-existent movie raises MovieNotFoundException."""
    mock_get_movie.return_value = None
    with pytest.raises(MovieNotFoundException):
        await service.delete_movie(AsyncMock(), 1)


@patch("src.movies.service.crud.get_movie_with_orders", new_callable=AsyncMock)
@patch("src.movies.service.crud.delete_movie", new_callable=AsyncMock)
async def test_delete_movie_has_orders(mock_delete_movie, mock_get_movie):
    """Ensure deleting movie with orders raises MovieHasOrdersException and does not delete."""
    movie_mock = AsyncMock()
    movie_mock.order_items = [1]
    mock_get_movie.return_value = movie_mock

    with pytest.raises(MovieHasOrdersException):
        await service.delete_movie(AsyncMock(), 1)
    mock_delete_movie.assert_not_awaited()


async def test_get_movie_calls_db():
    """Ensure get_movie calls db.execute and returns the expected movie."""
    mock_db = AsyncMock()
    fake_movie = models.MovieDB(
        id=1,
        name="Test Movie",
        year=2023,
        time=120,
        imdb=Decimal("8.5"),
        votes=1000,
        price=Decimal("10.0"),
        description="Test",
        certification_id=1,
    )

    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = fake_movie
    mock_db.execute.return_value = mock_result

    result = await service.get_movie(mock_db, 1)

    mock_db.execute.assert_awaited()
    assert result == fake_movie
