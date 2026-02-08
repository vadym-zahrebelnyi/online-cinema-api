from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import joinedload

from src.cart.models import CartDB, CartItemDB
from src.movies.models import MovieDB


class CartCRUD:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(self, user_id: int) -> CartDB | None:
        """
        Return user's cart or None if it does not exist.
        """

        stmt = select(CartDB).where(CartDB.user_id == user_id)

        return await self.db.scalar(stmt)

    async def create(self, user_id: int) -> CartDB:
        """
        Create a new cart for a user.
        """

        new_cart = CartDB(user_id=user_id)
        self.db.add(new_cart)
        await self.db.flush()
        await self.db.refresh(new_cart)

        return new_cart

    async def get_or_create(self, user_id: int) -> CartDB:
        """
        Get existing cart or create a new one atomically-ish.
        """

        cart = await self.get_by_user_id(user_id)

        return cart or await self.create(user_id)

    async def get_cart_with_details_by_user_id(self, user_id: int) -> CartDB | None: # NEW METHOD
        """
        Fetches the user's cart along with all its items and associated movie details.
        """
        stmt = (
            select(CartDB)
            .options(
                joinedload(CartDB.items).joinedload(CartItemDB.movie).joinedload(MovieDB.genres)
            )
            .where(CartDB.user_id == user_id)
        )
        return await self.db.scalar(stmt)


class CartItemCRUD:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, cart_id: int, movie_id: int) -> CartItemDB:
        """
        Adds a movie to the specified cart.
        """
        new_cart_item = CartItemDB(cart_id=cart_id, movie_id=movie_id)
        self.db.add(new_cart_item)
        await self.db.flush()
        await self.db.refresh(new_cart_item)

        return new_cart_item

    async def get(self, cart_id: int, movie_id: int) -> CartItemDB | None:
        """
        Returns a specific cart item or None if it does not exist.
        """
        stmt = select(CartItemDB).where(
            CartItemDB.cart_id == cart_id, CartItemDB.movie_id == movie_id
        )

        return await self.db.scalar(stmt)

    async def remove(self, cart_id: int, movie_id: int) -> None:
        """
        Removes a specific movie from the cart.
        """
        stmt = delete(CartItemDB).where(
            CartItemDB.cart_id == cart_id, CartItemDB.movie_id == movie_id
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def clear_cart(self, cart_id: int) -> None:
        """
        Removes all items from the specified cart.
        """
        stmt = delete(CartItemDB).where(CartItemDB.cart_id == cart_id)
        await self.db.execute(stmt)
        await self.db.flush()
