from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.cart.crud import CartCRUD
from src.movies.models import MovieDB


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def crud(mock_db: AsyncMock) -> CartCRUD:
    return CartCRUD(db=mock_db)


@pytest.mark.asyncio
async def test_get_cart_by_user(crud: CartCRUD, mock_db: AsyncMock):
    movie = MovieDB(id=1, name="Test Movie", year=2020, price=Decimal("10.00"))
    cart_item = AsyncMock()
    cart_item.movie = movie
    cart_item.id = 101
    cart_item.added_at = "2023-01-01"
    cart = AsyncMock()
    cart.id = 1
    cart.items = [cart_item]

    mock_db.scalar.return_value = cart

    result = await crud.get_cart_by_user(1)
    assert result == cart
    mock_db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_cart(crud: CartCRUD, mock_db: AsyncMock):
    cart = await crud.create_cart(1)
    assert cart.user_id == 1
    mock_db.add.assert_called_once_with(cart)
    mock_db.flush.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(cart)


@pytest.mark.asyncio
async def test_add_item(crud: CartCRUD, mock_db: AsyncMock):
    item = await crud.add_item(1, 10)
    assert item.cart_id == 1
    assert item.movie_id == 10
    mock_db.add.assert_called_once_with(item)
    mock_db.flush.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(item)


@pytest.mark.asyncio
async def test_is_movie_available_to_buy(crud: CartCRUD, mock_db: AsyncMock):
    mock_db.scalar.return_value = True
    result = await crud.is_movie_available_to_buy(1, 10)
    assert result is True
    mock_db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_item_exists(crud: CartCRUD, mock_db: AsyncMock):
    mock_db.scalar.return_value = True
    result = await crud.item_exists(1, 10)
    assert result is True
    mock_db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_item(crud: CartCRUD, mock_db: AsyncMock):
    await crud.remove_item(1, 10)
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_clear_cart(crud: CartCRUD, mock_db: AsyncMock):
    await crud.clear_cart(1)
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_movie(crud: CartCRUD, mock_db: AsyncMock):
    movie = MovieDB(id=10, name="Test", year=2020, price=Decimal("10.00"))
    mock_db.get.return_value = movie
    result = await crud.get_movie(10)
    assert result == movie
    mock_db.get.assert_awaited_once_with(MovieDB, 10)


@pytest.mark.asyncio
async def test_get_movies_by_ids(crud: CartCRUD, mock_db: AsyncMock):
    movie1 = MovieDB(id=1, name="A", year=2020, price=Decimal("10.00"))
    movie2 = MovieDB(id=2, name="B", year=2021, price=Decimal("20.00"))

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [movie1, movie2]

    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars

    mock_db.execute.return_value = mock_result

    result = await crud.get_movies_by_ids([1, 2])
    assert result == [movie1, movie2]
    mock_db.execute.assert_awaited_once()
