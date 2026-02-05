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

from database import Base

if TYPE_CHECKING:
    from src.accounts.models import UserDB
    from src.orders.models import OrderDB, OrderItemDB


class PaymentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class PaymentDB(Base):
    __tablename__ = "payments"

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

    __table_args__ = (
        CheckConstraint("amount >= 0", name="check_payment_amount_positive"),
        Index("idx_user_payments_history", "user_id", "created_at"),
    )

    __mapper_args__ = {"order_by": func.desc("created_at")}

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, status={self.status}, amount={self.amount})>"


class PaymentItemDB(Base):
    __tablename__ = "payment_items"

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

    __table_args__ = (
        UniqueConstraint(
            "payment_id", "order_item_id", name="uq_payment_item_per_order_item"
        ),
        CheckConstraint("price_at_payment >= 0", name="check_price_positive"),
    )

    def __repr__(self) -> str:
        return f"<PaymentItem(id={self.id}, price={self.price_at_payment})>"
