from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from src.cart.models import CartDB, CartItemDB
from src.core.dependencies import PaginationParams
from src.orders.crud import (
    cancel_order,
    create_order,
    get_all_orders_filtered,
    get_order_with_items,
    get_orders_by_user,
)
from src.orders.exceptions import CartIsEmptyError, OrderNotFoundError
from src.orders.models import OrderDB, OrderStatusEnum


@pytest.mark.asyncio
async def test_get_orders_by_user():
    """
    Test retrieving all orders for a specific user.
    """
    db = AsyncMock()
    order1 = OrderDB(id=1, user_id=1)
    order2 = OrderDB(id=2, user_id=1)

    class MockScalarResult:
        """Mock object for db.scalars() result."""

        def all(self):
            return [order1, order2]

    db.scalars.return_value = MockScalarResult()

    result = await get_orders_by_user(db, user_id=1)
    assert result == [order1, order2]
    db.scalars.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_order_success():
    """
    Test successful cancellation of an order.
    """
    db = AsyncMock()
    order = OrderDB(id=1, status=OrderStatusEnum.PENDING)
    db.get.return_value = order

    await cancel_order(db, order_id=1)
    assert order.status == OrderStatusEnum.CANCELLED
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_order_not_found():
    """
    Test cancelling an order that does not exist raises OrderNotFoundError.
    """
    db = AsyncMock()
    db.get.return_value = None

    with pytest.raises(OrderNotFoundError):
        await cancel_order(db, order_id=1)


@pytest.mark.asyncio
async def test_get_order_with_items():
    """
    Test retrieving an order along with its items.
    """
    db = AsyncMock()
    order = OrderDB(id=1)
    db.scalar.return_value = order

    result = await get_order_with_items(db, order_id=1)
    assert result == order
    db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_all_orders_filtered():
    """
    Test retrieving all orders with filters and pagination applied.
    """
    db = AsyncMock()
    filters = MagicMock()
    filters.filter.return_value = select(OrderDB)
    filters.sort.return_value = select(OrderDB)

    order1 = OrderDB(id=1)
    order2 = OrderDB(id=2)

    class MockScalarResult:
        """Mock object for db.scalars() result."""

        def all(self):
            return [order1, order2]

    db.scalars.return_value = MockScalarResult()

    pagination = PaginationParams(offset=0, limit=10)
    result = await get_all_orders_filtered(db, filters, pagination)
    assert result == [order1, order2]


@pytest.mark.asyncio
async def test_create_order_cart_empty():
    """
    Test that creating an order with an empty cart raises CartIsEmptyError.
    """
    db = AsyncMock()
    db.scalar.return_value = None
    cart_service = AsyncMock()

    with pytest.raises(CartIsEmptyError):
        await create_order(db, user_id=1, cart_service=cart_service)


@pytest.mark.asyncio
async def test_create_order_success(monkeypatch):
    """
    Test successful creation of an order including DB interactions and cart processing.
    """
    db = AsyncMock()
    cart_service = AsyncMock()

    class MockMovie:
        """Mock movie object with id and price."""

        def __init__(self, id, price):
            self.id = id
            self.price = price

    movie1 = MockMovie(1, Decimal("10.5"))
    movie2 = MockMovie(2, Decimal("5.25"))

    cart_item1 = CartItemDB()
    cart_item1.movie = movie1
    cart_item2 = CartItemDB()
    cart_item2.movie = movie2

    cart = CartDB()
    cart.items = [cart_item1, cart_item2]

    db.scalar = AsyncMock(
        side_effect=[
            cart,
            False,
            OrderDB(id=1, user_id=1, total_amount=Decimal("15.75")),
        ]
    )

    class MockScalars:
        def first(self):
            return None

    class MockExecuteResult:
        def scalars(self):
            return MockScalars()

    db.execute.return_value = MockExecuteResult()

    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    monkeypatch.setattr("src.orders.crud.create_order_items_from_cart", AsyncMock())

    order = await create_order(db, user_id=1, cart_service=cart_service)

    assert order.user_id == 1
    db.add.assert_called()
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
