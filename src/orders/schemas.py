from datetime import datetime
from decimal import Decimal
from typing import List, Annotated

from pydantic import BaseModel, ConfigDict, Field, condecimal

from .models import OrderStatusEnum


class OrderItemMovieSchema(BaseModel):
    """Movie information within an order"""

    title: str = Field(alias="name")
    price_at_order: Annotated[Decimal, Field(max_digits=10, decimal_places=2)]

    model_config = ConfigDict(from_attributes=True)


class OrderItemReadSchema(BaseModel):
    """Schema for reading a single order item"""

    id: int
    movie: OrderItemMovieSchema

    model_config = ConfigDict(from_attributes=True)


class OrderItemCreateSchema(BaseModel):
    """Schema for creating a single order item"""

    movie_id: int
    price_at_order: Annotated[Decimal, Field(max_digits=10, decimal_places=2)]

    model_config = ConfigDict(from_attributes=True)


class OrderBaseSchema(BaseModel):
    """Base schema for an order"""

    user_id: int
    status: OrderStatusEnum
    total_amount: Annotated[Decimal, Field(max_digits=10, decimal_places=2)]

    model_config = ConfigDict(from_attributes=True)


class OrderCreateSchema(OrderBaseSchema):
    """Schema for creating an order with items"""

    items: List[OrderItemCreateSchema]


class OrderReadSchema(OrderBaseSchema):
    """Schema for reading an order, including items"""

    id: int
    created_at: datetime
    items: List[OrderItemReadSchema]

    model_config = ConfigDict(from_attributes=True)
