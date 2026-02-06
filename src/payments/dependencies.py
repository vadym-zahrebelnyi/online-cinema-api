from .interfaces import BasePaymentGateway
from .services import StripeGateway


def get_payment_gateway() -> BasePaymentGateway:
    return StripeGateway()
