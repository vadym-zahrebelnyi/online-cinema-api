import stripe
from stripe import (
    APIConnectionError,
    AuthenticationError,
    InvalidRequestError,
    RateLimitError,
    SignatureVerificationError,
    StripeError,
)

from src.core.settings import settings

from .exceptions import (
    PaymentConfigurationError,
    PaymentConnectionError,
    PaymentError,
    PaymentValidationError,
    PaymentWebhookError,
)
from .interfaces import BasePaymentGateway
from .schemas import PaymentGatewayCreateSchema, PaymentGatewayResponseSchema

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeGateway(BasePaymentGateway):
    async def create_checkout_session(
        self, session_data: PaymentGatewayCreateSchema
    ) -> PaymentGatewayResponseSchema:
        try:
            unit_amount = int(session_data.amount * 100)

            session = await stripe.checkout.Session.create_async(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": session_data.currency,
                            "product_data": {
                                "name": f"Order #{session_data.order_id}",
                            },
                            "unit_amount": unit_amount,
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=f"{settings.DOMAIN_NAME}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.DOMAIN_NAME}/payment/cancel",
                client_reference_id=str(session_data.order_id),
                metadata={
                    "order_id": str(session_data.order_id),
                    "user_id": str(session_data.user_id),
                    "email": session_data.email or "",
                },
                customer_email=session_data.email if session_data.email else None,
            )

            return PaymentGatewayResponseSchema(url=session.url, session_id=session.id)

        except InvalidRequestError as e:
            raise PaymentValidationError(
                f"Invalid payment data: {e.user_message}"
            ) from e

        except AuthenticationError as e:
            raise PaymentConfigurationError(
                "Payment provider authentication failed."
            ) from e

        except RateLimitError as e:
            raise PaymentConnectionError(
                "Payment provider is busy. Please try again later."
            ) from e

        except APIConnectionError as e:
            raise PaymentConnectionError(
                "Could not connect to payment provider."
            ) from e

        except StripeError as e:
            raise PaymentError(
                f"Payment provider error: {e.user_message or 'Unknown error'}"
            ) from e

        except Exception as e:
            raise PaymentError("Internal error during payment initialization") from e

    async def validate_webhook(self, payload: bytes, signature: str) -> dict:
        try:
            return stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )

        except ValueError as e:
            raise PaymentWebhookError("Invalid payload body") from e
        except SignatureVerificationError as e:
            raise PaymentWebhookError("Invalid webhook signature") from e
        except Exception as e:
            raise PaymentWebhookError(f"Webhook processing failed: {str(e)}") from e
