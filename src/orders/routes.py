from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.orders.crud import cancel_order
from src.accounts.dependencies import get_current_user
from src.accounts.models import UserDB
from src.core.database import get_db
from src.orders.crud import get_orders_by_user
from src.orders.schemas import OrderItemCreateSchema, OrderReadSchema, CancelShema
from src.orders.services import create_order_from_cart, get_order

router = APIRouter()


@router.get(
    "/meow",
    response_model=List[OrderReadSchema],
)
async def get_my_orders_endpoint(
    current_user: Annotated[UserDB, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get all user's orders"""
    return await get_orders_by_user(db, current_user.id)


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


@router.patch("/{order_id}/cancel", response_model=CancelShema)
async def pay_order_endpoint(
    order_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Cancel order by ID
    """
    try:
        await cancel_order(db, order_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CancelShema(message="Order canceled")
