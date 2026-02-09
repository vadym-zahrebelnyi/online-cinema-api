"""
Module: orders.schemas

This module defines Pydantic schemas for serializing and validating order data
in the online cinema system. These schemas are used for API responses and
data transfer between the backend and frontend.

Schemas:
    - OrderItemMovieSchema: Represents movie information within an order item.
    - OrderItemReadSchema: Represents a single order item including movie info and price.
    - OrderReadSchema: Represents an entire order with its metadata and list of items.
    - CancelSchema: Represents a response message when cancelling an order.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, List

from pydantic import BaseModel, ConfigDict, Field

from .models import OrderStatusEnum


class OrderItemMovieSchema(BaseModel):
    """
    Movie information within an order.

    Attributes:
        name (str): Name of the movie.
    """

    name: str
    model_config = ConfigDict(from_attributes=True)


class OrderItemReadSchema(BaseModel):
    """
    Schema for reading a single order item.

    Attributes:
        movie (OrderItemMovieSchema): Information about the movie.
        price_at_order (Decimal): Price of the movie at the time of order.
    """

    movie: OrderItemMovieSchema
    price_at_order: Decimal
    model_config = ConfigDict(from_attributes=True)


class OrderReadSchema(BaseModel):
    """
    Schema for reading an entire order, including its items.

    Attributes:
        id (int): ID of the order.
        created_at (datetime): Timestamp when the order was created.
        total_amount (Decimal): Total amount of the order (max 10 digits, 2 decimals).
        status (OrderStatusEnum): Current status of the order (e.g., pending, paid, cancelled).
        items (List[OrderItemReadSchema]): List of items included in the order.
    """

    id: int
    user_id: int
    created_at: datetime
    total_amount: Annotated[Decimal, Field(max_digits=10, decimal_places=2)]
    status: OrderStatusEnum
    items: List[OrderItemReadSchema]

    model_config = ConfigDict(from_attributes=True)


class CancelSchema(BaseModel):
    """
    Schema for cancelling a single order.

    Attributes:
        message (str): Confirmation message for the cancellation action.
    """

    message: str
