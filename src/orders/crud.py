from decimal import Decimal
from typing import List

from fastapi import HTTPException
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.cart.models import CartDB, CartItemDB
from src.cart.services import CartService
from src.orders.exceptions import (
    CartIsEmptyError,
    OrderNotFoundError,
)
from src.orders.filters import OrderFilter
from src.orders.models import OrderDB, OrderItemDB, OrderStatusEnum
from src.orders.services import create_order_items_from_cart


async def create_order(
    db: AsyncSession, user_id: int, cart_service: CartService
) -> OrderDB:
    """CREATES ORDER YEEAAAAAAAAAAAA"""
    cart = await db.scalar(
        select(CartDB)
        .where(CartDB.user_id == user_id)
        .options(selectinload(CartDB.items).selectinload(CartItemDB.movie))
    )
    if not cart or not cart.items:
        raise CartIsEmptyError("Cart is empty")

    movies = [item.movie for item in cart.items]
    movie_ids = [m.id for m in movies]

    already_paid_query = (
        select(OrderItemDB.movie_id)
        .join(OrderDB)
        .where(
            OrderDB.user_id == user_id,
            OrderDB.status == OrderStatusEnum.PAID,
            OrderItemDB.movie_id.in_(movie_ids),
        )
    )
    paid_result = await db.execute(already_paid_query)
    paid_movie = paid_result.scalars().first()

    if paid_movie:
        raise HTTPException(
            status_code=409,
            detail=f"You have already purchased movie with ID {paid_movie}",
        )

    pending_exists = await db.scalar(
        select(
            exists().where(
                OrderDB.user_id == user_id,
                OrderDB.status == OrderStatusEnum.PENDING,
                OrderDB.id == OrderItemDB.order_id,
                OrderItemDB.movie_id.in_(movie_ids),
            )
        )
    )
    if pending_exists:
        raise HTTPException(status_code=409, detail="Order already pending")

    total_amount = Decimal(sum(m.price for m in movies))

    order = OrderDB(
        user_id=user_id, status=OrderStatusEnum.PENDING, total_amount=total_amount
    )
    db.add(order)
    await db.flush()

    await create_order_items_from_cart(db, order.id, movies)

    await cart_service.clear_cart(user_id=user_id, anon_id=None)

    await db.commit()

    return await db.scalar(
        select(OrderDB)
        .where(OrderDB.id == order.id)
        .options(selectinload(OrderDB.items).selectinload(OrderItemDB.movie))
    )


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


async def get_order_with_items(db: AsyncSession, order_id: int) -> OrderDB | None:
    """
    Return order with loaded items specifically for payment processing.
    """
    stmt = (
        select(OrderDB)
        .where(OrderDB.id == order_id)
        .options(selectinload(OrderDB.items))
    )
    return await db.scalar(stmt)


async def get_all_orders_filtered(db: AsyncSession, filters: OrderFilter):
    query = select(OrderDB).options(
        selectinload(OrderDB.items).selectinload(OrderItemDB.movie)
    )

    query = filters.filter(query)
    query = filters.sort(query)

    result = await db.scalars(query)
    return result.all()
