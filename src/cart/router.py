from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.accounts.dependencies import allow_admin, get_current_user_optional
from src.accounts.models import UserDB
from src.cart.dependencies import get_anon_cart_id, get_cart_service
from src.cart.exceptions import (
    MovieAlreadyInCartError,
    MovieAlreadyOwnedError,
)
from src.cart.schemas import CartReadSchema
from src.cart.services import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("/", response_model=CartReadSchema)
async def get_my_cart(
    user: Annotated[UserDB | None, Depends(get_current_user_optional)],
    anon_id: Annotated[str, Depends(get_anon_cart_id)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    user_id = user.id if user else None
    return await service.get_cart(user_id, anon_id)


@router.post("/items/{movie_id}", status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    movie_id: int,
    user: Annotated[UserDB | None, Depends(get_current_user_optional)],
    anon_id: Annotated[str, Depends(get_anon_cart_id)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
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
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"status": "ok", "message": "Movie added to cart"}


@router.delete("/items/{movie_id}", status_code=status.HTTP_200_OK)
async def remove_from_cart(
    movie_id: int,
    user: Annotated[UserDB | None, Depends(get_current_user_optional)],
    anon_id: Annotated[str, Depends(get_anon_cart_id)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    user_id = user.id if user else None
    await service.remove_item(movie_id, user_id, anon_id)
    return {"status": "ok", "message": "Item removed from cart"}


@router.delete("/", status_code=status.HTTP_200_OK)
async def clear_cart(
    user: Annotated[UserDB | None, Depends(get_current_user_optional)],
    anon_id: Annotated[str, Depends(get_anon_cart_id)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    user_id = user.id if user else None
    await service.clear_cart(user_id, anon_id)
    return {"status": "ok", "message": "Cart cleared"}


@router.get(
    "/users/{target_user_id}",
    response_model=CartReadSchema,
    dependencies=[Depends(allow_admin)],
)
async def get_user_cart_admin(
    target_user_id: int,
    service: Annotated[CartService, Depends(get_cart_service)],
):
    return await service.get_cart(user_id=target_user_id, anon_id=None)
