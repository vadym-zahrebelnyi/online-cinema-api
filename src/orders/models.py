"""
Module: orders.models

This module contains the SQLAlchemy ORM models for managing orders
in the online cinema system. It defines the database tables, relationships,
and enumerations related to orders, order items, and their statuses.

Classes:
    - OrderStatusEnum: Enumeration of possible order statuses.
    - OrderDB: Represents a user's order with items and payments.
    - OrderItemDB: Represents individual items (movies) within an order.

Relationships:
    - OrderDB -> UserDB: Many-to-One (an order belongs to a user)
    - OrderDB -> OrderItemDB: One-to-Many (an order has multiple items)
    - OrderDB -> PaymentDB: One-to-Many (an order can have multiple payments)
    - OrderItemDB -> MovieDB: Many-to-One (an item is associated with a movie)
    - OrderItemDB -> PaymentItemDB: One-to-Many (an item can have multiple payment records)
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import Base

if TYPE_CHECKING:
    from src.payments.models import PaymentItemDB


class OrderStatusEnum(str, Enum):
    """
    Enum for tracking the status of an order.

    Attributes:
        PENDING: Order is created but not yet paid.
        PAID: Order has been successfully paid.
        CANCELLED: Order was cancelled.
    """
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class OrderDB(Base):
    """
    Database model representing a user's order.

    Attributes:
        id (int): Primary key of the order.
        user_id (int): Foreign key to the user who placed the order.
        created_at (datetime): Timestamp when the order was created.
        status (OrderStatusEnum): Current status of the order.
        total_amount (Decimal): Total amount for the order.

    Relationships:
        user (UserDB): The user who owns this order.
        items (list[OrderItemDB]): The items (movies) included in the order.
        payments (list[PaymentDB]): Payments associated with this order.
    """
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    status: Mapped[OrderStatusEnum] = mapped_column(
        SQLAlchemyEnum(OrderStatusEnum),
        default=OrderStatusEnum.PENDING,
        nullable=False,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    user = relationship("UserDB", back_populates="orders")

    items = relationship(
        "OrderItemDB",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    payments = relationship("PaymentDB", back_populates="order")


class OrderItemDB(Base):
    """
    Database model representing an individual item (movie) within an order.

    Attributes:
        id (int): Primary key of the order item.
        order_id (int): Foreign key to the associated order.
        movie_id (int): Foreign key to the movie included in the order.
        price_at_order (Decimal): Price of the movie at the time of order.

    Relationships:
        order (OrderDB): The parent order of this item.
        movie (MovieDB): The movie associated with this item.
        payment_items (list[PaymentItemDB]): Payment records for this item.

    Constraints:
        UniqueConstraint(order_id, movie_id): Prevents adding the same movie
        multiple times to the same order.
    """
    __tablename__ = "order_items"

    __table_args__ = (UniqueConstraint("order_id", "movie_id", name="uix_order_movie"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    price_at_order: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    order = relationship("OrderDB", back_populates="items")

    movie = relationship("MovieDB", lazy="joined")
    payment_items: Mapped[list["PaymentItemDB"]] = relationship(
        back_populates="order_item",
        cascade="all, delete-orphan",
    )
