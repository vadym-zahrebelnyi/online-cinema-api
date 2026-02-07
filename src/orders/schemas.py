from datetime import datetime
from decimal import Decimal
from typing import Annotated, List

from pydantic import BaseModel, ConfigDict, Field

from .models import OrderStatusEnum


class OrderItemMovieSchema(BaseModel):
    """Movie information within an order"""

    name: str
    model_config = ConfigDict(from_attributes=True)


class OrderItemReadSchema(BaseModel):
    """Schema for reading a single order item"""

    movie: OrderItemMovieSchema
    price_at_order: Decimal
    model_config = ConfigDict(from_attributes=True)


class OrderItemCreateSchema(BaseModel):
    """Schema for creating a single order item"""

    movie_id: int
    price_at_order: Annotated[Decimal, Field(max_digits=10, decimal_places=2)]

    model_config = ConfigDict(from_attributes=True)


class OrderBaseSchema(BaseModel):
    """Base schema for an order"""

    id: int
    created_at: datetime
    total_amount: Annotated[Decimal, Field(max_digits=10, decimal_places=2)]
    status: OrderStatusEnum


class OrderCreateSchema(OrderBaseSchema):
    """Schema for creating an order with items"""

    items: List[OrderItemCreateSchema]


class OrderReadSchema(BaseModel):
    """Schema for reading an order, including items"""

    id: int
    created_at: datetime
    total_amount: Annotated[Decimal, Field(max_digits=10, decimal_places=2)]
    status: OrderStatusEnum
    items: List[OrderItemReadSchema]

    model_config = ConfigDict(from_attributes=True)
