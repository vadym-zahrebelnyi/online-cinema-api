from datetime import datetime
from decimal import Decimal

from redis.asyncio import Redis

from src.cart.crud import CartCRUD
from src.cart.exceptions import (
    MovieAlreadyInCartError,
    MovieAlreadyOwnedError,
    MovieNotFoundError,
)
from src.cart.schemas import CartItemReadSchema, CartReadSchema, MovieCartReadSchema


class CartService:
    def __init__(self, repo: CartCRUD, redis: Redis):
        self.repo = repo
        self.redis = redis

    async def get_cart(
        self, user_id: int | None, anon_id: str | None
    ) -> CartReadSchema:
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
        movie = await self.repo.get_movie(movie_id)
        if not movie:
            raise MovieNotFoundError()

        if user_id:
            already_owned = await self.repo.is_movie_available_to_buy(user_id, movie_id)
            if already_owned:
                raise MovieAlreadyOwnedError()

            cart = await self.repo.get_cart_by_user(user_id)
            if not cart:
                cart = await self.repo.create_cart(user_id)

            if await self.repo.item_exists(cart.id, movie_id):
                raise MovieAlreadyInCartError()

            await self.repo.add_item(cart.id, movie_id)

        elif anon_id:
            key = f"cart:{anon_id}"

            if await self.redis.sismember(key, str(movie_id)):
                raise MovieAlreadyInCartError()

            await self.redis.sadd(key, str(movie_id))
            await self.redis.expire(key, 604800)

    async def remove_item(
        self, movie_id: int, user_id: int | None, anon_id: str | None
    ):
        if user_id:
            cart = await self.repo.get_cart_by_user(user_id)
            if cart:
                await self.repo.remove_item(cart.id, movie_id)

        elif anon_id:
            key = f"cart:{anon_id}"
            await self.redis.srem(key, str(movie_id))

    async def clear_cart(self, user_id: int | None, anon_id: str | None):
        if user_id:
            cart = await self.repo.get_cart_by_user(user_id)
            if cart:
                await self.repo.clear_cart(cart.id)

        elif anon_id:
            key = f"cart:{anon_id}"
            await self.redis.delete(key)

    async def merge_anon_cart(self, anon_id: str, user_id: int):
        redis_key = f"cart:{anon_id}"

        anon_movie_ids_raw = await self.redis.smembers(redis_key)

        if not anon_movie_ids_raw:
            return

        ids_to_check = [int(mid) for mid in anon_movie_ids_raw]

        valid_movies = await self.repo.get_movies_by_ids(ids_to_check)

        if not valid_movies:
            await self.redis.delete(redis_key)
            return

        cart = await self.repo.get_cart_by_user(user_id)
        if not cart:
            cart = await self.repo.create_cart(user_id)

        for movie in valid_movies:
            movie_id = movie.id

            is_owned = await self.repo.is_movie_available_to_buy(user_id, movie_id)
            if is_owned:
                continue

            exists_in_cart = await self.repo.item_exists(cart.id, movie_id)
            if exists_in_cart:
                continue

            await self.repo.add_item(cart.id, movie_id)

        await self.redis.delete(redis_key)
