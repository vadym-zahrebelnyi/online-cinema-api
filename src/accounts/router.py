from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.accounts.dependencies import get_auth_service
from src.accounts.exceptions import (
    AccountNotActiveException,
    InvalidCredentialsException,
    InvalidTokenException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from src.accounts.schemas import (
    AccessTokenResponseSchema,
    ActivateAccountRequestSchema,
    ForgotPasswordRequestSchema,
    LoginRequestSchema,
    MessageResponseSchema,
    RefreshTokenRequestSchema,
    RegisterRequestSchema,
    RegisterResponseSchema,
    ResetPasswordRequestSchema,
    TokenPairSchema,
)
from src.accounts.services import AuthService

router = APIRouter()



@router.post(
    "/register/",
    response_model=RegisterResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_data: RegisterRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        return await service.register_user(user_data)
    except UserAlreadyExistsException:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user_data.email} already exists.",
        )
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user group not found.",
        )


@router.post(
    "/activate/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def activate_account(
    activation_data: ActivateAccountRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        await service.activate_user(activation_data)
        return MessageResponseSchema(message="User account activated successfully.")
    except (InvalidTokenException, AccountNotActiveException):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token or account already active.",
        )


@router.post(
    "/login/",
    response_model=TokenPairSchema,
    status_code=status.HTTP_200_OK,
)
async def login_user(
    login_data: LoginRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        return await service.login_user(login_data)
    except InvalidCredentialsException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    except AccountNotActiveException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )


@router.post(
    "/refresh/",
    response_model=AccessTokenResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def refresh_access_token(
    token_data: RefreshTokenRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        tokens = await service.refresh_token(token_data)
        return AccessTokenResponseSchema(access_token=tokens.access_token)
    except InvalidTokenException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )


@router.post(
    "/password-reset/request/",
    response_model=MessageResponseSchema,
)
async def request_password_reset(
    data: ForgotPasswordRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    await service.request_password_reset(data)
    return MessageResponseSchema(
        message="If you are registered, you will receive an email with instructions."
    )


@router.post(
    "/reset-password/complete/",
    response_model=MessageResponseSchema,
)
async def reset_password_complete(
    data: ResetPasswordRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        await service.complete_password_reset(data)
        return MessageResponseSchema(message="Password reset successfully.")
    except InvalidTokenException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token."
        )
