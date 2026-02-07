from abc import ABC, abstractmethod
from typing import Any, Dict

from .schemas import PaymentGatewayCreateSchema, PaymentGatewayResponseSchema


class BasePaymentGateway(ABC):
    """
    Abstract Base Class (Interface) for payment processing gateways.

    This class defines the contract that any payment provider implementation
    (Stripe, PayPal, etc.) must adhere to. It ensures that the core application
    business logic remains agnostic of the specific payment provider details.
    """

    @abstractmethod
    async def create_checkout_session(
        self, session_data: PaymentGatewayCreateSchema
    ) -> PaymentGatewayResponseSchema:
        """
        Initiates a payment session on the external provider's side.

        This method should handle the communication with the payment gateway API
        to generate a secure link where the user can enter their payment details.

        Args:
            session_data (PaymentGatewayCreateSchema): Validated DTO containing
                order details, user info, and amount strictly typed.

        Returns:
            PaymentGatewayResponseSchema: A schema containing the redirect URL
                and the external session ID.

        Raises:
            Exception: Implementations should raise specific exceptions if
                the external API call fails (e.g., connection timeout, auth error).
        """
        pass

    @abstractmethod
    async def validate_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Validates the authenticity of a webhook request from the payment provider.

        Security is critical here. This method must verify the cryptographic
        signature header against the raw payload to ensure the request truly
        originated from the payment provider.

        Args:
            payload (bytes): The raw body of the webhook request (do not decode to string).
            signature (str): The signature header provided by the payment gateway
                (e.g., 'Stripe-Signature').

        Returns:
            Dict[str, Any]: The parsed and validated event data (e.g., event type, object).

        Raises:
            ValueError: If the payload is invalid or the signature verification fails.
        """
        pass

    @abstractmethod
    async def refund_payment(self, payment_intent_id: str) -> dict:
        """Process a refund via the payment provider."""
        pass
