import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.cart.services import (
    CartService,
    MovieNotFoundError,
    MovieAlreadyOwnedError,
    MovieAlreadyInCartError,
)


class MockMovie:
    def __init__(self, id: int):
        self.id = id


class MockCartItem:
    def __init__(self, id: int, movie: MockMovie, added_at: datetime):
        self.id = id
        self.movie = movie
        self.added_at = added_at


class MockCart:
    def __init__(self, id: int, user_id: int, items: list):
        self.id = id
        self.user_id = user_id
        self.items = items


@pytest.fixture
def mock_repo():
    """
    Create a mocked repository with async CRUD methods
    and async commit/rollback.
    """
    repo = MagicMock()

    repo.db = MagicMock()
    repo.db.commit = AsyncMock()
    repo.db.rollback = AsyncMock()

    repo.get_movie = AsyncMock()
    repo.is_movie_available_to_buy = AsyncMock()
    repo.get_cart_by_user = AsyncMock()
    repo.item_exists = AsyncMock()
    repo.add_item = AsyncMock()
    repo.remove_item = AsyncMock()
    repo.clear_cart = AsyncMock()
    repo.create_cart = AsyncMock()

    return repo


@pytest.fixture
def mock_redis():
    """Return mocked async Redis client."""
    return AsyncMock()


@pytest.fixture
def cart_service_instance(mock_repo, mock_redis):
    """Create CartService instance with mocked dependencies."""
    return CartService(repo=mock_repo, redis=mock_redis)


@pytest.fixture
def movie_a():
    """Return simple mock movie object."""
    return MockMovie(id=1)


@pytest.mark.asyncio
async def test_add_movie_success(cart_service_instance, mock_repo, movie_a):
    """Should successfully add movie to user cart and commit transaction."""
    user_id = 1

    mock_repo.get_movie.return_value = movie_a
    mock_repo.is_movie_available_to_buy.return_value = False
    mock_repo.get_cart_by_user.return_value = MockCart(id=1, user_id=user_id, items=[])
    mock_repo.item_exists.return_value = False

    await cart_service_instance.add_movie(movie_a.id, user_id, None)

    mock_repo.add_item.assert_awaited_once_with(1, movie_a.id)
    mock_repo.db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_movie_already_owned(cart_service_instance, mock_repo, movie_a):
    """Should raise error if user already owns the movie."""
    user_id = 1

    mock_repo.get_movie.return_value = movie_a
    mock_repo.is_movie_available_to_buy.return_value = True

    with pytest.raises(MovieAlreadyOwnedError):
        await cart_service_instance.add_movie(movie_a.id, user_id, None)

    mock_repo.db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_movie_not_found(cart_service_instance, mock_repo):
    """Should raise error if movie does not exist."""
    user_id = 1
    mock_repo.get_movie.return_value = None

    with pytest.raises(MovieNotFoundError):
        await cart_service_instance.add_movie(999, user_id, None)


@pytest.mark.asyncio
async def test_add_movie_already_in_cart(cart_service_instance, mock_repo, movie_a):
    """Should raise error if movie is already in the cart."""
    user_id = 1

    mock_repo.get_movie.return_value = movie_a
    mock_repo.is_movie_available_to_buy.return_value = False

    mock_cart_item = MockCartItem(
        id=101,
        movie=movie_a,
        added_at=datetime.utcnow(),
    )

    mock_cart = MockCart(id=1, user_id=user_id, items=[mock_cart_item])
    mock_repo.get_cart_by_user.return_value = mock_cart
    mock_repo.item_exists.return_value = True

    with pytest.raises(MovieAlreadyInCartError):
        await cart_service_instance.add_movie(movie_a.id, user_id, None)

    mock_repo.db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_item(cart_service_instance, mock_repo, movie_a):
    """Should remove movie from cart and commit transaction."""
    user_id = 1

    mock_cart = MockCart(
        id=1,
        user_id=user_id,
        items=[MockCartItem(id=101, movie=movie_a, added_at=datetime.utcnow())],
    )

    mock_repo.get_cart_by_user.return_value = mock_cart

    await cart_service_instance.remove_item(movie_a.id, user_id, None)

    mock_repo.remove_item.assert_awaited_once_with(1, movie_a.id)
    mock_repo.db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_clear_cart(cart_service_instance, mock_repo):
    """Should clear all cart items and commit transaction."""
    user_id = 1

    mock_repo.get_cart_by_user.return_value = MockCart(
        id=1,
        user_id=user_id,
        items=[],
    )

    await cart_service_instance.clear_cart(user_id, None)

    mock_repo.clear_cart.assert_awaited_once_with(1)
    mock_repo.db.commit.assert_awaited_once()
