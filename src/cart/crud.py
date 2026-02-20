from typing import Sequence

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.cart.models import CartDB, CartItemDB
from src.movies.models import MovieDB
from src.orders.models import OrderDB, OrderItemDB, OrderStatusEnum


class CartCRUD:
    """
    Data Access Object (DAO) for Cart operations.

    Handles all direct database interactions related to shopping carts,
    including retrieval, item addition/removal, and availability checks.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the CRUD with a database session.

        Args:
            db (AsyncSession): The SQLAlchemy async session.
        """
        self.db = db

    async def get_cart_by_user(self, user_id: int) -> CartDB | None:
        """
        Retrieve a user's cart with all items and associated movie details.

        Uses eager loading (selectinload) to fetch related movies and their genres
        in an optimized way to prevent N+1 query problems.

        Args:
            user_id (int): The ID of the user.

        Returns:
            CartDB | None: The cart object if found, otherwise None.
        """
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
        """
        Create a new empty cart for a user.

        Args:
            user_id (int): The ID of the user.

        Returns:
            CartDB: The newly created cart instance.
        """
        cart = CartDB(user_id=user_id)
        self.db.add(cart)
        await self.db.flush()
        await self.db.refresh(cart)
        return cart

    async def add_item(self, cart_id: int, movie_id: int) -> CartItemDB:
        """
        Add a movie to a specific cart.

        Args:
            cart_id (int): The ID of the target cart.
            movie_id (int): The ID of the movie to add.

        Returns:
            CartItemDB: The created cart item record.
        """
        item = CartItemDB(cart_id=cart_id, movie_id=movie_id)
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def is_movie_available_to_buy(self, user_id: int, movie_id: int) -> bool:
        """
        Check if a user has already purchased or has a pending order for a movie.

        This prevents duplicate purchases of digital content.

        Args:
            user_id (int): The ID of the user.
            movie_id (int): The ID of the movie.

        Returns:
            bool: True if the movie is already 'locked' (owned or pending), False otherwise.
        """
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
        """
        Check if a specific movie is already present in the cart.

        Args:
            cart_id (int): The ID of the cart.
            movie_id (int): The ID of the movie.

        Returns:
            bool: True if the item exists in the cart, False otherwise.
        """
        stmt = select(
            exists().where(
                CartItemDB.cart_id == cart_id, CartItemDB.movie_id == movie_id
            )
        )
        return await self.db.scalar(stmt)

    async def remove_item(self, cart_id: int, movie_id: int) -> None:
        """
        Remove a specific movie from the cart.

        Args:
            cart_id (int): The ID of the cart.
            movie_id (int): The ID of the movie to remove.
        """
        await self.db.execute(
            delete(CartItemDB).where(
                CartItemDB.cart_id == cart_id, CartItemDB.movie_id == movie_id
            )
        )

    async def clear_cart(self, cart_id: int) -> None:
        """
        Remove all items from a specific cart.

        Args:
            cart_id (int): The ID of the cart to empty.
        """
        await self.db.execute(delete(CartItemDB).where(CartItemDB.cart_id == cart_id))

    async def get_movie(self, movie_id: int) -> MovieDB | None:
        """
        Fetch a movie by its ID.

        Args:
            movie_id (int): The ID of the movie.

        Returns:
            MovieDB | None: The movie object or None if not found.
        """
        return await self.db.get(MovieDB, movie_id)

    async def get_movies_by_ids(self, movie_ids: list[int]) -> Sequence[MovieDB]:
        """
        Fetch a list of movies based on a list of IDs.

        Used primarily for hydrating anonymous carts where data is stored in Redis.

        Args:
            movie_ids (list[int]): A list of movie IDs.

        Returns:
            Sequence[MovieDB]: A list of MovieDB objects.
        """
        if not movie_ids:
            return []
        query = select(MovieDB).where(MovieDB.id.in_(movie_ids))
        result = await self.db.execute(query)
        return result.scalars().all()
