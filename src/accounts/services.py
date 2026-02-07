from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
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
from src.core.settings import Settings
from src.security.interfaces import JWTAuthManagerInterface


class AuthService:
    def __init__(
        self, db: AsyncSession, settings: Settings, jwt_manager: JWTAuthManagerInterface
    ):
        self.db = db
        self.settings = settings
        self.jwt_manager = jwt_manager

    async def register_user(self, user_data: RegisterRequestSchema) -> UserDB:
        stmt = select(UserGroupDB).where(UserGroupDB.name == UserGroupEnum.USER)
        result = await self.db.execute(stmt)
        user_group = result.scalars().first()

        if not user_group:
            raise UserNotFoundException()

        try:
            new_user = UserDB.create(
                email=user_data.email,
                raw_password=user_data.password,
                group_id=user_group.id,
            )
            self.db.add(new_user)
            await self.db.flush()

            new_profile = UserProfileDB(user_id=new_user.id)
            self.db.add(new_profile)

            activation_token = ActivationTokenDB(user_id=new_user.id)
            self.db.add(activation_token)

            await self.db.commit()
            await self.db.refresh(new_user)

            from src.accounts.tasks import send_activation_email_task

            send_activation_email_task.delay(new_user.email, activation_token.token)

            return new_user

        except IntegrityError:
            await self.db.rollback()
            raise UserAlreadyExistsException()

    async def activate_user(
        self, activation_data: ActivateAccountRequestSchema
    ) -> None:
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
            await self.db.commit()
            raise InvalidTokenException()

        user = token_record.user
        if user.is_active:
            raise AccountNotActiveException()

        user.is_active = True
        await self.db.delete(token_record)
        await self.db.commit()

        from src.accounts.tasks import send_activation_complete_email_task

        send_activation_complete_email_task.delay(user.email)

    async def login_user(self, login_data: LoginRequestSchema) -> TokenPairSchema:
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
        await self.db.commit()

        return TokenPairSchema(
            access_token=jwt_access_token, refresh_token=jwt_refresh_token
        )

    async def refresh_token(
        self, token_data: RefreshTokenRequestSchema
    ) -> TokenPairSchema:
        try:
            decoded = self.jwt_manager.decode_refresh_token(token_data.refresh_token)
            user_id = decoded.get("user_id")
        except Exception:
            raise InvalidTokenException()

        stmt = select(RefreshTokenDB).where(
            RefreshTokenDB.token == token_data.refresh_token
        )
        result = await self.db.execute(stmt)
        stored_token = result.scalars().first()

        if not stored_token:
            raise InvalidTokenException()

        await self.db.delete(stored_token)

        if stored_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            await self.db.commit()
            raise InvalidTokenException()

        stmt = select(UserDB).where(UserDB.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if not user:
            await self.db.commit()
            raise UserNotFoundException()

        new_access_token = self.jwt_manager.create_access_token({"user_id": user_id})
        new_refresh_token = self.jwt_manager.create_refresh_token({"user_id": user_id})

        new_refresh_record = RefreshTokenDB.create(
            user_id=user.id,
            days_valid=self.settings.LOGIN_TIME_DAYS,
            token=new_refresh_token,
        )
        self.db.add(new_refresh_record)

        await self.db.commit()

        return TokenPairSchema(
            access_token=new_access_token, refresh_token=new_refresh_token
        )

    async def request_password_reset(self, data: ForgotPasswordRequestSchema) -> None:
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
        await self.db.commit()

        from src.accounts.tasks import send_password_reset_email_task

        send_password_reset_email_task.delay(user.email, reset_token.token)

    async def complete_password_reset(self, data: ResetPasswordRequestSchema) -> None:
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
        await self.db.commit()

        from src.accounts.tasks import send_password_reset_complete_email_task

        send_password_reset_complete_email_task.delay(user.email)

    async def logout_user(self, refresh_token: str) -> None:
        stmt = delete(RefreshTokenDB).where(RefreshTokenDB.token == refresh_token)
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_profile(
        self, user: UserDB, profile_data: dict, avatar: UploadFile | None = None
    ) -> UserProfileDB:
        profile = user.profile

        if not profile:
            raise UserNotFoundException("Profile integrity error")

        for key, value in profile_data.items():
            setattr(profile, key, value)

        if avatar:
            # TODO: (S3 / MinIO / Local)
            # file_path = await save_file_to_storage(avatar)
            # profile.avatar = file_path

            profile.avatar = f"path/to/{avatar.filename}"

        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def resend_activation_email(self, email: str) -> None:
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
        await self.db.commit()

        from src.accounts.tasks import send_activation_email_task

        send_activation_email_task.delay(user.email, new_token.token)

    async def change_password(
        self, user: UserDB, data: ChangePasswordRequestSchema
    ) -> None:
        if not user.verify_password(data.old_password):
            raise InvalidCredentialsException()

        user.password = data.new_password
        self.db.add(user)
        await self.db.commit()

    async def admin_update_user(
        self, user_id: int, data: AdminUserUpdateSchema
    ) -> UserDB:
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

        await self.db.commit()
        await self.db.refresh(user)
        return user
