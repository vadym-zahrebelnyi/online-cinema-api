from datetime import date, datetime

from fastapi import Form
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.accounts.models import GenderEnum, UserGroupEnum
from src.accounts.validators import validate_password_strength


class BaseEmailPasswordSchema(BaseModel):
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
    pass


class RegisterResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    message: str = (
        "Registration successful. Please check your email to activate your account."
    )


class ActivateAccountRequestSchema(BaseModel):
    token: str = Field(min_length=1, description="Activation token from email")


class ResendActivationRequestSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class LoginRequestSchema(BaseEmailPasswordSchema):
    pass


class TokenPairSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutRequestSchema(BaseModel):
    refresh_token: str


class ChangePasswordRequestSchema(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class ForgotPasswordRequestSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class ResetPasswordRequestSchema(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str


class ProfileUpdateSchema(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str | None = None
    last_name: str | None = None
    avatar: str | None = None
    gender: GenderEnum | None = None
    date_of_birth: date | None = None
    info: str | None = None


class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
    group: UserGroupEnum
    created_at: datetime
    profile: UserProfileResponseSchema | None = None


class MessageResponseSchema(BaseModel):
    message: str


class AdminUserUpdateSchema(BaseModel):
    is_active: bool | None = None
    group_id: int | None = None
