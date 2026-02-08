from datetime import date, datetime

from fastapi import Form
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.accounts.models import GenderEnum, UserGroupEnum
from src.accounts.validators import validate_password_strength


class BaseEmailPasswordSchema(BaseModel):
    """
        Base schema for authentication tasks requiring email and password.
        Includes automatic email normalization and password strength validation.
    """
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    password: str = Field(
        min_length=8, description="Password must be at least 8 characters"
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class RegisterRequestSchema(BaseEmailPasswordSchema):
    """Schema for new user registration requests."""
    pass


class RegisterResponseSchema(BaseModel):
    """Successful registration response containing basic user info and instructions."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    message: str = (
        "Registration successful. Please check your email to activate your account."
    )


class ActivateAccountRequestSchema(BaseModel):
    """Schema for account activation via secure token."""
    token: str = Field(min_length=1, description="Activation token from email")


class ResendActivationRequestSchema(BaseModel):
    """Request schema for resending the activation link."""
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class LoginRequestSchema(BaseEmailPasswordSchema):
    """Credentials required for user authentication."""
    pass


class TokenPairSchema(BaseModel):
    """Standard JWT response containing both access and refresh tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponseSchema(BaseModel):
    """Response containing only a new access token after rotation."""
    access_token: str
    token_type: str = "bearer"


class LogoutRequestSchema(BaseModel):
    """Schema to invalidate a session by providing the refresh token."""
    refresh_token: str


class ChangePasswordRequestSchema(BaseModel):
    """Internal password update schema for authenticated users."""
    old_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class ForgotPasswordRequestSchema(BaseModel):
    """Schema to initiate the password recovery process via email."""
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class ResetPasswordRequestSchema(BaseModel):
    """Schema to set a new password using a recovery token."""
    token: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class RefreshTokenRequestSchema(BaseModel):
    """Schema for token rotation requests."""
    refresh_token: str


class ProfileUpdateSchema(BaseModel):
    """
        Schema for updating user profile details.
        Supports both JSON and Form data (as_form) for multipart requests.
    """
    model_config = ConfigDict(from_attributes=True)

    first_name: str | None = None
    last_name: str | None = None
    gender: GenderEnum | None = None
    date_of_birth: date | None = None
    info: str | None = None

    @classmethod
    def as_form(
        cls,
        first_name: str | None = Form(None),
        last_name: str | None = Form(None),
        gender: GenderEnum | None = Form(None),  # noqa: B008
        date_of_birth: date | None = Form(None),  # noqa: B008
        info: str | None = Form(None),
    ) -> "ProfileUpdateSchema":
        return cls(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info,
        )


class UserProfileResponseSchema(BaseModel):
    """Public profile information returned in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str | None = None
    last_name: str | None = None
    avatar: str | None = None
    gender: GenderEnum | None = None
    date_of_birth: date | None = None
    info: str | None = None


class UserResponseSchema(BaseModel):
    """
        Comprehensive user data schema, including group role,
        status, and profile details. Used in administrative and profile views.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
    group: UserGroupEnum
    created_at: datetime
    profile: UserProfileResponseSchema | None = None


class MessageResponseSchema(BaseModel):
    """Generic schema for returning simple text messages or confirmations."""
    message: str


class AdminUserUpdateSchema(BaseModel):
    """Administrative schema to modify user status or change authorization groups."""
    is_active: bool | None = None
    group_id: int | None = None
