"""
Module: orders.services

This module contains service functions for handling orders in the online cinema system.
These functions encapsulate the business logic for creating, retrieving, cancelling,
and filtering orders. They interact with the database using SQLAlchemy AsyncSession
and with the shopping cart via CartService.

Functions:
    - create_order: Create a new order from a user's cart.
    - get_orders_by_user: Retrieve all orders for a specific user.
    - cancel_order: Cancel an order by changing its status to CANCELLED.
    - get_order_with_items: Retrieve an order with its items for payment processing.
    - get_all_orders_filtered: Retrieve all orders based on applied filters.
"""

from decimal import Decimal
from typing import List

from fastapi import HTTPException
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.cart.models import CartDB, CartItemDB
from src.cart.services import CartService
from src.core.dependencies import PaginationParams
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
    """
    Create a new order for a user based on the contents of their cart.

    Steps:
        1. Load the user's cart and ensure it is not empty.
        2. Check if any movies in the cart are already paid.
        3. Check if there are pending orders with the same movies.
        4. Calculate total amount for the order.
        5. Create the OrderDB instance and related OrderItemDB entries.
        6. Clear the user's cart.
        7. Commit the transaction and return the newly created order.

    Args:
        db (AsyncSession): The async database session.
        user_id (int): ID of the user placing the order.
        cart_service (CartService): Service for managing the user's cart.

    Raises:
        CartIsEmptyError: If the user's cart is empty.
        HTTPException(409): If the user has already purchased a movie
            or has a pending order for a movie.

    Returns:
        OrderDB: The newly created order with items loaded.
    """
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
    """
    Retrieve all orders placed by a specific user.

    Args:
        db (AsyncSession): The async database session.
        user_id (int): ID of the user.

    Returns:
        List[OrderDB]: List of the user's orders.
    """
    result = await db.scalars(select(OrderDB).where(OrderDB.user_id == user_id))
    return list(result.all())


async def cancel_order(db: AsyncSession, order_id: int) -> None:
    """
    Cancel an existing order by setting its status to CANCELLED.

    Args:
        db (AsyncSession): The async database session.
        order_id (int): ID of the order to cancel.

    Raises:
        OrderNotFoundError: If the order with the given ID does not exist.
    """
    order = await db.get(OrderDB, order_id)
    if not order:
        raise OrderNotFoundError(f"Order {order_id} not found")
    order.status = OrderStatusEnum.CANCELLED
    await db.commit()


async def get_order_with_items(db: AsyncSession, order_id: int) -> OrderDB | None:
    """
    Retrieve a single order along with its items, primarily for payment processing.

    Args:
        db (AsyncSession): The async database session.
        order_id (int): ID of the order.

    Returns:
        OrderDB | None: The order with items loaded, or None if not found.
    """
    stmt = (
        select(OrderDB)
        .where(OrderDB.id == order_id)
        .options(selectinload(OrderDB.items))
    )
    return await db.scalar(stmt)


async def get_all_orders_filtered(
    db: AsyncSession, filters: OrderFilter, pagination: PaginationParams
) -> List[OrderDB]:
    """
    Retrieve all orders from the database with applied filters and sorting.

    Args:
        db (AsyncSession): The async database session.
        filters (OrderFilter): Filter object containing filter criteria and sorting.

    Returns:
        List[OrderDB]: List of orders matching the filters.
    """
    query = select(OrderDB).options(
        selectinload(OrderDB.items).selectinload(OrderItemDB.movie)
    )

    query = filters.filter(query)
    query = filters.sort(query)

    query = query.offset(pagination.offset).limit(pagination.limit)

    result = await db.scalars(query)
    return result.all()
