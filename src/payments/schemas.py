from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from payments.models import PaymentStatusEnum


class PaymentGatewayCreateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(default="usd", pattern=r"^[a-z]{3}$")
    email: Optional[EmailStr] = None

    order_id: int = Field(gt=0)
    user_id: int = Field(gt=0)


class PaymentGatewayResponseSchema(BaseModel):
    url: HttpUrl
    session_id: str


class PaymentCheckoutRequestSchema(BaseModel):
    order_id: int = Field(gt=0)


class PaymentSearchSchema(BaseModel):
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    user_id: Optional[int] = Field(None, gt=0, description="Filter by user ID")
    status: Optional[PaymentStatusEnum] = Field(
        None, description="Filter by payment status"
    )


class PaymentItemResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    movie_title: str
    price_at_payment: Decimal = Field(decimal_places=2)


class PaymentResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal = Field(decimal_places=2)
    status: PaymentStatusEnum
    created_at: datetime
    items: list[PaymentItemResponseSchema] = Field(
        default_factory=list, validation_alias="payment_items"
    )
