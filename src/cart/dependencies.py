from functools import partial

from typing import Annotated, Callable, List, Dict, Any
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.movies.models import MovieDB
from src.core import get_db
from src.cart.crud import CartCRUD, CartItemCRUD
from src.cart.services import CartService
from src.orders.services import create_order_from_cart


async def get_movie_by_id(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Dependency to provide a functional Movie CRUD method (get_by_id), bound to the current db session.
    """
    async def get_movie_by_id_bound(movie_id: int) -> MovieDB | None:
        return await db.get(MovieDB, movie_id)
    return get_movie_by_id_bound


async def get_cart_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> CartCRUD:
    """
    Dependency to provide CartCRUD instance.
    """
    return CartCRUD(db)


async def get_cart_item_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> CartItemCRUD:
    """
    Dependency to provide CartItemCRUD instance.
    """
    return CartItemCRUD(db)


async def get_create_order_from_cart_func(db: Annotated[AsyncSession, Depends(get_db)]) -> Callable[[int, list[dict]], Any]:
    """
    Dependency to provide the create_order_from_cart function, bound to the current db session.
    """
    return partial(create_order_from_cart, db)


async def get_cart_service(
    cart_crud: Annotated[CartCRUD, Depends(get_cart_crud)],
    cart_item_crud: Annotated[CartItemCRUD, Depends(get_cart_item_crud)],
    get_movie_by_id: Annotated[Callable, Depends(get_movie_by_id)],
    create_order_from_cart_func: Annotated[Callable, Depends(get_create_order_from_cart_func)],
) -> CartService:
    """
    Dependency to provide CartService instance.
    """
    return CartService(
        cart_crud=cart_crud,
        cart_item_crud=cart_item_crud,
        get_movie_by_id=get_movie_by_id,
        create_order_from_cart_func=create_order_from_cart_func
    )