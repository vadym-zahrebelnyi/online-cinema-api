from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError

from src.movies import crud, models
from src.movies.exceptions import (
    AppException,
    CertificationAlreadyExistsException,
    GenreAlreadyExistsException,
    MovieAlreadyExistsException,
)

pytestmark = pytest.mark.asyncio


async def test_create_movie_success():
    """Ensure a movie is created successfully with commit and refresh."""
    db = AsyncMock()
    db.add = Mock()
    movie = models.MovieDB(id=1, name="Test", year=2024)

    db.commit.return_value = None
    db.refresh.return_value = None

    result = await crud.create_movie(db, movie)

    db.add.assert_called_once_with(movie)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(movie)
    assert result == movie


async def test_create_movie_integrity_error():
    """Verify MovieAlreadyExistsException is raised on duplicate movie creation."""
    db = AsyncMock()
    db.add = Mock()
    movie = models.MovieDB(id=1, name="Duplicate", year=2024)

    db.commit.side_effect = IntegrityError("", "", "")

    with pytest.raises(MovieAlreadyExistsException):
        await crud.create_movie(db, movie)

    db.rollback.assert_called_once()


async def test_update_movie_unexpected_error():
    """Verify AppException is raised when an unexpected error occurs during update."""
    db = AsyncMock()
    db.add = Mock()
    movie = models.MovieDB(id=1, name="Update", year=2024)

    db.commit.side_effect = Exception("DB error")

    with pytest.raises(AppException):
        await crud.update_movie(db, movie)

    db.rollback.assert_called_once()


async def test_delete_movie_unexpected_error():
    """Verify AppException is raised when an unexpected error occurs during deletion."""
    db = AsyncMock()
    db.delete = Mock()
    movie = models.MovieDB(id=1, name="Delete", year=2024)

    db.delete.side_effect = Exception("DB error")

    with pytest.raises(AppException):
        await crud.delete_movie(db, movie)

    db.rollback.assert_called_once()


async def test_create_genre_integrity_error():
    """Verify GenreAlreadyExistsException is raised on duplicate genre creation."""
    db = AsyncMock()
    db.add = Mock()
    genre = models.GenreDB(id=1, name="Action")

    db.commit.side_effect = IntegrityError("", "", "")

    with pytest.raises(GenreAlreadyExistsException):
        await crud.create_genre(db, genre)

    db.rollback.assert_called_once()


async def test_create_certification_integrity_error():
    """Verify CertificationAlreadyExistsException is raised on duplicate certification creation."""
    db = AsyncMock()
    db.add = Mock()
    cert = models.CertificationDB(id=1, name="PG-13")

    db.commit.side_effect = IntegrityError("", "", "")

    with pytest.raises(CertificationAlreadyExistsException):
        await crud.create_certification(db, cert)

    db.rollback.assert_called_once()
