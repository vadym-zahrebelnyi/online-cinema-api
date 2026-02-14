from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.accounts.dependencies import allow_admin, get_current_user_optional
from src.accounts.models import UserDB
from src.cart.dependencies import get_anon_cart_id, get_cart_service
from src.cart.exceptions import (
    MovieAlreadyInCartError,
    MovieAlreadyOwnedError,
    MovieNotFoundError,
)
from src.cart.schemas import CartReadSchema
from src.cart.services import CartService

router = APIRouter()


@router.get(
    "/",
    response_model=CartReadSchema,
    summary="Get current cart state",
    responses={
        200: {"description": "Current cart details (items, total price)"},
    },
)
async def get_my_cart(
    user: Annotated[UserDB | None, Depends(get_current_user_optional)],
    anon_id: Annotated[str, Depends(get_anon_cart_id)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    """
    Retrieve the shopping cart for the current user.

    Handles both authenticated and anonymous users:
    - **Authenticated**: Returns the persistent cart from the database.
    - **Anonymous**: Returns the temporary cart from Redis (identified by cookie).
    """
    user_id = user.id if user else None
    return await service.get_cart(user_id, anon_id)


@router.post(
    "/items/{movie_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Add movie to cart",
    responses={
        201: {"description": "Item successfully added"},
        400: {"description": "Invalid movie ID"},
        409: {"description": "Movie already in cart or already owned by user"},
    },
)
async def add_to_cart(
    movie_id: int,
    user: Annotated[UserDB | None, Depends(get_current_user_optional)],
    anon_id: Annotated[str, Depends(get_anon_cart_id)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    """
    Add a specific movie to the user's cart.

    Enforces business rules:
    - User cannot add a movie they already own (purchased previously).
    - User cannot add the same movie twice to the cart.
    - Validates that the movie ID exists.
    """
    user_id = user.id if user else None
    try:
        await service.add_movie(movie_id, user_id, anon_id)
    except MovieAlreadyOwnedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already purchased this movie.",
        )
    except MovieAlreadyInCartError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie is already in your cart.",
        )
    except MovieNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

    return {"status": "ok", "message": "Movie added to cart"}


@router.delete(
    "/items/{movie_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove item from cart",
    responses={
        200: {"description": "Item removed successfully"},
    },
)
async def remove_from_cart(
    movie_id: int,
    user: Annotated[UserDB | None, Depends(get_current_user_optional)],
    anon_id: Annotated[str, Depends(get_anon_cart_id)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    """
    Remove a specific movie from the cart.

    If the item is not in the cart, the operation is idempotent (returns 200 OK without error).
    """
    user_id = user.id if user else None
    await service.remove_item(movie_id, user_id, anon_id)
    return {"status": "ok", "message": "Item removed from cart"}


@router.delete(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Clear entire cart",
    responses={
        200: {"description": "Cart cleared successfully"},
    },
)
async def clear_cart(
    user: Annotated[UserDB | None, Depends(get_current_user_optional)],
    anon_id: Annotated[str, Depends(get_anon_cart_id)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    """
    Empty the shopping cart completely.

    Removes all items associated with the current user (DB or Redis).
    """
    user_id = user.id if user else None
    await service.clear_cart(user_id, anon_id)
    return {"status": "ok", "message": "Cart cleared"}


@router.get(
    "/users/{target_user_id}",
    response_model=CartReadSchema,
    dependencies=[Depends(allow_admin)],
    summary="Get user cart (Admin)",
    responses={
        403: {"description": "Not authorized (Admin only)"},
    },
)
async def get_user_cart_admin(
    target_user_id: int,
    service: Annotated[CartService, Depends(get_cart_service)],
):
    """
    Retrieve the cart of a specific user.

    **Requires Administrator privileges.**
    Useful for customer support to inspect a user's current shopping session.
    """
    return await service.get_cart(user_id=target_user_id, anon_id=None)
