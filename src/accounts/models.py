import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql.functions import func

from src.database import Base

if TYPE_CHECKING:
    from src.payments.models import PaymentDB


class UserGroupEnum(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class GenderEnum(str, enum.Enum):
    MAN = "man"
    WOMAN = "woman"


class UserGroupDB(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[UserGroupEnum] = mapped_column(
        Enum(UserGroupEnum), nullable=False, unique=True
    )
    users: Mapped[list["UserDB"]] = relationship(back_populates="group")


class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    group_id: Mapped[int] = mapped_column(ForeignKey("user_groups.id"), nullable=False)
    group: Mapped["UserGroupDB"] = relationship(back_populates="users")

    cart: Mapped["CartDB"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    orders: Mapped[list["OrderDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    payments: Mapped[list["PaymentDB"]] = relationship(
        "PaymentDB", back_populates="user"
    )

    profile: Mapped["UserProfileDB"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    activation_token: Mapped["ActivationTokenDB"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    password_reset_token: Mapped["PasswordResetTokenDB"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    refresh_tokens: Mapped[list["RefreshTokenDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserProfileDB(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True
    )
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    avatar: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[GenderEnum | None] = mapped_column(Enum(GenderEnum))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    info: Mapped[str | None] = mapped_column(Text)
    user: Mapped["UserDB"] = relationship(back_populates="profile")


class ActivationTokenDB(Base):
    __tablename__ = "activation_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    user: Mapped["UserDB"] = relationship(back_populates="activation_token")


class PasswordResetTokenDB(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    user: Mapped["UserDB"] = relationship(back_populates="password_reset_token")


class RefreshTokenDB(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    user: Mapped["UserDB"] = relationship(back_populates="refresh_tokens")
