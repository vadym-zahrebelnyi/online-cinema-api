import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from jose.exceptions import JWTError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

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
    TokenPairSchema,
)
from src.accounts.tasks import (
    send_activation_complete_email_task,
    send_activation_email_task,
    send_password_reset_complete_email_task,
    send_password_reset_email_task,
)
from src.cart.services import CartService
from src.core.settings import Settings
from src.security.interfaces import JWTAuthManagerInterface
from src.storages.s3 import S3StorageClient


class AuthService:
    """
    Service for handling authentication, user management, and profile operations.

    This service coordinates interactions between the database, JWT manager,
    S3 storage, and background tasks (Celery) to provide a complete
    identity management system.
    """

    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        jwt_manager: JWTAuthManagerInterface,
        storage_client: S3StorageClient,
    ):
        self.db = db
        self.settings = settings
        self.jwt_manager = jwt_manager
        self.storage_client = storage_client

    async def register_user(self, user_data: RegisterRequestSchema) -> UserDB:
        """
        Registers a new user in the system.

        Steps:
        1. Assigns the default 'USER' group.
        2. Creates a UserDB record with a hashed password.
        3. Initializes an empty UserProfileDB.
        4. Generates an activation token.
        5. Triggers a background task to send an activation email.

        :raises UserNotFoundException: If the default user group is missing.
        :raises UserAlreadyExistsException: If the email is already registered.
        """
        stmt = select(UserGroupDB).where(UserGroupDB.name == UserGroupEnum.USER)
        result = await self.db.execute(stmt)
        user_group = result.scalars().first()

        if not user_group:
            raise UserNotFoundException()

        try:
            new_user = UserDB(
                email=user_data.email,
                group_id=user_group.id,
            )
            new_user.password = user_data.password

            self.db.add(new_user)
            await self.db.flush()

            new_profile = UserProfileDB(user_id=new_user.id)
            self.db.add(new_profile)

            activation_token = ActivationTokenDB(user_id=new_user.id)
            self.db.add(activation_token)

            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                raise

            await self.db.refresh(new_user)

            send_activation_email_task.delay(new_user.email, activation_token.token)

            return new_user

        except IntegrityError:
            await self.db.rollback()
            raise UserAlreadyExistsException()

    async def activate_user(
        self, activation_data: ActivateAccountRequestSchema
    ) -> None:
        """
        Activates a user account using a secure token.

        Validates the token's existence and expiration date. Upon success,
        sets 'is_active' to True and removes the token.

        :raises InvalidTokenException: If the token is missing or expired.
        :raises AccountNotActiveException: If the user is already active.
        """
        stmt = (
            select(ActivationTokenDB)
            .options(joinedload(ActivationTokenDB.user))
            .where(ActivationTokenDB.token == activation_data.token)
        )
        result = await self.db.execute(stmt)
        token_record = result.scalars().first()

        if not token_record:
            raise InvalidTokenException()

        if token_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            await self.db.delete(token_record)
            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                raise
            raise InvalidTokenException()

        user = token_record.user
        try:
            if user.is_active:
                raise AccountNotActiveException()

            user.is_active = True
            await self.db.delete(token_record)

            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

        send_activation_complete_email_task.delay(user.email)

    async def login_user(
        self,
        login_data: LoginRequestSchema,
        cart_id: str | None = None,
        cart_service: CartService | None = None,
    ) -> TokenPairSchema:

        stmt = select(UserDB).where(UserDB.email == login_data.email)
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if not user or not user.verify_password(login_data.password):
            raise InvalidCredentialsException()

        if not user.is_active:
            raise AccountNotActiveException()

        jwt_refresh_token = self.jwt_manager.create_refresh_token({"user_id": user.id})
        jwt_access_token = self.jwt_manager.create_access_token({"user_id": user.id})

        refresh_token_record = RefreshTokenDB.create(
            user_id=user.id,
            days_valid=self.settings.LOGIN_TIME_DAYS,
            token=jwt_refresh_token,
        )
        self.db.add(refresh_token_record)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        if cart_id and cart_service:
            try:
                await cart_service.merge_anon_cart(
                    anon_id=cart_id,
                    user_id=user.id,
                )
            except Exception as e:
                logging.error(f"Failed to merge cart: {e}")

        return TokenPairSchema(
            access_token=jwt_access_token,
            refresh_token=jwt_refresh_token,
        )

    async def refresh_token(
        self, token_data: RefreshTokenRequestSchema
    ) -> TokenPairSchema:
        """
        Rotates JWT tokens using a valid Refresh Token.
        Verifies the provided refresh token, deletes the old one from DB,
        and issues a new Access/Refresh pair (Token Rotation).

        :raises InvalidTokenException: If the token is reused, expired, or invalid.
        """

        try:
            decoded = self.jwt_manager.decode_refresh_token(token_data.refresh_token)
            user_id = decoded.get("user_id")
        except JWTError:
            raise InvalidTokenException()

        stmt = select(RefreshTokenDB).where(
            RefreshTokenDB.token == token_data.refresh_token
        )
        result = await self.db.execute(stmt)
        stored_token = result.scalars().first()

        if not stored_token:
            raise InvalidTokenException()

        if stored_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            await self.db.delete(stored_token)

            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                raise

            raise InvalidTokenException()

        stmt = select(UserDB).where(UserDB.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if not user:
            raise UserNotFoundException()

        new_access_token = self.jwt_manager.create_access_token({"user_id": user_id})
        new_refresh_token = self.jwt_manager.create_refresh_token({"user_id": user_id})

        new_refresh_record = RefreshTokenDB.create(
            user_id=user.id,
            days_valid=self.settings.LOGIN_TIME_DAYS,
            token=new_refresh_token,
        )
        self.db.add(new_refresh_record)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return TokenPairSchema(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )

    async def request_password_reset(self, data: ForgotPasswordRequestSchema) -> None:
        """
        Initiates the password recovery process.

        Generates a PasswordResetToken and triggers a background task
        to send reset instructions to the user's email.
        """
        stmt = select(UserDB).where(UserDB.email == data.email)
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if not user or not user.is_active:
            return

        await self.db.execute(
            delete(PasswordResetTokenDB).where(PasswordResetTokenDB.user_id == user.id)
        )

        reset_token = PasswordResetTokenDB(user_id=user.id)
        self.db.add(reset_token)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        send_password_reset_email_task.delay(user.email, reset_token.token)

    async def complete_password_reset(self, data: ResetPasswordRequestSchema) -> None:
        """
        Sets a new password using a valid reset token.

        Validates the token and updates the User's hashed password.
        """
        stmt = (
            select(PasswordResetTokenDB)
            .options(joinedload(PasswordResetTokenDB.user))
            .where(PasswordResetTokenDB.token == data.token)
        )
        result = await self.db.execute(stmt)
        token_record = result.scalars().first()

        if not token_record:
            raise InvalidTokenException()

        if token_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            await self.db.delete(token_record)
            await self.db.commit()
            raise InvalidTokenException()

        user = token_record.user
        user.password = data.new_password

        await self.db.delete(token_record)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        send_password_reset_complete_email_task.delay(user.email)

    async def logout_user(self, refresh_token: str) -> None:
        """
        Inactivates a session by deleting the refresh token from the database.
        """
        stmt = delete(RefreshTokenDB).where(RefreshTokenDB.token == refresh_token)
        await self.db.execute(stmt)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

    async def update_profile(
        self, user: UserDB, profile_data: dict, avatar: UploadFile | None = None
    ) -> UserProfileDB:
        """
        Updates user profile information and optionally handles avatar uploads to S3.

        If an avatar is provided, it is uploaded to a unique path in the S3 bucket,
        and the resulting URL is saved in the profile.
        """
        profile = user.profile

        if not profile:
            raise UserNotFoundException("Profile integrity error")

        for key, value in profile_data.items():
            if value is not None:
                setattr(profile, key, value)

        if avatar:
            file_content = await avatar.read()

            file_extension = avatar.filename.split(".")[-1]
            file_name = f"avatars/{user.id}/{uuid.uuid4()}.{file_extension}"

            file_url = await self.storage_client.upload_file(
                file_name=file_name,
                file_data=file_content,
                content_type=avatar.content_type or "application/octet-stream",
            )

            profile.avatar = file_url

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(profile)
        return profile

    async def resend_activation_email(self, email: str) -> None:
        """
        Invalidates old activation tokens and sends a fresh one.
        Used when the user hasn't received the email or the previous token expired.
        """
        stmt = select(UserDB).where(UserDB.email == email)
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if not user or user.is_active:
            return

        await self.db.execute(
            delete(ActivationTokenDB).where(ActivationTokenDB.user_id == user.id)
        )

        new_token = ActivationTokenDB(user_id=user.id)
        self.db.add(new_token)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        send_activation_email_task.delay(user.email, new_token.token)

    async def change_password(
        self, user: UserDB, data: ChangePasswordRequestSchema
    ) -> None:
        """
        Allows an authenticated user to update their password.

        Verifies the old password before applying the new one.
        """
        if not user.verify_password(data.old_password):
            raise InvalidCredentialsException()

        user.password = data.new_password
        self.db.add(user)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

    async def admin_update_user(
        self, user_id: int, data: AdminUserUpdateSchema
    ) -> UserDB:
        """
        Administrative method to modify user status or group.
        Allows manual activation/deactivation and role assignment.
        """
        stmt = (
            select(UserDB)
            .options(joinedload(UserDB.profile), joinedload(UserDB.group))
            .where(UserDB.id == user_id)
        )
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if not user:
            raise UserNotFoundException()

        if data.is_active is not None:
            user.is_active = data.is_active

        if data.group_id is not None:
            group = await self.db.get(UserGroupDB, data.group_id)
            if not group:
                raise HTTPException(status_code=400, detail="Invalid group ID")
            user.group_id = data.group_id

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(user)
        return user
