from typing import Annotated
from uuid import uuid4

from fastapi import Cookie, Depends, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.cart.crud import CartCRUD
from src.cart.services import CartService
from src.core import get_db
from src.core.dependencies import get_redis


async def get_anon_cart_id(
    response: Response, cart_id: Annotated[str | None, Cookie()] = None
) -> str:
    if cart_id is None:
        new_id = str(uuid4())
        response.set_cookie(key="cart_id", value=new_id, httponly=True, max_age=604800)
        return new_id
    return cart_id


async def get_cart_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> CartService:
    repo = CartCRUD(db)

    return CartService(repo, redis)
