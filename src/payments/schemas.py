from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

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


class PaymentSearchSchema(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None

    user_id: Annotated[int | None, Field(gt=0, description="Filter by user ID")] = None
    status: Annotated[
        PaymentStatusEnum | None, Field(description="Filter by payment status")
    ] = None


class PaymentItemResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    movie_title: str
    price_at_payment: Annotated[Decimal, Field(decimal_places=2)]


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
