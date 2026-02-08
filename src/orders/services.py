from decimal import Decimal
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.orders.exceptions import MovieNotAvailableError
from src.cart.models import CartItemDB
from src.movies.models import MovieDB
from src.orders.models import OrderItemDB


async def calculate_total_amount(db: AsyncSession, cart_items: List[CartItemDB]) -> Tuple[Decimal, List[MovieDB]]:
    """Calculate total_amount + check film availability"""
    movie_ids = [item.movie_id for item in cart_items]
    movies: List[MovieDB] = (await db.scalars(select(MovieDB).where(MovieDB.id.in_(movie_ids)))).all()

    existing_movie_ids = {movie.id for movie in movies}
    deleted_movies = [item.movie_id for item in cart_items if item.movie_id not in existing_movie_ids]
    if deleted_movies:
        raise MovieNotAvailableError(f"Movies with IDs {deleted_movies} not available")

    total_amount: Decimal = sum((Decimal(movie.price) for movie in movies), Decimal("0.00"))
    return total_amount, movies


async def create_order_items_from_cart(db: AsyncSession, order_id: int, movies: list[MovieDB]):
    """Create Order Items"""
    for movie in movies:
        order_item = OrderItemDB(
            order_id=order_id,
            movie_id=movie.id,
            price_at_order=Decimal(movie.price)
        )
        db.add(order_item)
