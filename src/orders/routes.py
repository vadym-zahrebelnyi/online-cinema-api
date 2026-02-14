"""
Module: orders.router

This module defines FastAPI routes for managing orders in the online cinema system.
It includes endpoints for users to create orders from their cart, view their orders,
and for admins to view all orders with filtering. Users can also cancel orders.

Endpoints:
    - GET /me: Retrieve all orders for the current authenticated user.
    - GET /admin/all: Retrieve all orders with filtering (admin only).
    - POST /: Create a new order from the current user's cart.
    - PATCH /{order_id}/cancel: Cancel an order by its ID.
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi_filter import FilterDepends
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.dependencies import allow_admin, get_current_user
from src.accounts.models import UserDB
from src.cart.dependencies import get_cart_service
from src.cart.services import CartService
from src.core import get_db, PaginationParams, get_pagination
from src.orders.crud import (
    cancel_order,
    create_order,
    get_all_orders_filtered,
    get_orders_by_user,
)
from src.orders.filters import OrderFilter
from src.orders.schemas import CancelSchema, OrderReadSchema

router = APIRouter()


@router.get(
    "/me",
    response_model=List[OrderReadSchema],
)
async def get_my_orders_endpoint(
    current_user: Annotated[UserDB, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Retrieve all orders for the currently authenticated user.

    Args:
        current_user (UserDB): The currently authenticated user (injected by Depends).
        db (AsyncSession): Async database session (injected by Depends).

    Returns:
        List[OrderReadSchema]: List of orders belonging to the current user.
    """
    return await get_orders_by_user(db, current_user.id)


@router.get("/admin/all", response_model=list[OrderReadSchema])
async def get_all_orders_admin(
    filters: Annotated[OrderFilter, FilterDepends(OrderFilter)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[UserDB, Depends(allow_admin)],
):
    """
    Retrieve all orders in the system with optional filters. Admin-only endpoint.

    Args:
        filters (OrderFilter): Filter criteria for orders (status, user_id, dates).
        db (AsyncSession): Async database session.
        _ (UserDB): Admin user verification (dependency, not used directly).

    Returns:
        List[OrderReadSchema]: List of orders matching the filters.
    """
    return await get_all_orders_filtered(db, filters, pagination)


@router.post("/", response_model=OrderReadSchema)
async def create_order_endpoint(
    current_user: Annotated[UserDB, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    cart_service: Annotated[CartService, Depends(get_cart_service)],
):
    """
    Create a new order from the current user's cart items.

    Steps:
        1. Validate the user's cart is not empty.
        2. Check for previously purchased or pending movies.
        3. Create an order and associated order items.
        4. Clear the user's cart.

    Args:
        current_user (UserDB): The currently authenticated user.
        db (AsyncSession): Async database session.
        cart_service (CartService): Service for cart management.

    Raises:
        HTTPException 400: If the cart is empty or other order creation errors occur.

    Returns:
        OrderReadSchema: The newly created order with its items.
    """
    try:
        return await create_order(db, current_user.id, cart_service)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{order_id}/cancel", response_model=CancelSchema)
async def cancel_order_endpoint(
    order_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Cancel an order by its ID.

    Args:
        order_id (int): ID of the order to cancel.
        db (AsyncSession): Async database session.

    Raises:
        HTTPException 400: If the order does not exist or cannot be cancelled.

    Returns:
        CancelSchema: Confirmation message indicating the order was cancelled.
    """
    try:
        await cancel_order(db, order_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CancelSchema(message="Order canceled")
