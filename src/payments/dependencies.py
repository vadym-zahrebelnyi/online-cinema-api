from typing import Annotated

from fastapi import Depends

from .gateway import StripeGateway
from .interfaces import BasePaymentGateway


def get_payment_gateway() -> BasePaymentGateway:
    return StripeGateway()


PaymentGatewayDep = Annotated[BasePaymentGateway, Depends(get_payment_gateway)]
