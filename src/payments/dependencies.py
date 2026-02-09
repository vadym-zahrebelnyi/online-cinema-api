from typing import Annotated

from fastapi import Depends

from .gateway import StripeGateway
from .interfaces import BasePaymentGateway


def get_payment_gateway() -> BasePaymentGateway:
    """
    Dependency provider for the payment gateway instance.

    This factory function returns a concrete implementation of the BasePaymentGateway
    interface. Currently configured to use the StripeGateway.

    Using this dependency allows for easy substitution of the payment provider
    (e.g., switching to PayPal or a mock gateway for testing) without modifying
    the dependent services.

    Returns:
        BasePaymentGateway: An initialized instance of the payment gateway.
    """
    return StripeGateway()

"""
Type alias for the payment gateway dependency.

Use this type hint in route handlers and services to automatically inject
the configured payment gateway.

Example:
    def create_payment(gateway: PaymentGatewayDep):
        ...
"""
PaymentGatewayDep = Annotated[BasePaymentGateway, Depends(get_payment_gateway)]
