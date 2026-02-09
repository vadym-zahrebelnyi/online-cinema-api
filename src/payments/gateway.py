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
    """
    Concrete implementation of the BasePaymentGateway interface using Stripe.

    This class handles direct interactions with the Stripe API, including
    session creation, webhook signature validation, and refund processing.
    It encapsulates Stripe-specific error handling, converting external
    library exceptions into internal domain exceptions.

    Attributes:
        stripe.api_key: The secret key used to authenticate with Stripe.
    """
    async def create_checkout_session(
        self, session_data: PaymentGatewayCreateSchema
    ) -> PaymentGatewayResponseSchema:
        """
        Initialize a new Stripe Checkout Session for a customer order.

        This method constructs the payment payload, converts currency amounts
        to the smallest currency unit (e.g., cents), and calls the Stripe API
        to generate a payment link.

        Args:
            session_data (PaymentGatewayCreateSchema): Validated data required
                to create a session, including amount, currency, order ID,
                and user details.

        Returns:
            PaymentGatewayResponseSchema: An object containing the payment
                page URL and the unique session ID.

        Raises:
            PaymentValidationError: If the provided data is invalid according
                to Stripe (e.g., negative amount, invalid currency).
            PaymentConfigurationError: If API authentication fails (e.g.,
                bad API key).
            PaymentConnectionError: If there are network issues or rate limits
                are exceeded.
            PaymentError: For any other unhandled Stripe errors or internal
                system failures.
        """
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
        """
        Verify the authenticity of a webhook request from Stripe.

        This method checks the cryptographic signature of the incoming
        payload to ensure it was sent by Stripe and has not been tampered with.

        Args:
            payload (bytes): The raw body of the HTTP request.
            signature (str): The value of the 'Stripe-Signature' header.

        Returns:
            dict: The constructed Stripe event object if validation is successful.

        Raises:
            PaymentWebhookError: If the payload is invalid, the signature
                verification fails, or any other processing error occurs.
        """
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

    async def refund_payment(self, payment_intent_id: str) -> dict:
        """
        Process a full refund for a specific payment intent.

        Args:
            payment_intent_id (str): The unique identifier of the payment
                intent to be refunded (typically stored as external_payment_id).

        Returns:
            dict: The Stripe refund object containing status and details.

        Raises:
            PaymentValidationError: If the refund request is invalid (e.g.,
                payment already refunded or ID not found).
            PaymentError: For general Stripe errors or internal failures
                during the refund process.
        """
        try:
            refund = await stripe.Refund.create_async(payment_intent=payment_intent_id)
            return refund

        except InvalidRequestError as e:
            raise PaymentValidationError(f"Refund failed: {e.user_message}") from e

        except StripeError as e:
            raise PaymentError(f"Stripe refund error: {e.user_message}") from e

        except Exception as e:
            raise PaymentError("Internal error during refund") from e
