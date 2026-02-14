from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result

from src.cart.crud import CartCRUD
from src.cart.models import CartDB, CartItemDB
from src.movies.models import MovieDB


@pytest.fixture
def db() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.mark.asyncio
async def test_get_cart_by_user_found(db: AsyncMock):
    user_id = 1
    movie1 = MovieDB(id=1, name="Movie 1", price=Decimal("10.00"))
    movie2 = MovieDB(id=2, name="Movie 2", price=Decimal("15.00"))
    cart_item1 = CartItemDB(id=1, movie=movie1)
    cart_item2 = CartItemDB(id=2, movie=movie2)
    expected_cart = CartDB(id=10, user_id=user_id, items=[cart_item1, cart_item2])

    db.scalar.return_value = expected_cart

    crud = CartCRUD(db)
    result = await crud.get_cart_by_user(user_id)

    assert result == expected_cart
    db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_cart_by_user_not_found(db: AsyncMock):
    user_id = 1
    db.scalar.return_value = None

    crud = CartCRUD(db)
    result = await crud.get_cart_by_user(user_id)

    assert result is None
    db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_cart(db: AsyncMock):
    user_id = 1
    
    mock_cart = CartDB(user_id=user_id)
    mock_cart.id = 20

    db.add.return_value = None
    db.flush.return_value = None
    db.refresh.side_effect = lambda obj: setattr(obj, 'id', mock_cart.id)

    crud = CartCRUD(db)
    result = await crud.create_cart(user_id)

    assert result.user_id == user_id
    assert result.id == mock_cart.id
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_add_item(db: AsyncMock):
    cart_id = 10
    movie_id = 1
    
    mock_item = CartItemDB(cart_id=cart_id, movie_id=movie_id)
    mock_item.id = 100

    db.add.return_value = None
    db.flush.return_value = None
    db.refresh.side_effect = lambda obj: setattr(obj, 'id', mock_item.id)

    crud = CartCRUD(db)
    result = await crud.add_item(cart_id, movie_id)

    assert result.cart_id == cart_id
    assert result.movie_id == movie_id
    assert result.id == mock_item.id
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_is_movie_available_to_buy_true(db: AsyncMock):
    db.scalar.return_value = True

    crud = CartCRUD(db)
    result = await crud.is_movie_available_to_buy(user_id=1, movie_id=1)

    assert result is True
    db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_movie_available_to_buy_false(db: AsyncMock):
    db.scalar.return_value = False

    crud = CartCRUD(db)
    result = await crud.is_movie_available_to_buy(user_id=1, movie_id=1)

    assert result is False
    db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_item_exists_true(db: AsyncMock):
    db.scalar.return_value = True

    crud = CartCRUD(db)
    result = await crud.item_exists(cart_id=1, movie_id=1)

    assert result is True
    db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_item_exists_false(db: AsyncMock):
    db.scalar.return_value = False

    crud = CartCRUD(db)
    result = await crud.item_exists(cart_id=1, movie_id=1)

    assert result is False
    db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_item(db: AsyncMock):
    cart_id = 1
    movie_id = 1
    item_to_delete = CartItemDB(cart_id=cart_id, movie_id=movie_id)

    db.scalar.return_value = item_to_delete
    db.delete.return_value = None
    db.flush.return_value = None

    crud = CartCRUD(db)
    await crud.remove_item(cart_id, movie_id)

    db.scalar.assert_awaited_once()
    db.delete.assert_awaited_once_with(item_to_delete)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_item_not_found(db: AsyncMock):
    db.scalar.return_value = None

    crud = CartCRUD(db)
    await crud.remove_item(cart_id=1, movie_id=1)

    db.scalar.assert_awaited_once()
    db.delete.assert_not_awaited()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_clear_cart(db: AsyncMock):
    cart_id = 1
    item1 = CartItemDB(id=1, cart_id=cart_id, movie_id=1)
    item2 = CartItemDB(id=2, cart_id=cart_id, movie_id=2)

    db.scalars.return_value.all.return_value = [item1, item2]
    db.delete.return_value = None
    db.flush.return_value = None

    crud = CartCRUD(db)
    await crud.clear_cart(cart_id)

    db.scalars.assert_awaited_once()
    assert db.delete.call_count == 2
    db.delete.assert_any_call(item1)
    db.delete.assert_any_call(item2)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_clear_cart_empty_cart(db: AsyncMock):
    db.scalars.return_value.all.return_value = []

    crud = CartCRUD(db)
    await crud.clear_cart(cart_id=1)

    db.scalars.assert_awaited_once()
    db.delete.assert_not_awaited()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_movie_found(db: AsyncMock):
    movie_id = 1
    expected_movie = MovieDB(id=movie_id, name="Test Movie")
    db.get.return_value = expected_movie

    crud = CartCRUD(db)
    result = await crud.get_movie(movie_id)

    assert result == expected_movie
    db.get.assert_awaited_once_with(MovieDB, movie_id)


@pytest.mark.asyncio
async def test_get_movie_not_found(db: AsyncMock):
    movie_id = 1
    db.get.return_value = None

    crud = CartCRUD(db)
    result = await crud.get_movie(movie_id)

    assert result is None
    db.get.assert_awaited_once_with(MovieDB, movie_id)


@pytest.mark.asyncio
async def test_get_movies_by_ids_found(db: AsyncMock):
    movie_ids = [1, 2]
    movie1 = MovieDB(id=1, name="Movie A")
    movie2 = MovieDB(id=2, name="Movie B")

    class MockScalarsResult:
        def all(self):
            return [movie1, movie2]

    mock_execute_result = AsyncMock(spec=Result)
    mock_execute_result.scalars.return_value = MockScalarsResult()
    db.execute.return_value = mock_execute_result

    crud = CartCRUD(db)
    result = await crud.get_movies_by_ids(movie_ids)

    assert result == [movie1, movie2]
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_movies_by_ids_not_found(db: AsyncMock):
    movie_ids = [1, 2]

    class MockScalarsResult:
        def all(self):
            return []

    mock_execute_result = AsyncMock(spec=Result)
    mock_execute_result.scalars.return_value = MockScalarsResult()
    db.execute.return_value = mock_execute_result

    crud = CartCRUD(db)
    result = await crud.get_movies_by_ids(movie_ids)

    assert result == []
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_movies_by_ids_empty_list(db: AsyncMock):
    crud = CartCRUD(db)
    result = await crud.get_movies_by_ids([])

    assert result == []
    db.execute.assert_not_awaited()
