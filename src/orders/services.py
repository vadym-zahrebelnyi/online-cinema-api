"""
Module: orders.helpers

This module provides helper functions for order processing in the online cinema system.
Includes functions for calculating the total order amount, checking movie availability,
and creating order items from a cart.

Functions:
    - calculate_total_amount: Calculate the total price of cart items and check movie availability.
    - create_order_items_from_cart: Create order items in the database based on a list of movies.
"""

from decimal import Decimal
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cart.models import CartItemDB
from src.movies.models import MovieDB
from src.orders.exceptions import MovieNotAvailableError
from src.orders.models import OrderItemDB


async def calculate_total_amount(
    db: AsyncSession, cart_items: List[CartItemDB]
) -> Tuple[Decimal, List[MovieDB]]:
    """
    Calculate the total amount for a list of cart items and check movie availability.

    Steps:
        1. Extract movie IDs from cart items.
        2. Retrieve movies from the database.
        3. Check if any movies have been deleted/unavailable.
        4. Calculate the total amount as the sum of movie prices.

    Args:
        db (AsyncSession): The async database session.
        cart_items (List[CartItemDB]): List of cart items to calculate.

    Raises:
        MovieNotAvailableError: If one or more movies in the cart are no longer available.

    Returns:
        Tuple[Decimal, List[MovieDB]]:
            - total_amount: Total price of all available movies.
            - movies: List of available MovieDB objects corresponding to the cart.
    """
    movie_ids = [item.movie_id for item in cart_items]
    movies: List[MovieDB] = (
        await db.scalars(select(MovieDB).where(MovieDB.id.in_(movie_ids)))
    ).all()

    existing_movie_ids = {movie.id for movie in movies}
    deleted_movies = [
        item.movie_id for item in cart_items if item.movie_id not in existing_movie_ids
    ]
    if deleted_movies:
        raise MovieNotAvailableError(f"Movies with IDs {deleted_movies} not available")

    total_amount: Decimal = sum(
        (Decimal(movie.price) for movie in movies), Decimal("0.00")
    )
    return total_amount, movies


async def create_order_items_from_cart(
    db: AsyncSession, order_id: int, movies: list[MovieDB]
):
    """
    Create OrderItemDB entries in the database based on a list of movies.

    Args:
        db (AsyncSession): The async database session.
        order_id (int): ID of the order for which items are being created.
        movies (list[MovieDB]): List of MovieDB instances to add to the order.

    Notes:
        Each movie will generate one OrderItemDB with the current price at order time.
        Objects are added to the session but not committed. Commit should be done externally.
    """
    for movie in movies:
        order_item = OrderItemDB(
            order_id=order_id, movie_id=movie.id, price_at_order=Decimal(movie.price)
        )
        db.add(order_item)
