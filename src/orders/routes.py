from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.orders.crud import get_orders_by_user
from src.orders.schemas import OrderItemCreateSchema, OrderReadSchema
from src.orders.services import create_order_from_cart, get_order, mark_order_paid

router = APIRouter()


@router.get(
    "/",
    response_model=List[OrderReadSchema],
)
async def get_my_orders_endpoint(
    user_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get all user's orders"""
    return await get_orders_by_user(db, user_id)


@router.post("/", response_model=OrderReadSchema)
async def create_order_endpoint(
    user_id: int,
    cart_items: List[OrderItemCreateSchema],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create an order from user's cart items
    """
    try:
        order = await create_order_from_cart(
            db, user_id, [item.model_dump() for item in cart_items]
        )
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}", response_model=OrderReadSchema)
async def get_order_endpoint(
    order_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Get order by ID
    """
    try:
        order = await get_order(db, order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{order_id}/pay", response_model=OrderReadSchema)
async def pay_order_endpoint(
    order_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Mark an order as PAID
    """
    try:
        order = await mark_order_paid(db, order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
