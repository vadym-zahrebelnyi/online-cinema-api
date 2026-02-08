from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from src.accounts.dependencies import get_current_user_id
from src.cart.dependencies import get_cart_service
from src.cart.exceptions import (
    MovieNotFoundException,
    MovieAlreadyInCartException,
    MovieNotInCartException,
    MovieAlreadyPurchasedException,
)
from src.cart.schemas import CartReadSchema, CartItemCreateSchema
from src.cart.services import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.post(
    "/items/",
    response_model=CartReadSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a movie to the user's cart",
)
async def add_movie_to_cart_route(
    item_data: CartItemCreateSchema,
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    cart_service: Annotated[CartService, Depends(get_cart_service)],
):
    try:
        cart = await cart_service.add_movie_to_cart(current_user_id, item_data.movie_id)
        return cart
    except MovieNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found.")
    except MovieAlreadyInCartException:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Movie is already in the cart.")
    except MovieAlreadyPurchasedException:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Movie has already been purchased by the user.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


@router.delete(
    "/items/{movie_id}",
    response_model=CartReadSchema,
    status_code=status.HTTP_200_OK,
    summary="Remove a movie from the user's cart",
)
async def remove_movie_from_cart_route(
    movie_id: int,
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    cart_service: Annotated[CartService, Depends(get_cart_service)],
):
    try:
        cart = await cart_service.remove_movie_from_cart(current_user_id, movie_id)
        return cart
    except MovieNotInCartException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie is not in the cart.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


@router.get(
    "/",
    response_model=CartReadSchema,
    status_code=status.HTTP_200_OK,
    summary="Get the user's cart contents",
)
async def get_user_cart_route(
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    cart_service: Annotated[CartService, Depends(get_cart_service)],
):
    try:
        cart = await cart_service.get_user_cart(current_user_id)
        return cart
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


@router.delete(
    "/",
    response_model=CartReadSchema,
    status_code=status.HTTP_200_OK,
    summary="Clear all items from the user's cart",
)
async def clear_user_cart_route(
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    cart_service: Annotated[CartService, Depends(get_cart_service)],
):
    try:
        cart = await cart_service.clear_user_cart(current_user_id)
        return cart
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


@router.post(
    "/checkout/",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Proceed to checkout for the user's cart",
)
async def checkout_cart_route(
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    cart_service: Annotated[CartService, Depends(get_cart_service)],
):
    try:
        checkout_result = await cart_service.checkout_cart(current_user_id)
        return checkout_result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")
