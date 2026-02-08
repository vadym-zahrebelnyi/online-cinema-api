from typing import List

from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.orders.services import calculate_total_amount, create_order_items_from_cart
from src.cart.models import CartDB
from src.orders.exceptions import OrderNotFoundError, CartIsEmptyError, OrderAlreadyPendingError
from src.orders.models import OrderDB, OrderStatusEnum, OrderItemDB


async def create_order(db: AsyncSession, user_id: int) -> OrderDB:
    """CREATES ORDER YEEAAAAAAAAAAAA"""
    cart = await db.scalar(
        select(CartDB).where(CartDB.user_id == user_id).options(selectinload(CartDB.items))
    )
    if not cart or not cart.items:
        raise CartIsEmptyError("Cart is empty")

    cart_movie_ids = [item.movie_id for item in cart.items]

    pending_exists = await db.scalar(
        select(
            exists().where(
                OrderDB.user_id == user_id,
                OrderDB.status == OrderStatusEnum.PENDING,
                OrderDB.id == OrderItemDB.order_id,
                OrderItemDB.movie_id.in_(cart_movie_ids),
            )
        )
    )
    if pending_exists:
        raise OrderAlreadyPendingError("Order already pending")

    total_amount, movies = await calculate_total_amount(db, cart.items)

    order = OrderDB(
        user_id=user_id,
        status=OrderStatusEnum.PENDING,
        total_amount=total_amount
    )
    db.add(order)
    await db.flush()

    await create_order_items_from_cart(db, order.id, movies)

    await db.commit()
    order = await db.scalar(
        select(OrderDB)
        .where(OrderDB.id == order.id)
        .options(selectinload(OrderDB.items).selectinload(OrderItemDB.movie))
    )
    return order


async def get_orders_by_user(db: AsyncSession, user_id: int) -> List[OrderDB]:
    """Return list of user's orders"""
    result = await db.scalars(select(OrderDB).where(OrderDB.user_id == user_id))
    return list(result.all())


async def cancel_order(db: AsyncSession, order_id: int) -> None:
    """Change order status to CANCELLED"""
    order = await db.get(OrderDB, order_id)
    if not order:
        raise OrderNotFoundError(f"Order {order_id} not found")
    order.status = OrderStatusEnum.CANCELLED
    await db.commit()
