from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.cart.models import CartItemDB
from src.movies.models import MovieDB
from src.orders.exceptions import MovieNotAvailableError
from src.orders.models import OrderItemDB
from src.orders.services import calculate_total_amount, create_order_items_from_cart


@pytest.fixture
def db():
    """Fixture providing a mocked async database session."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_calculate_total_amount_success(db):
    """
    Test that calculate_total_amount correctly sums the prices of available movies
    in the cart and returns the total amount along with the movie objects.
    """
    cart_items = [CartItemDB(movie_id=1), CartItemDB(movie_id=2)]
    movie1 = MovieDB(id=1, price=Decimal("10.50"))
    movie2 = MovieDB(id=2, price=Decimal("5.25"))

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [movie1, movie2]
    db.scalars.return_value = mock_scalars

    total, movies = await calculate_total_amount(db, cart_items)

    assert total == Decimal("15.75")
    assert movies == [movie1, movie2]


@pytest.mark.asyncio
async def test_calculate_total_amount_movie_missing(db):
    """
    Test that calculate_total_amount raises MovieNotAvailableError when a cart
    item references a movie that is not available in the database.
    """
    cart_items = [CartItemDB(movie_id=1), CartItemDB(movie_id=2)]
    movie1 = MovieDB(id=1, price=Decimal("10.50"))

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [movie1]
    db.scalars.return_value = mock_scalars

    with pytest.raises(MovieNotAvailableError) as exc:
        await calculate_total_amount(db, cart_items)
    assert "2" in str(exc.value)


@pytest.mark.asyncio
async def test_create_order_items_from_cart():
    """
    Test that create_order_items_from_cart correctly creates OrderItemDB entries
    for each movie in the list and adds them to the database session.
    """
    db = AsyncMock()
    db.add = MagicMock()

    order_id = 123
    movie1 = MovieDB(id=1, price=Decimal("10.50"))
    movie2 = MovieDB(id=2, price=Decimal("5.25"))
    movies = [movie1, movie2]

    await create_order_items_from_cart(db, order_id, movies)

    assert db.add.call_count == 2

    added_items = [call_args[0][0] for call_args in db.add.call_args_list]
    assert all(isinstance(item, OrderItemDB) for item in added_items)
    assert added_items[0].order_id == order_id
    assert added_items[0].movie_id == 1
    assert added_items[0].price_at_order == Decimal("10.50")
    assert added_items[1].movie_id == 2
