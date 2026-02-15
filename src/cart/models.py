import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import Base

if TYPE_CHECKING:
    from src.accounts.models import UserDB
    from src.movies.models import MovieDB


class CartDB(Base):
    """
    Represents a user's shopping cart.

    This model acts as a persistent container for movies that a user intends to purchase.
    It implements a one-to-one relationship with the User model, ensuring that each
    user has exactly one active cart instance.

    Attributes:
        id (int): Unique identifier for the cart.
        user_id (int): Foreign key referencing the owner of the cart.
            Configured with `unique=True` to enforce the one-to-one relationship.
        user (UserDB): Relationship to the User model.
        items (list[CartItemDB]): A collection of items currently in the cart.
            Configured with `cascade="all, delete-orphan"`, meaning that if the
            cart is deleted, all its items are automatically removed from the database.
    """

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
    """
    Represents a single movie item within a shopping cart.

    This model serves as an association table between `CartDB` and `MovieDB`,
    containing metadata about when the item was added.

    Constraints:
        unique_cart_movie: Ensures that a specific movie can verify appear only once
        in a specific cart (prevents duplicate entries for the same product).

    Attributes:
        id (int): Unique identifier for the cart item.
        cart_id (int): Foreign key referencing the parent cart.
        movie_id (int): Foreign key referencing the movie added.
        added_at (datetime): Timestamp of when the item was added to the cart.
            Defaults to the current server time.
        cart (CartDB): Relationship to the parent Cart model.
        movie (MovieDB): Relationship to the Movie model. Configured with `lazy="joined"`
            to optimize performance by fetching movie details in the same SQL query.
    """

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
    movie: Mapped["MovieDB"] = relationship(lazy="joined", back_populates="cart_items")
