from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.accounts.models import GenderEnum, UserGroupEnum
from src.accounts.validators import validate_password_strength


class BaseEmailPasswordSchema(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8, description="Password must be at least 8 characters"
    )

    model_config = {"from_attributes": True}

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class RegisterRequest(BaseEmailPasswordSchema):
    pass


class RegisterResponse(BaseModel):
    id: int
    email: EmailStr
    message: str = (
        "Registration successful. Please check your email to activate your account."
    )

    model_config = {"from_attributes": True}


# TODO: OCA-31 - Чекає на Celery
class ActivateAccountRequest(BaseModel):
    token: str = Field(min_length=1, description="Activation token from email")


class ResendActivationRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class LoginRequest(BaseEmailPasswordSchema):
    pass


# TODO: Чекає на логіку JWT
class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserProfileResponse(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[GenderEnum] = None
    date_of_birth: Optional[date] = None
    info: Optional[str] = None

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    group: UserGroupEnum
    created_at: datetime
    profile: Optional[UserProfileResponse] = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
