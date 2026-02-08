from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi_filter import FilterDepends
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.dependencies import (
    allow_admin,
    allow_moderator,
    get_current_user,
)
from src.accounts.models import UserDB
from src.core.database import get_db

from .crud import payment_crud
from .exceptions import (
    PaymentConnectionError,
    PaymentError,
    PaymentValidationError,
    PaymentWebhookError,
)
from .filters import PaymentFilter
from .schemas import (
    PaymentCheckoutRequestSchema,
    PaymentDetailSchema,
    PaymentGatewayResponseSchema,
    PaymentResponseSchema,
)
from .services import PaymentService, get_payment_service

router = APIRouter()


@router.post("/checkout", response_model=PaymentGatewayResponseSchema)
async def create_checkout_session(
    checkout_data: PaymentCheckoutRequestSchema,
    current_user: Annotated[UserDB, Depends(get_current_user)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
):
    try:
        return await service.create_checkout_session(
            current_user, checkout_data.order_id
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except PaymentValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except PaymentConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment provider unavailable",
        )

    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    service: Annotated[PaymentService, Depends(get_payment_service)],
    stripe_signature: Annotated[str | None, Header()] = None,
):
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No signature header"
        )

    payload = await request.body()

    try:
        return await service.process_webhook(payload, stripe_signature)
    except PaymentWebhookError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook internal error",
        )


@router.post("/{payment_id}/cancel", response_model=PaymentResponseSchema)
async def cancel_pending_payment(
    payment_id: int,
    current_user: Annotated[UserDB, Depends(get_current_user)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
):
    try:
        return await service.cancel_payment(current_user, payment_id)

    except ValueError as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in str(e).lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(e))

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{payment_id}/refund/request", response_model=PaymentResponseSchema)
async def request_refund(
    payment_id: int,
    current_user: Annotated[UserDB, Depends(get_current_user)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
):
    try:
        return await service.request_refund(current_user, payment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{payment_id}/refund/approve", response_model=PaymentResponseSchema)
async def approve_refund(
    payment_id: int,
    current_user: Annotated[UserDB, Depends(allow_admin)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
):
    try:
        return await service.approve_refund(current_user, payment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/history/my", response_model=list[PaymentResponseSchema])
async def get_my_payments(
    current_user: Annotated[UserDB, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await payment_crud.get_user_payments(db, user_id=current_user.id)


@router.get("/{payment_id}", response_model=PaymentDetailSchema)
async def get_payment_details(
    payment_id: int,
    _: Annotated[UserDB, Depends(allow_moderator)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    payment = await payment_crud.get_payment_details(db, payment_id)

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment


@router.get("/history/all", response_model=list[PaymentResponseSchema])
async def get_all_payments_admin(
    filters: Annotated[PaymentFilter, FilterDepends(PaymentFilter)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[UserDB, Depends(allow_moderator)],
):
    return await payment_crud.get_all_payments_filtered(db, filters)
