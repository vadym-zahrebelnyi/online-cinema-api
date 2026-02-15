import uuid as uuid_pkg
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from src.cart.models import CartItemDB
    from src.orders.models import OrderItemDB

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from src.core import Base

movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

movie_stars = Table(
    "movie_stars",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("star_id", ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True),
)

movie_directors = Table(
    "movie_directors",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "director_id", ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True
    ),
)


class CertificationDB(Base):
    """Represents a movie certification (e.g., PG-13, R)."""

    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )

    movies: Mapped[List["MovieDB"]] = relationship(
        back_populates="certification",
        cascade="save-update, merge",
    )


class GenreDB(Base):
    """Represents a movie genre (e.g., Action, Drama)."""

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )

    movies: Mapped[List["MovieDB"]] = relationship(
        secondary=movie_genres,
        back_populates="genres",
        lazy="selectin",
    )


class StarDB(Base):
    """Represents an actor associated with movies."""

    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )

    movies: Mapped[List["MovieDB"]] = relationship(
        secondary=movie_stars,
        back_populates="stars",
        lazy="selectin",
    )


class DirectorDB(Base):
    """Represents a director associated with movies."""

    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )

    movies: Mapped[List["MovieDB"]] = relationship(
        secondary=movie_directors,
        back_populates="directors",
        lazy="selectin",
    )


class MovieDB(Base):
    """Represents a movie with its details, genres, stars, and directors."""

    __tablename__ = "movies"
    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="uq_movie_identity"),
        CheckConstraint("votes >= 0", name="ck_movies_votes_non_negative"),
        CheckConstraint("price >= 0", name="ck_movies_price_non_negative"),
        CheckConstraint("imdb >= 0 AND imdb <= 10", name="ck_movies_imdb_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid_pkg.uuid4,
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(250), index=True, nullable=False)
    year: Mapped[int] = mapped_column(index=True, nullable=False)
    time: Mapped[int] = mapped_column(nullable=False)

    imdb: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False)
    votes: Mapped[int] = mapped_column(nullable=False)

    meta_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1), nullable=True)
    gross: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)

    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="RESTRICT"), nullable=False
    )

    certification: Mapped["CertificationDB"] = relationship(
        back_populates="movies",
        lazy="joined",
    )

    genres: Mapped[List["GenreDB"]] = relationship(
        secondary=movie_genres,
        back_populates="movies",
        lazy="selectin",
    )

    stars: Mapped[List["StarDB"]] = relationship(
        secondary=movie_stars,
        back_populates="movies",
        lazy="selectin",
    )

    directors: Mapped[List["DirectorDB"]] = relationship(
        secondary=movie_directors,
        back_populates="movies",
        lazy="selectin",
    )

    cart_items: Mapped[list["CartItemDB"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )

    order_items: Mapped[list["OrderItemDB"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )
