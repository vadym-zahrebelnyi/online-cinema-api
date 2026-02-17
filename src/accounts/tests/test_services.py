from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from src.accounts.exceptions import (
    AccountNotActiveException,
    InvalidCredentialsException,
    InvalidTokenException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from src.accounts.models import (
    ActivationTokenDB,
    PasswordResetTokenDB,
    RefreshTokenDB,
    UserDB,
    UserGroupDB,
    UserGroupEnum,
    UserProfileDB,
)
from src.accounts.schemas import (
    ActivateAccountRequestSchema,
    AdminUserUpdateSchema,
    ChangePasswordRequestSchema,
    ForgotPasswordRequestSchema,
    LoginRequestSchema,
    RefreshTokenRequestSchema,
    RegisterRequestSchema,
    ResetPasswordRequestSchema,
)
from src.accounts.services import AuthService


@pytest.fixture
def mock_db():
    db = AsyncMock()
    mock_result = MagicMock()
    db.execute.return_value = mock_result
    mock_result.scalars.return_value.first.return_value = None
    return db


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.LOGIN_TIME_DAYS = 7
    return settings


@pytest.fixture
def mock_jwt_manager():
    jwt = MagicMock()
    jwt.create_access_token.return_value = "access_token_str"
    jwt.create_refresh_token.return_value = "refresh_token_str"
    return jwt


@pytest.fixture
def mock_s3_client():
    s3 = AsyncMock()
    s3.upload_file.return_value = "https://s3.fake/avatar.jpg"
    return s3


@pytest.fixture
def auth_service(mock_db, mock_settings, mock_jwt_manager, mock_s3_client):
    return AuthService(
        db=mock_db,
        settings=mock_settings,
        jwt_manager=mock_jwt_manager,
        storage_client=mock_s3_client,
    )


@pytest.mark.asyncio
async def test_register_user_success(auth_service, mock_db):
    """
    Test successful user registration.
    Verifies that the user is created with the default group, saved to the database,
    and an activation email task is triggered.
    """
    user_group = UserGroupDB(id=1, name=UserGroupEnum.USER)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user_group
    mock_db.execute.return_value = mock_result

    user_data = RegisterRequestSchema(email="test@example.com", password="StrongPass1!")

    with patch("src.accounts.services.send_activation_email_task.delay") as mock_task:
        result = await auth_service.register_user(user_data)

        assert result.email == "test@example.com"
        assert result.group_id == 1
        assert mock_db.add.call_count >= 3
        mock_db.commit.assert_awaited_once()
        mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_already_exists(auth_service, mock_db):
    """
    Test user registration failure when email already exists.
    Verifies that a UserAlreadyExistsException is raised and the transaction is rolled back twice.
    """
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = UserGroupDB(id=1)
    mock_db.execute.return_value = mock_result
    mock_db.commit.side_effect = IntegrityError(None, None, None)

    user_data = RegisterRequestSchema(
        email="duplicate@example.com", password="StrongPass1!"
    )

    with pytest.raises(UserAlreadyExistsException):
        await auth_service.register_user(user_data)

    assert mock_db.rollback.await_count == 2


@pytest.mark.asyncio
async def test_register_user_no_default_group(auth_service, mock_db):
    """
    Test user registration failure when the default user group is missing.
    Verifies that a UserNotFoundException is raised.
    """
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    user_data = RegisterRequestSchema(email="test@example.com", password="StrongPass1!")

    with pytest.raises(UserNotFoundException):
        await auth_service.register_user(user_data)


@pytest.mark.asyncio
async def test_activate_user_success(auth_service, mock_db):
    """
    Test successful account activation.
    Verifies that the user status is updated to active, the token is deleted,
    and a confirmation email is sent.
    """
    user = UserDB(id=1, email="test@example.com", is_active=False)
    token = ActivationTokenDB(
        token="valid_token",
        user=user,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = token
    mock_db.execute.return_value = mock_result

    with patch(
        "src.accounts.services.send_activation_complete_email_task.delay"
    ) as mock_task:
        await auth_service.activate_user(
            ActivateAccountRequestSchema(token="valid_token")
        )

        assert user.is_active is True
        mock_db.delete.assert_awaited_once_with(token)
        mock_db.commit.assert_awaited_once()
        mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_activate_user_expired(auth_service, mock_db):
    """
    Test account activation failure with an expired token.
    Verifies that InvalidTokenException is raised and the expired token is deleted.
    """
    token = ActivationTokenDB(
        token="expired",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = token
    mock_db.execute.return_value = mock_result

    with pytest.raises(InvalidTokenException):
        await auth_service.activate_user(ActivateAccountRequestSchema(token="expired"))

    mock_db.delete.assert_awaited_once_with(token)


@pytest.mark.asyncio
async def test_activate_user_already_active(auth_service, mock_db):
    """
    Test account activation failure when the user is already active.
    Verifies that AccountNotActiveException is raised.
    """
    user = UserDB(id=1, is_active=True)
    token = ActivationTokenDB(
        token="valid_token",
        user=user,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = token
    mock_db.execute.return_value = mock_result

    with pytest.raises(AccountNotActiveException):
        await auth_service.activate_user(
            ActivateAccountRequestSchema(token="valid_token")
        )


@pytest.mark.asyncio
async def test_login_user_success(auth_service, mock_db):
    """
    Test successful user login.
    Verifies that access and refresh tokens are generated and stored.
    """
    user = UserDB(
        id=1,
        email="test@example.com",
        hashed_password="hashed_secret",
        is_active=True,
    )
    user.verify_password = MagicMock(return_value=True)

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_result

    login_data = LoginRequestSchema(email="test@example.com", password="StrongPass1!")

    result = await auth_service.login_user(login_data)

    assert result.access_token == "access_token_str"
    mock_db.add.assert_called()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_user_invalid_credentials(auth_service, mock_db):
    """
    Test user login failure with incorrect password.
    Verifies that InvalidCredentialsException is raised.
    """
    user = UserDB(id=1, hashed_password="hashed_secret")
    user.verify_password = MagicMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_result

    login_data = LoginRequestSchema(email="test@example.com", password="StrongPass1!")

    with pytest.raises(InvalidCredentialsException):
        await auth_service.login_user(login_data)


@pytest.mark.asyncio
async def test_login_user_inactive(auth_service, mock_db):
    """
    Test user login failure when account is inactive.
    Verifies that AccountNotActiveException is raised.
    """
    user = UserDB(
        id=1,
        email="test@example.com",
        hashed_password="hashed_secret",
        is_active=False,
    )
    user.verify_password = MagicMock(return_value=True)

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_result

    login_data = LoginRequestSchema(email="test@example.com", password="StrongPass1!")

    with pytest.raises(AccountNotActiveException):
        await auth_service.login_user(login_data)


@pytest.mark.asyncio
async def test_refresh_token_success(auth_service, mock_db, mock_jwt_manager):
    """
    Test successful token refresh.
    Verifies that a new token pair is issued and the old refresh token is replaced.
    """
    mock_jwt_manager.decode_refresh_token.return_value = {"user_id": 1}

    stored_token = RefreshTokenDB(
        token="old_refresh",
        user_id=1,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    user = UserDB(id=1)

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.side_effect = [stored_token, user]
    mock_db.execute.return_value = mock_result

    token_data = RefreshTokenRequestSchema(refresh_token="old_refresh")
    result = await auth_service.refresh_token(token_data)

    assert result.access_token == "access_token_str"
    mock_db.add.assert_called()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_password_reset_success(auth_service, mock_db):
    """
    Test successful password reset request.
    Verifies that old tokens are deleted, a new token is created, and an email is sent.
    """
    user = UserDB(id=1, email="test@example.com", is_active=True)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_result

    data = ForgotPasswordRequestSchema(email="test@example.com")

    with patch(
        "src.accounts.services.send_password_reset_email_task.delay"
    ) as mock_task:
        await auth_service.request_password_reset(data)

        mock_db.execute.assert_called()
        mock_db.add.assert_called()
        mock_db.commit.assert_awaited_once()
        mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_complete_password_reset_success(auth_service, mock_db):
    """
    Test successful password reset completion.
    Verifies that the password is updated, the token is deleted, and a confirmation email is sent.
    """
    user = UserDB(id=1, email="test@example.com")
    token = PasswordResetTokenDB(
        token="valid_token",
        user=user,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = token
    mock_db.execute.return_value = mock_result

    data = ResetPasswordRequestSchema(
        token="valid_token", new_password="NewStrongPass1!"
    )

    with patch(
        "src.accounts.services.send_password_reset_complete_email_task.delay"
    ) as mock_task:
        await auth_service.complete_password_reset(data)

        assert user.verify_password("NewStrongPass1!") is True
        mock_db.delete.assert_awaited_once_with(token)
        mock_db.commit.assert_awaited_once()
        mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_logout_user_success(auth_service, mock_db):
    """
    Test successful user logout.
    Verifies that the refresh token is deleted from the database.
    """
    refresh_token = "valid_refresh_token"
    await auth_service.logout_user(refresh_token)

    mock_db.execute.assert_called()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_profile_with_avatar(auth_service, mock_db, mock_s3_client):
    """
    Test user profile update including avatar upload.
    Verifies that profile fields are updated and the avatar is uploaded to S3.
    """
    user = UserDB(id=1)
    profile = UserProfileDB(user_id=1, first_name="Old")
    user.profile = profile

    avatar_file = AsyncMock()
    avatar_file.filename = "me.png"
    avatar_file.read.return_value = b"image_content"
    avatar_file.content_type = "image/png"

    profile_data = {"first_name": "New"}

    result = await auth_service.update_profile(user, profile_data, avatar=avatar_file)

    assert result.first_name == "New"
    assert result.avatar == "https://s3.fake/avatar.jpg"
    mock_s3_client.upload_file.assert_awaited_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_resend_activation_email_success(auth_service, mock_db):
    """
    Test resending activation email.
    Verifies that the old token is deleted, a new one is created, and an email is sent.
    """
    user = UserDB(id=1, email="test@example.com", is_active=False)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_result

    with patch("src.accounts.services.send_activation_email_task.delay") as mock_task:
        await auth_service.resend_activation_email("test@example.com")

        mock_db.execute.assert_called()
        mock_db.add.assert_called()
        mock_db.commit.assert_awaited_once()
        mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_change_password_success(auth_service, mock_db):
    """
    Test successful password change for authenticated user.
    Verifies that the password is updated and changes are committed.
    """
    user = UserDB(id=1, hashed_password="old_hash")
    user.verify_password = MagicMock(return_value=True)

    data = ChangePasswordRequestSchema(
        old_password="OldPass1!", new_password="NewPass1!"
    )

    await auth_service.change_password(user, data)

    assert user.hashed_password != "old_hash"
    mock_db.add.assert_called_with(user)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_update_user_success(auth_service, mock_db):
    """
    Test admin update of user details.
    Verifies that user status and group are updated successfully.
    """
    user = UserDB(id=1, is_active=False, group_id=1)
    new_group = UserGroupDB(id=2, name=UserGroupEnum.MODERATOR)

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.side_effect = [user]
    mock_db.execute.return_value = mock_result
    mock_db.get.return_value = new_group

    data = AdminUserUpdateSchema(is_active=True, group_id=2)

    result = await auth_service.admin_update_user(1, data)

    assert result.is_active is True
    assert result.group_id == 2
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(user)
