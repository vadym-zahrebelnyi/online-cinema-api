from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Cookie, Depends, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.cart.crud import CartCRUD
from src.cart.services import CartService
from src.core import get_db, get_redis


async def get_anon_cart_id(
    response: Response, cart_id: Annotated[str | None, Cookie()] = None
) -> str:
    """
    Retrieve or generate an anonymous cart ID from cookies.

    If the user does not have a 'cart_id' cookie, a new UUID is generated
    and set in the response cookies with a 7-day expiration.
    If an existing 'cart_id' cookie is invalid, a new one is generated.

    Args:
        response (Response): The FastAPI response object to set the cookie.
        cart_id (str | None): The current value of the 'cart_id' cookie.

    Returns:
        str: The UUID string representing the anonymous cart.
    """
    valid_uuid = None
    if cart_id:
        try:
            valid_uuid = UUID(cart_id)
        except ValueError:
            pass

    if not valid_uuid:
        new_id = str(uuid4())
        response.set_cookie(key="cart_id", value=new_id, httponly=True, max_age=604800)
        return new_id
    return str(valid_uuid)


async def get_cart_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> CartService:
    """
    Dependency injection factory for the CartService.

    Initializes the CartRepository with a database session and injects it,
    along with the Redis client, into the CartService.

    Args:
        db (AsyncSession): The active database session.
        redis (Redis): The active Redis client connection.

    Returns:
        CartService: An initialized instance of the cart business logic service.
    """
    repo = CartCRUD(db)

    return CartService(repo, redis)
