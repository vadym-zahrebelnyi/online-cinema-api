from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import UserDB
from src.core.database import get_db
from src.orders import crud as order_crud
from src.orders.models import OrderStatusEnum
from src.payments.crud import payment_crud
from src.payments.dependencies import PaymentGatewayDep
from src.payments.models import PaymentStatusEnum
from src.payments.schemas import (
    PaymentGatewayCreateSchema,
    PaymentGatewayResponseSchema,
)
from src.payments.tasks import send_payment_confirmation_email_task


class PaymentService:
    def __init__(self, db: AsyncSession, gateway: PaymentGatewayDep):
        self.db = db
        self.gateway = gateway

    async def create_checkout_session(
        self, user: UserDB, order_id: int
    ) -> PaymentGatewayResponseSchema:
        order = await order_crud.get_order_with_items(self.db, order_id)

        if not order:
            raise ValueError("Order not found")

        if order.user_id != user.id:
            raise PermissionError("Not authorized to pay for this order")

        if order.status == OrderStatusEnum.PAID:
            raise ValueError("Order is already paid")

        payment = await payment_crud.create_payment(
            self.db, order=order, user_id=user.id
        )

        gateway_schema = PaymentGatewayCreateSchema(
            order_id=order.id,
            user_id=user.id,
            amount=payment.amount,
            currency="usd",
            email=user.email,
        )

        session_data = await self.gateway.create_checkout_session(gateway_schema)

        await payment_crud.set_external_id(self.db, payment.id, session_data.session_id)

        return session_data

    async def process_webhook(self, payload: bytes, signature: str) -> dict:
        event = await self.gateway.validate_webhook(payload, signature)
        event_type = event["type"]

        if event_type == "checkout.session.completed":
            await self._handle_checkout_completed(event["data"]["object"])

        elif event_type == "charge.refunded":
            await self._handle_refund(event["data"]["object"])

        return {"status": "ok"}

    async def cancel_payment(self, user: UserDB, payment_id: int):
        payment = await payment_crud.get_by_id(self.db, payment_id)

        if not payment:
            raise ValueError("Payment not found")

        if payment.user_id != user.id:
            raise PermissionError("Not authorized")

        if payment.status != PaymentStatusEnum.PENDING:
            raise ValueError("Cannot cancel processed payment. Use refund instead.")

        return await payment_crud.cancel_payment(self.db, payment)

    async def request_refund(self, user: UserDB, payment_id: int):
        payment = await payment_crud.get_by_id(self.db, payment_id)

        if not payment:
            raise ValueError("Payment not found")

        if payment.user_id != user.id:
            raise PermissionError("Not authorized")

        if payment.status != PaymentStatusEnum.SUCCESSFUL:
            raise ValueError("Can only request refund for successful payments")

        return await payment_crud.mark_refund_requested(self.db, payment)

    async def approve_refund(self, admin_user: UserDB, payment_id: int):
        payment = await payment_crud.get_by_id(self.db, payment_id)

        if not payment:
            raise ValueError("Payment not found")

        allowed_statuses = [
            PaymentStatusEnum.SUCCESSFUL,
            PaymentStatusEnum.REFUND_REQUESTED,
        ]
        if payment.status not in allowed_statuses:
            raise ValueError("Payment is not eligible for refund")

        if not payment.external_payment_id:
            raise ValueError("Missing external Stripe ID")

        try:
            await self.gateway.refund_payment(payment.external_payment_id)
        except Exception as e:
            raise e

        return await payment_crud.refund_payment(self.db, payment)

    async def _handle_checkout_completed(self, session_data: dict):
        session_id = session_data.get("id")
        payment_intent_id = session_data.get("payment_intent")

        payment = await payment_crud.get_by_session_id(self.db, session_id)

        if not payment:
            return

        if payment.status != PaymentStatusEnum.SUCCESSFUL:
            if payment_intent_id:
                await payment_crud.set_external_id(
                    self.db, payment.id, payment_intent_id
                )

            payment = await payment_crud.confirm_payment(self.db, payment)

            if payment.user and payment.user.email:
                send_payment_confirmation_email_task.delay(
                    email=payment.user.email,
                    amount=str(payment.amount),
                    order_id=payment.order_id,
                )

    async def _handle_refund(self, charge_data: dict):
        payment_intent_id = charge_data.get("payment_intent")
        payment = await payment_crud.get_by_session_id(self.db, payment_intent_id)

        if payment:
            await payment_crud.refund_payment(self.db, payment)


def get_payment_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    gateway: PaymentGatewayDep,
) -> PaymentService:
    return PaymentService(db, gateway)
