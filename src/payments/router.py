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
from src.core import get_db

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


@router.post(
    "/checkout",
    response_model=PaymentGatewayResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Create a new payment session",
    responses={
        400: {"description": "Invalid order state or payment data validation failed"},
        403: {"description": "User is not authorized to pay for this order"},
        503: {"description": "Payment provider (Stripe) is currently unavailable"},
    },
)
async def create_checkout_session(
    checkout_data: PaymentCheckoutRequestSchema,
    current_user: Annotated[UserDB, Depends(get_current_user)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
):
    """
    Initialize a checkout session with the external payment gateway.

    This endpoint:
    1. Validates that the order exists and belongs to the current user.
    2. Checks if the order is already paid.
    3. Creates a local payment record in PENDING status.
    4. Contacts Stripe to generate a secure payment URL.

    - order_id: The ID of the order to be paid.
    """
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


@router.post(
    "/{payment_id}/cancel",
    response_model=PaymentResponseSchema,
    summary="Cancel a pending payment",
    responses={
        400: {"description": "Payment cannot be canceled (already processed)"},
        403: {"description": "Payment belongs to another user"},
        404: {"description": "Payment not found"},
    },
)
async def cancel_pending_payment(
    payment_id: int,
    current_user: Annotated[UserDB, Depends(get_current_user)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
):
    """
    Cancel a payment that is currently in PENDING state.

    This action is irreversible. If the payment was already successful,
    this endpoint will return a 400 error (use refund instead).
    """
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


@router.post(
    "/{payment_id}/refund/request",
    response_model=PaymentResponseSchema,
    summary="Request a refund for a completed payment",
    responses={
        400: {"description": "Payment is not successful or eligible for refund"},
        403: {"description": "Payment belongs to another user"},
        404: {"description": "Payment not found"},
    },
)
async def request_refund(
    payment_id: int,
    current_user: Annotated[UserDB, Depends(get_current_user)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
):
    """
    Submit a request to refund a successful payment.

    This changes the payment status to REFUND_REQUESTED. The funds are not
    returned immediately; an administrator must approve the request via the
    admin API.
    """
    try:
        return await service.request_refund(current_user, payment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post(
    "/{payment_id}/refund/approve",
    response_model=PaymentResponseSchema,
    summary="Approve refund (Admin only)",
    responses={
        400: {"description": "Payment not eligible for refund (e.g., missing ID)"},
        403: {"description": "Not authorized (Admin access required)"},
        502: {"description": "Upstream error from Stripe during refund processing"},
    },
)
async def approve_refund(
    payment_id: int,
    current_user: Annotated[UserDB, Depends(allow_admin)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
):
    """
    Approve and execute a refund transaction.

    **Requires Administrator privileges.**

    This endpoint triggers the actual money transfer via Stripe API and
    updates the local system state to REFUNDED.
    """
    try:
        return await service.approve_refund(current_user, payment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get(
    "/history/my",
    response_model=list[PaymentResponseSchema],
    summary="Get current user's payment history",
)
async def get_my_payments(
    current_user: Annotated[UserDB, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Retrieve a list of all payments made by the authenticated user.
    Results are ordered by creation date (newest first).
    """
    return await payment_crud.get_user_payments(db, user_id=current_user.id)


@router.get(
    "/{payment_id}",
    response_model=PaymentDetailSchema,
    summary="Get payment details (Staff only)",
    responses={
        404: {"description": "Payment not found"},
        403: {"description": "Not authorized (Moderator/Admin access required)"},
    },
)
async def get_payment_details(
    payment_id: int,
    _: Annotated[UserDB, Depends(allow_moderator)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Retrieve detailed information for a specific payment.

    **Requires Moderator or Admin privileges.**

    Returns comprehensive data including:
    - Payment status and amounts
    - User details (payer)
    - Full order breakdown (items, movie titles)
    - External gateway IDs
    """
    payment = await payment_crud.get_payment_details(db, payment_id)

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment


@router.get(
    "/history/all",
    response_model=list[PaymentResponseSchema],
    summary="Get all payments (Staff only)",
    responses={
        403: {"description": "Not authorized (Moderator/Admin access required)"},
    },
)
async def get_all_payments_admin(
    filters: Annotated[PaymentFilter, FilterDepends(PaymentFilter)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[UserDB, Depends(allow_moderator)],
):
    """
    Retrieve a filtered list of all system payments.

    **Requires Moderator or Admin privileges.**

    Supports filtering by:
    - **user_id**: Filter by specific user
    - **status**: Filter by payment status (pending, successful, etc.)
    - **created_at**: Date range filtering
    """
    return await payment_crud.get_all_payments_filtered(db, filters)
