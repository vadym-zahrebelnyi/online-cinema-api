import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    DECIMAL,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.accounts.models import UserDB
    from src.orders.models import OrderDB, OrderItemDB


class PaymentStatusEnum(str, enum.Enum):
    """
    Enumeration representing the lifecycle states of a payment transaction.

    Used to track the progression of a payment from initialization to finalization
    or reversal.

    Attributes:
        PENDING: The payment intent is created but not yet processed by the gateway.
        SUCCESSFUL: The transaction was successfully confirmed by the payment provider.
        CANCELED: The transaction was aborted by the user or the system before completion.
        REFUNDED: The funds have been returned to the user (full refund).
        REFUND_REQUESTED: The user has requested a refund, pending administrative approval.
    """

    PENDING = "pending"
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    REFUND_REQUESTED = "refund_requested"


class PaymentDB(Base):
    """
    Represents a financial transaction record within the system.

    This model serves as the aggregate root for payment operations, storing
    metadata about the transaction status, amount, and integration with
    external payment gateways (e.g., Stripe).

    Attributes:
        id (int): Unique identifier for the payment record.
        amount (Decimal): The total monetary value of the transaction. Must be non-negative.
        status (PaymentStatusEnum): The current state of the payment (e.g., pending, successful).
        created_at (datetime): The UTC timestamp when the payment record was initialized.
        user_id (int): Foreign key referencing the user who initiated the payment.
        order_id (int): Foreign key referencing the order associated with this payment.
        external_payment_id (str, optional): The unique identifier returned by the payment
            gateway (e.g., Stripe PaymentIntent ID). Used for reconciliation and webhooks.
        user (UserDB): Relationship to the User model.
        order (OrderDB): Relationship to the Order model.
        payment_items (List[PaymentItemDB]): Collection of individual line items included
            in this payment.
    """

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="check_payment_amount_positive"),
        Index("idx_user_payments_history", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    status: Mapped[PaymentStatusEnum] = mapped_column(
        SQLEnum(PaymentStatusEnum),
        default=PaymentStatusEnum.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False, index=True
    )

    external_payment_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    user: Mapped["UserDB"] = relationship("UserDB", back_populates="payments")
    order: Mapped["OrderDB"] = relationship("OrderDB", back_populates="payments")

    payment_items: Mapped[List["PaymentItemDB"]] = relationship(
        "PaymentItemDB",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """
        Return a string representation of the Payment instance.
        """
        return f"<Payment(id={self.id}, status={self.status}, amount={self.amount})>"


class PaymentItemDB(Base):
    """
    Represents a specific line item within a payment transaction.

    This model implements the 'Snapshot' pattern. It records the price of an item
    at the exact moment of purchase. This ensures historical accuracy for financial
    reporting, even if the catalog price of the movie changes later.

    Attributes:
        id (int): Unique identifier for the payment item.
        price_at_payment (Decimal): The price of the item at the moment of the transaction.
            Must be non-negative.
        payment_id (int): Foreign key referencing the parent payment transaction.
        order_item_id (int): Foreign key referencing the specific item in the order.
        payment (PaymentDB): Relationship to the parent Payment model.
        order_item (OrderItemDB): Relationship to the original OrderItem model.
    """

    __tablename__ = "payment_items"
    __table_args__ = (
        UniqueConstraint(
            "payment_id", "order_item_id", name="uq_payment_item_per_order_item"
        ),
        CheckConstraint("price_at_payment >= 0", name="check_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    price_at_payment: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)

    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False)
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id"), nullable=False
    )

    payment: Mapped["PaymentDB"] = relationship(
        "PaymentDB", back_populates="payment_items"
    )
    order_item: Mapped["OrderItemDB"] = relationship("OrderItemDB")

    @property
    def movie_title(self) -> str:
        """
        Retrieve the name of the movie associated with this payment item.

        Returns:
            str: The name of the movie if the relationship exists, otherwise 'Unknown Movie'.
        """
        if self.order_item and self.order_item.movie:
            return self.order_item.movie.name
        return "Unknown Movie"

    def __repr__(self) -> str:
        """
        Return a string representation of the PaymentItem instance.
        """
        return f"<PaymentItem(id={self.id}, price={self.price_at_payment})>"
