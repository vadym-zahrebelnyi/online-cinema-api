from datetime import datetime
from decimal import Decimal

from redis.asyncio import Redis

from src.cart.crud import CartCRUD
from src.cart.exceptions import (
    CartLimitExceededError,
    MovieAlreadyInCartError,
    MovieAlreadyOwnedError,
    MovieNotFoundError,
)
from src.cart.schemas import CartItemReadSchema, CartReadSchema, MovieCartReadSchema


class CartService:
    """
    Business logic for managing shopping carts.

    This service implements a 'Hybrid Cart' pattern:
    1. Anonymous Users: Cart data is stored in Redis (ephemeral, expires in 7 days).
    2. Authenticated Users: Cart data is stored in PostgreSQL (persistent).

    It also handles merging an anonymous Redis cart into a persistent user cart
    upon login or registration.
    """

    MAX_CART_ITEMS = 50

    def __init__(self, repo: CartCRUD, redis: Redis):
        """
        Initialize the service.

        Args:
            repo (CartCRUD): Repository for database operations.
            redis (Redis): Redis client for anonymous cart operations.
        """
        self.repo = repo
        self.redis = redis

    async def get_cart(
        self, user_id: int | None, anon_id: str | None
    ) -> CartReadSchema:
        """
        Retrieve the current cart state.

        Priority logic:
        - If `user_id` is provided, fetches the persistent cart from DB.
        - If `user_id` is None but `anon_id` exists, fetches items from Redis.

        Args:
            user_id (int | None): ID of the logged-in user.
            anon_id (str | None): ID from the anonymous cookie.

        Returns:
            CartReadSchema: Schema containing cart items and total price.
        """
        items = []
        cart_id = None

        if user_id:
            cart = await self.repo.get_cart_by_user(user_id)
            if cart:
                cart_id = cart.id
                items = [
                    CartItemReadSchema(
                        id=item.id,
                        movie=MovieCartReadSchema.model_validate(item.movie),
                        added_at=item.added_at,
                    )
                    for item in cart.items
                ]

        elif anon_id:
            key = f"cart:{anon_id}"
            movie_ids = await self.redis.smembers(key)
            if movie_ids:
                ids = [int(mid) for mid in movie_ids]
                movies = await self.repo.get_movies_by_ids(ids)
                items = [
                    CartItemReadSchema(
                        id=m.id,
                        movie=MovieCartReadSchema.model_validate(m),
                        added_at=datetime.utcnow(),
                    )
                    for m in movies
                ]

        total_price = Decimal(sum(item.movie.price for item in items))

        return CartReadSchema(
            id=cart_id, items=items, total_price=total_price, total_items=len(items)
        )

    async def add_movie(self, movie_id: int, user_id: int | None, anon_id: str | None):
        """
        Add a movie to the cart.

        Validations:
        1. Movie must exist.
        2. Authenticated user cannot add movies they already own.
        3. Movie cannot already be in the cart.
        4. Cart cannot exceed MAX_CART_ITEMS.

        Args:
            movie_id (int): ID of the movie to add.
            user_id (int | None): ID of the logged-in user.
            anon_id (str | None): ID from the anonymous cookie.

        Raises:
            MovieNotFoundError
            MovieAlreadyOwnedError
            MovieAlreadyInCartError
            CartLimitExceededError
        """
        movie = await self.repo.get_movie(movie_id)
        if not movie:
            raise MovieNotFoundError()

        if user_id:
            session = self.repo.db
            try:
                already_owned = await self.repo.is_movie_available_to_buy(
                    user_id, movie_id
                )
                if already_owned:
                    raise MovieAlreadyOwnedError()

                cart = await self.repo.get_cart_by_user(user_id)

                if cart and await self.repo.item_exists(cart.id, movie_id):
                    raise MovieAlreadyInCartError()

                if cart and len(cart.items) >= self.MAX_CART_ITEMS:
                    raise CartLimitExceededError(self.MAX_CART_ITEMS)

                if not cart:
                    cart = await self.repo.create_cart(user_id)

                await self.repo.add_item(cart.id, movie_id)

                await session.commit()
            except:
                await session.rollback()
                raise

        elif anon_id:
            key = f"cart:{anon_id}"
            if await self.redis.sismember(key, str(movie_id)):
                raise MovieAlreadyInCartError()
            await self.redis.sadd(key, str(movie_id))
            await self.redis.expire(key, 604800)

    async def remove_item(
        self, movie_id: int, user_id: int | None, anon_id: str | None
    ):
        """
        Remove a movie from the cart.

        Args:
            movie_id (int): ID of the movie to remove.
            user_id (int | None): ID of the logged-in user.
            anon_id (str | None): ID from the anonymous cookie.
        """
        if user_id:
            session = self.repo.db
            try:
                cart = await self.repo.get_cart_by_user(user_id)
                if cart:
                    await self.repo.remove_item(cart.id, movie_id)
                await session.commit()
            except:
                await session.rollback()
                raise

        elif anon_id:
            key = f"cart:{anon_id}"
            await self.redis.srem(key, str(movie_id))

    async def clear_cart(self, user_id: int | None, anon_id: str | None):
        """
        Clear all items from the cart.

        Args:
            user_id (int | None): ID of the logged-in user.
            anon_id (str | None): ID from the anonymous cookie.
        """
        if user_id:
            session = self.repo.db
            try:
                cart = await self.repo.get_cart_by_user(user_id)
                if cart:
                    await self.repo.clear_cart(cart.id)
                await session.commit()
            except:
                await session.rollback()
                raise

        elif anon_id:
            key = f"cart:{anon_id}"
            await self.redis.delete(key)

    async def merge_anon_cart(self, anon_id: str, user_id: int):
        """
        Merge an anonymous Redis cart into the persistent user cart.

        Rules:
        - Skip movies that are invalid, already owned, or already in the user's cart.
        - Delete Redis cart after merging.

        Args:
            anon_id (str): Anonymous cart ID.
            user_id (int): Logged-in user ID.
        """
        redis_key = f"cart:{anon_id}"
        anon_movie_ids_raw = await self.redis.smembers(redis_key)
        if not anon_movie_ids_raw:
            return

        ids_to_check = [int(mid) for mid in anon_movie_ids_raw]

        session = self.repo.db
        try:
            valid_movies = await self.repo.get_movies_by_ids(ids_to_check)
            if not valid_movies:
                await self.redis.delete(redis_key)
                return

            cart = await self.repo.get_cart_by_user(user_id)
            if not cart:
                cart = await self.repo.create_cart(user_id)

            for movie in valid_movies:
                movie_id = movie.id
                if await self.repo.is_movie_available_to_buy(user_id, movie_id):
                    continue
                if await self.repo.item_exists(cart.id, movie_id):
                    continue
                await self.repo.add_item(cart.id, movie_id)

            await session.commit()
            await self.redis.delete(redis_key)
        except:
            await session.rollback()
            raise
