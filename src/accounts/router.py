from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm

from src.accounts.dependencies import (
    allow_admin,
    get_auth_service,
    get_current_user,
)
from src.accounts.exceptions import (
    AccountNotActiveException,
    InvalidTokenException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from src.accounts.models import UserDB
from src.accounts.schemas import (
    ActivateAccountRequestSchema,
    AdminUserUpdateSchema,
    ChangePasswordRequestSchema,
    ForgotPasswordRequestSchema,
    LoginRequestSchema,
    MessageResponseSchema,
    ProfileUpdateSchema,
    RefreshTokenRequestSchema,
    RegisterRequestSchema,
    RegisterResponseSchema,
    ResendActivationRequestSchema,
    ResetPasswordRequestSchema,
    TokenPairSchema,
    UserProfileResponseSchema,
    UserResponseSchema,
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
    summary="Login via JSON (Standard)",
)
async def login_user(
    login_data: LoginRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        return await service.login_user(login_data)
    except Exception:
        raise HTTPException(status_code=401, detail="Auth failed")


@router.post(
    "/token/",
    response_model=TokenPairSchema,
    summary="Login via Form Data (Swagger/OAuth2)",
    include_in_schema=False,
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        login_schema = LoginRequestSchema(
            email=form_data.username, password=form_data.password
        )
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid email format")

    try:
        return await service.login_user(login_schema)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post(
    "/refresh/",
    response_model=TokenPairSchema,
    status_code=status.HTTP_200_OK,
)
async def refresh_access_token(
    token_data: RefreshTokenRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        return await service.refresh_token(token_data)
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


@router.post("/activate/resend/", response_model=MessageResponseSchema)
async def resend_activation_token(
    data: ResendActivationRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    await service.resend_activation_email(data.email)
    return MessageResponseSchema(
        message="Activation token sent if account exists and is inactive."
    )


@router.post("/me/change-password/", response_model=MessageResponseSchema)
async def change_password(
    password_data: ChangePasswordRequestSchema,
    user: Annotated[UserDB, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    await service.change_password(user, password_data)
    return MessageResponseSchema(message="Password updated successfully.")


@router.get(
    "/me/",
    response_model=UserResponseSchema,
    summary="Get current user info",
)
async def get_me(user: Annotated[UserDB, Depends(get_current_user)]):
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "group": user.group.name,
        "profile": user.profile,
    }


@router.patch(
    "/me/profile/",
    response_model=UserProfileResponseSchema,
    summary="Update my profile",
)
async def update_my_profile(
    profile_data: Annotated[ProfileUpdateSchema, Depends(ProfileUpdateSchema.as_form)],
    user: Annotated[UserDB, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    avatar: Annotated[UploadFile | None, File()] = None,
):
    update_data = profile_data.model_dump(exclude_none=True)

    return await service.update_profile(
        user=user, profile_data=update_data, avatar=avatar
    )


@router.post(
    "/logout/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
)
async def logout(
    token_data: RefreshTokenRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    await service.logout_user(token_data.refresh_token)
    return None


@router.patch(
    "/admin/users/{user_id}/",
    response_model=UserResponseSchema,
    dependencies=[Depends(allow_admin)],
)
async def admin_update_user(
    user_id: int,
    update_data: AdminUserUpdateSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    user = await service.admin_update_user(user_id, update_data)

    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "group": user.group.name,
        "profile": user.profile,
    }
