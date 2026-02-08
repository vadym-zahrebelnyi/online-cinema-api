from functools import partial
from typing import Callable

from src.cart.crud import CartCRUD, CartItemCRUD
from src.cart.exceptions import (
    MovieAlreadyInCartException,
    MovieNotInCartException,
    MovieNotFoundException,
    MovieAlreadyPurchasedException,
)
from src.cart.schemas import CartReadSchema
from src.movies.models import MovieDB
from fastapi import HTTPException


class CartService:
    def __init__(
        self,
        cart_crud: CartCRUD,
        cart_item_crud: CartItemCRUD,
        get_movie_by_id: Callable[[int], MovieDB | None],
        create_order_from_cart: Callable[[int, list[dict]], None],
    ) -> None:
        self.cart_crud = cart_crud
        self.cart_item_crud = cart_item_crud
        self.get_movie_by_id = get_movie_by_id
        self.create_order_from_cart = create_order_from_cart

    async def _get_user_cart_or_create(self, user_id: int):
        """
        Helper to get or create a cart for the user.
        """
        cart = await self.cart_crud.get_or_create(user_id)
        await self.cart_crud.db.refresh(cart)
        return cart

    async def add_movie_to_cart(self, user_id: int, movie_id: int) -> CartReadSchema:
        """
        Adds a movie to the user's cart.
        Raises:
            MovieNotFoundException: If the movie does not exist.
            MovieAlreadyInCartException: If the movie is already in the cart.
            MovieAlreadyPurchasedException: If the movie has already been purchased by the user.
        """
        try:
            cart = await self._get_user_cart_or_create(user_id)

            # 1. Check if movie exists
            movie = await self.get_movie_by_id(movie_id)
            if not movie:
                raise MovieNotFoundException

            # 2. Check if movie is already in cart (validation)
            if await self.cart_item_crud.get(cart.id, movie_id):
                raise MovieAlreadyInCartException

            # 3. TODO: Check if movie is already purchased by the user (validation)
            # This would involve querying the orders/purchases module.
            # For now, this is a placeholder.
            # purchased = await self.orders_crud.has_user_purchased_movie(user_id, movie_id)
            # if purchased:
            #     raise MovieAlreadyPurchasedException

            await self.cart_item_crud.add(cart.id, movie_id)
            await self.cart_crud.db.commit()

            updated_cart = await self.cart_crud.get_cart_with_details_by_user_id(user_id)
            return CartReadSchema.model_validate(updated_cart)
        except Exception:
            await self.cart_crud.db.rollback()
            raise

    async def remove_movie_from_cart(self, user_id: int, movie_id: int) -> CartReadSchema:
        """
        Removes a movie from the user's cart.
        Raises:
            MovieNotInCartException: If the movie is not found in the cart.
        """
        try:
            cart = await self.cart_crud.get_by_user_id(user_id)
            if not cart:
                # If there's no cart, the movie cannot be in it.
                raise MovieNotInCartException

            # Check if movie is in cart
            cart_item = await self.cart_item_crud.get(cart.id, movie_id)
            if not cart_item:
                raise MovieNotInCartException

            await self.cart_item_crud.remove(cart.id, movie_id)
            await self.cart_crud.db.commit()

            updated_cart = await self.cart_crud.get_cart_with_details_by_user_id(user_id)
            return CartReadSchema.model_validate(updated_cart)
        except Exception:
            await self.cart_crud.db.rollback()
            raise

    async def get_user_cart(self, user_id: int) -> CartReadSchema:
        """
        Retrieves the user's cart contents.
        """
        cart = await self.cart_crud.get_cart_with_details_by_user_id(user_id)
        if not cart:
            return CartReadSchema(id=-1, items=[]) # Return empty cart representation
        return CartReadSchema.model_validate(cart)

    async def clear_user_cart(self, user_id: int) -> CartReadSchema:
        """
        Clears all items from the user's cart.
        """
        try:
            cart = await self.cart_crud.get_by_user_id(user_id)
            if not cart or not cart.items:
                return CartReadSchema(id=cart.id if cart else -1, items=[]) # Already empty or no cart

            await self.cart_item_crud.clear_cart(cart.id)
            await self.cart_crud.db.commit()

            updated_cart = await self.cart_crud.get_cart_with_details_by_user_id(user_id)
            return CartReadSchema.model_validate(updated_cart)
        except Exception:
            await self.cart_crud.db.rollback()
            raise

    async def checkout_cart(self, user_id: int) -> dict:
        """
        Proceeds to checkout for the user's cart, creating an order.
        """
        try:
            cart = await self.cart_crud.get_cart_with_details_by_user_id(user_id)
            if not cart or not cart.items:
                raise HTTPException(status_code=400, detail="Cart is empty, cannot checkout.")

            # TODO: Add validation: "Ensure all movies are available for purchase before creating an order."
            # This would likely involve calling a method in the movies service/crud.

            # TODO: Add validation: "Exclude movies already purchased, notifying the user."
            # This would require filtering cart.items and potentially raising an exception
            # or returning a filtered list with a notification.

            order_items_data = [
                {"movie_id": item.movie.id, "price_at_order": item.movie.price}
                for item in cart.items
            ]

            # Call the create_order_from_cart function (bound with db session).
            # This function is assumed to handle its own transaction or participate
            # in the current one. Given it takes `db` as a partial, it's designed to
            # operate within the same session.
            order = await self.create_order_from_cart(user_id, order_items_data)

            # Clear the cart after successful order creation
            await self.cart_item_crud.clear_cart(cart.id)

            await self.cart_crud.db.commit()

            return {"message": "Checkout successful", "order_id": order.id}
        except HTTPException: # Re-raise FastAPI HTTPExceptions directly
            raise
        except Exception:
            await self.cart_crud.db.rollback()
            raise
