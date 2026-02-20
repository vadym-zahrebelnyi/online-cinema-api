import enum
from datetime import date, datetime, timedelta, timezone
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
from sqlalchemy.orm.mapper import validates
from sqlalchemy.sql.functions import func
from sqlalchemy.sql.schema import UniqueConstraint

from src.core import Base
from src.security.passwords import hash_password, verify_password
from src.security.utils import generate_secure_token

from . import validators

if TYPE_CHECKING:
    from src.cart.models import CartDB
    from src.orders.models import OrderDB
    from src.payments.models import PaymentDB


class UserGroupEnum(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class GenderEnum(str, enum.Enum):
    MAN = "man"
    WOMAN = "woman"


class UserGroupDB(Base):
    """
    Represents user role groups within the system.
    Defines access levels such as 'admin', 'moderator', or 'user'.
    """

    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[UserGroupEnum] = mapped_column(
        Enum(UserGroupEnum), nullable=False, unique=True
    )
    users: Mapped[list["UserDB"]] = relationship(back_populates="group")


class UserDB(Base):
    """
    The core user model for the application.
    Handles authentication data, password hashing mechanisms,
    and serves as the central point for profiles, orders, and security tokens.
    """

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

    payments: Mapped[list["PaymentDB"]] = relationship(
        "PaymentDB", back_populates="user"
    )

    cart: Mapped["CartDB"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    orders: Mapped[list["OrderDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
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

    def has_group(self, group_name: UserGroupEnum) -> bool:
        """
        Checks if the user belongs to a specific security group.
        """
        return self.group.name == group_name

    @property
    def password(self) -> None:
        raise AttributeError(
            "Password is write-only. Use the setter to set the password."
        )

    @password.setter
    def password(self, raw_password: str) -> None:
        """
        Set the user's password after validating its strength and hashing it.
        """
        validators.validate_password_strength(raw_password)
        self.hashed_password = hash_password(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        """
        Verify the provided password against the stored hashed password.
        """
        return verify_password(raw_password, self.hashed_password)

    @validates("email")
    def validate_email(self, key, value):
        return validators.validate_email(value.lower())


class UserProfileDB(Base):
    """
    Stores extended personal information for a user.
    Contains non-authentication data like names, gender, avatar, and bio.
    """

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

    def __repr__(self):
        return (
            f"<UserProfileDB(id={self.id}, first_name={self.first_name}, last_name={self.last_name}, "
            f"gender={self.gender}, date_of_birth={self.date_of_birth})>"
        )


class TokenBaseDB(Base):
    """
    An abstract base class for various security tokens.
    Provides common fields including the secure token string,
    expiration timestamp, and the associated user ID.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, default=generate_secure_token
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class ActivationTokenDB(TokenBaseDB):
    __tablename__ = "activation_tokens"

    user: Mapped["UserDB"] = relationship(back_populates="activation_token")
    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self):
        return f"<ActivationTokenDB(id={self.id}, token={self.token}, expires_at={self.expires_at})>"


class PasswordResetTokenDB(TokenBaseDB):
    __tablename__ = "password_reset_tokens"

    user: Mapped["UserDB"] = relationship(back_populates="password_reset_token")
    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self):
        return f"<PasswordResetTokenDB(id={self.id}, token={self.token}, expires_at={self.expires_at})>"


class RefreshTokenDB(TokenBaseDB):
    """
    Represents long-lived refresh tokens used to obtain
    new access tokens without re-authenticating the user.
    """

    __tablename__ = "refresh_tokens"

    token: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, default=generate_secure_token
    )
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="refresh_tokens")

    @classmethod
    def create(
        cls, user_id: int | Mapped[int], days_valid: int, token: str
    ) -> "RefreshTokenDB":
        """
        Factory method to create a new RefreshTokenDB instance.

        This method simplifies the creation of a new refresh token by calculating
        the expiration date based on the provided number of valid days and setting
        the required attributes.
        """
        expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)
        return cls(user_id=user_id, expires_at=expires_at, token=token)

    def __repr__(self):
        return f"<RefreshTokenDB(id={self.id}, token={self.token}, expires_at={self.expires_at})>"
