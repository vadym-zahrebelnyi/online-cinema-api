import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import Base

if TYPE_CHECKING:
    from src.accounts.models import UserDB
    from src.movies.models import MovieDB


class CartDB(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    user: Mapped["UserDB"] = relationship(back_populates="cart")
    items: Mapped[list["CartItemDB"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )


class CartItemDB(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "movie_id", name="unique_cart_movie"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    added_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    cart: Mapped["CartDB"] = relationship(back_populates="items")
    movie: Mapped["MovieDB"] = relationship(lazy="joined")
