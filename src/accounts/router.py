import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
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
from src.cart.dependencies import get_cart_service
from src.cart.services import CartService

router = APIRouter()
"""
    API Router for account management.
    Handles registration, authentication, profile updates, and administrative actions.
"""


@router.post(
    "/register/",
    response_model=RegisterResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Conflict - User with this email already exists."},
        500: {"description": "Internal Server Error - Default group not found."},
    },
)
async def register_user(
    user_data: RegisterRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    """
    Registers a new user and triggers an activation email.

    Returns 201 Created on success.
    Raises 409 Conflict if the email is already taken.
    """
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
    responses={
        400: {"description": "Bad Request - Invalid token or account already active."}
    },
)
async def activate_account(
    activation_data: ActivateAccountRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    """
    Activates a user account using the token provided via email.
    """
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
    responses={401: {"description": "Unauthorized - Invalid email or password."}},
)
async def login_user(
    login_data: LoginRequestSchema,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    cart_service: Annotated[CartService, Depends(get_cart_service)],
    cart_id: str | None = Cookie(None),
):
    """
    Authenticates a user and returns JWT access and refresh tokens.

    If an anonymous cart exists (via cookie), it will be merged with the
    user's persistent cart upon successful login.
    """
    try:
        token_pair = await service.login_user(login_data)
    except Exception:
        raise HTTPException(status_code=401, detail="Auth failed")

    if cart_id:
        try:
            payload = service.jwt_manager.decode_access_token(token_pair.access_token)
            user_id = payload.get("user_id")

            if user_id:
                await cart_service.merge_anon_cart(
                    anon_id=cart_id, user_id=int(user_id)
                )
                response.delete_cookie(key="cart_id")

        except Exception as e:
            logging.error(f"Failed to merge cart: {e}")

    return token_pair


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
    responses={
        401: {"description": "Unauthorized - Invalid or expired refresh token."},
        404: {"description": "Not Found - User associated with token not found."},
    },
)
async def refresh_access_token(
    token_data: RefreshTokenRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    """
    Rotates the session by exchanging a valid refresh token for a new token pair.
    """
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
    responses={200: {"description": "Success - Instructions sent if email exists."}},
)
async def request_password_reset(
    data: ForgotPasswordRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    """
    Initiates the password recovery flow by sending a reset link to the provided email.
    """
    await service.request_password_reset(data)
    return MessageResponseSchema(
        message="If you are registered, you will receive an email with instructions."
    )


@router.post(
    "/reset-password/complete/",
    response_model=MessageResponseSchema,
    responses={400: {"description": "Bad Request - Invalid or expired reset token."}},
)
async def reset_password_complete(
    data: ResetPasswordRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    """
    Updates the user's password using a valid reset token.
    """
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
    """
    Allows an authenticated user to change their password while logged in.
    """
    await service.change_password(user, password_data)
    return MessageResponseSchema(message="Password updated successfully.")


@router.get(
    "/me/",
    response_model=UserResponseSchema,
    summary="Get current user info",
    responses={401: {"description": "Unauthorized - Token missing or invalid."}},
)
async def get_me(user: Annotated[UserDB, Depends(get_current_user)]):
    """
    Returns complete information about the currently authenticated user.
    """
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
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Bad Request - Invalid data or file format."},
    },
)
async def update_my_profile(
    profile_data: Annotated[ProfileUpdateSchema, Depends(ProfileUpdateSchema.as_form)],
    user: Annotated[UserDB, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    avatar: Annotated[UploadFile | None, File()] = None,
):
    """
    Updates personal profile data. Supports multipart/form-data for avatar uploads to S3.
    """
    update_data = profile_data.model_dump(exclude_none=True)

    return await service.update_profile(
        user=user, profile_data=update_data, avatar=avatar
    )


@router.post(
    "/logout/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    responses={
        204: {"description": "No Content - Successfully logged out."},
        401: {"description": "Unauthorized"},
    },
)
async def logout(
    token_data: RefreshTokenRequestSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    """
    Inactivates the session by blacklisting/deleting the provided refresh token.
    """
    await service.logout_user(token_data.refresh_token)
    return None


@router.patch(
    "/admin/users/{user_id}/",
    response_model=UserResponseSchema,
    dependencies=[Depends(allow_admin)],
    responses={
        403: {"description": "Forbidden - Only admins can access this."},
        404: {"description": "Not Found - User not found."},
    },
)
async def admin_update_user(
    user_id: int,
    update_data: AdminUserUpdateSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    """
    Administrative endpoint to manage user status and roles.
    Requires ADMIN privileges.
    """
    user = await service.admin_update_user(user_id, update_data)

    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "group": user.group.name,
        "profile": user.profile,
    }
