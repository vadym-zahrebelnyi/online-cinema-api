from typing import Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.orders.crud import (
    add_order_items,
    create_order,
    get_order_by_id,
    update_order_status,
)
from src.orders.models import OrderStatusEnum
from src.orders.schemas import OrderItemCreateSchema


async def create_order_from_cart(
    db: AsyncSession, user_id: int, cart_items: List[Dict]
):
    """Create order from cart_items"""
    if not cart_items:
        raise ValueError("Cart is empty")

    total_amount = sum(item["price_at_order"] for item in cart_items)

    order = await create_order(db, user_id, total_amount)

    items_to_add = [
        OrderItemCreateSchema(movie_id=item["movie_id"], price_at_order=item["price"])
        for item in cart_items
    ]
    await add_order_items(db, order.id, items_to_add)

    return order


async def mark_order_paid(db: AsyncSession, order_id: int):
    """Change order status as PAID"""
    order = await get_order_by_id(db, order_id)
    if not order:
        raise ValueError("Order not found")

    if order.status == OrderStatusEnum.PAID:
        raise ValueError("Order is already paid")

    return await update_order_status(db, order, OrderStatusEnum.PAID)


async def get_order(db: AsyncSession, order_id: int):
    """Return order by id"""
    order = await get_order_by_id(db, order_id)
    if not order:
        raise ValueError("Order not found")
    return order
