from typing import Sequence

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.cart.models import CartDB, CartItemDB
from src.movies.models import MovieDB
from src.orders.models import OrderDB, OrderItemDB, OrderStatusEnum


class CartCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_cart_by_user(self, user_id: int) -> CartDB | None:
        query = (
            select(CartDB)
            .where(CartDB.user_id == user_id)
            .options(
                selectinload(CartDB.items)
                .selectinload(CartItemDB.movie)
                .selectinload(MovieDB.genres)
            )
        )
        return await self.db.scalar(query)

    async def create_cart(self, user_id: int) -> CartDB:
        cart = CartDB(user_id=user_id)
        self.db.add(cart)
        await self.db.commit()
        await self.db.refresh(cart)
        return cart

    async def add_item(self, cart_id: int, movie_id: int) -> CartItemDB:
        item = CartItemDB(cart_id=cart_id, movie_id=movie_id)
        self.db.add(item)
        await self.db.commit()
        return item

    async def is_movie_available_to_buy(self, user_id: int, movie_id: int) -> bool:
        stmt = (
            select(exists(1))
            .select_from(OrderItemDB)
            .join(OrderDB, OrderItemDB.order_id == OrderDB.id)
            .where(
                OrderDB.user_id == user_id,
                OrderDB.status.in_([OrderStatusEnum.PAID, OrderStatusEnum.PENDING]),
                OrderItemDB.movie_id == movie_id,
            )
        )
        is_locked = await self.db.scalar(stmt) or False

        return is_locked

    async def item_exists(self, cart_id: int, movie_id: int) -> bool:
        stmt = select(
            exists().where(
                CartItemDB.cart_id == cart_id, CartItemDB.movie_id == movie_id
            )
        )
        return await self.db.scalar(stmt)

    async def remove_item(self, cart_id: int, movie_id: int) -> None:
        await self.db.execute(
            delete(CartItemDB).where(
                CartItemDB.cart_id == cart_id, CartItemDB.movie_id == movie_id
            )
        )
        await self.db.commit()

    async def clear_cart(self, cart_id: int) -> None:
        await self.db.execute(delete(CartItemDB).where(CartItemDB.cart_id == cart_id))
        await self.db.commit()

    async def get_movie(self, movie_id: int) -> MovieDB | None:
        return await self.db.get(MovieDB, movie_id)

    async def get_movies_by_ids(self, movie_ids: list[int]) -> Sequence[MovieDB]:
        if not movie_ids:
            return []
        query = select(MovieDB).where(MovieDB.id.in_(movie_ids))
        result = await self.db.execute(query)
        return result.scalars().all()
