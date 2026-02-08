from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from src.orders.models import OrderStatusEnum

from .models import PaymentStatusEnum


class PaymentGatewayCreateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    amount: Annotated[Decimal, Field(gt=0, decimal_places=2)]
    currency: Annotated[str, Field(pattern=r"^[a-z]{3}$")] = "usd"
    email: EmailStr | None = None

    order_id: Annotated[int, Field(gt=0)]
    user_id: Annotated[int, Field(gt=0)]


class PaymentGatewayResponseSchema(BaseModel):
    url: HttpUrl
    session_id: str


class PaymentCheckoutRequestSchema(BaseModel):
    order_id: Annotated[int, Field(gt=0)]


class PaymentUserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str | None = None
    last_name: str | None = None


class PaymentOrderSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatusEnum
    total_amount: Decimal


class PaymentItemResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    movie_title: str
    price_at_payment: Annotated[Decimal, Field(decimal_places=2)]
    movie_title: str


class PaymentResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Annotated[Decimal, Field(decimal_places=2)]
    status: PaymentStatusEnum
    created_at: datetime
    items: Annotated[
        list[PaymentItemResponseSchema],
        Field(default_factory=list, validation_alias="payment_items"),
    ]


class PaymentDetailSchema(PaymentResponseSchema):
    user: PaymentUserSchema
    order: PaymentOrderSchema
    external_payment_id: str | None = None
