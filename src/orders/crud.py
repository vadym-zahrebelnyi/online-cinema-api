from decimal import Decimal
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.orders.exceptions import OrderNotFoundError
from src.orders.models import OrderDB, OrderItemDB, OrderStatusEnum
from src.orders.schemas import OrderItemCreateSchema


async def create_order(
    db: AsyncSession, user_id: int, total_amount: Decimal
) -> OrderDB:
    """Create empty order without items"""
    order = OrderDB(
        user_id=user_id, total_amount=total_amount, status=OrderStatusEnum.PENDING
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def add_order_items(
    db: AsyncSession, order_id: int, items: List[OrderItemCreateSchema]
) -> List[OrderItemDB]:
    """Add elements for order"""
    order_items = []
    for item in items:
        order_item = OrderItemDB(
            order_id=order_id,
            movie_id=item.movie_id,
            price_at_order=item.price_at_order,
        )
        db.add(order_item)
        order_items.append(order_item)

    await db.commit()
    for item in order_items:
        await db.refresh(item)

    return order_items


async def get_order_by_id(db: AsyncSession, order_id: int) -> OrderDB | None:
    """Return order by id"""
    order = await db.scalar(select(OrderDB).where(OrderDB.id == order_id))
    if not order:
        raise OrderNotFoundError(f"Order {order_id} not found")
    return order


async def get_orders_by_user(db: AsyncSession, user_id: int) -> List[OrderDB]:
    """Return list of user's orders"""
    result = await db.scalars(select(OrderDB).where(OrderDB.user_id == user_id))
    return list(result.all())


async def update_order_status(
    db: AsyncSession, order: OrderDB, status: OrderStatusEnum
) -> OrderDB:
    """Update order status"""
    order.status = status
    await db.commit()
    await db.refresh(order)
    return order


async def cancel_order(db: AsyncSession, order: OrderDB) -> None:
    """Delete order with items"""
    await db.delete(order)
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
