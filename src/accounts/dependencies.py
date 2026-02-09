from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.accounts.models import UserDB, UserGroupEnum
from src.accounts.services import AuthService
from src.core.database import get_db
from src.core.settings import Settings, get_settings, settings
from src.security.interfaces import JWTAuthManagerInterface
from src.security.token_manager import JWTAuthManager
from src.storages.s3 import S3StorageClient


def get_s3_client() -> S3StorageClient:
    """
        Initializes and returns an S3 storage client using global application settings.
        Used for handling file uploads (e.g., user avatars).
    """
    return S3StorageClient(
        endpoint_url=settings.S3_URL,
        access_key=settings.S3_ACCESS_KEY,
        secret_key=settings.S3_SECRET_KEY,
        bucket_name=settings.S3_BUCKET_NAME,
        region_name=settings.S3_REGION,
    )


def get_jwt_auth_manager(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JWTAuthManagerInterface:
    """
    Create and return a JWT authentication manager instance.

    This function uses the provided application settings to instantiate a JWTAuthManager, which implements
    the JWTAuthManagerInterface. The manager is configured with secret keys for access and refresh tokens
    as well as the JWT signing algorithm specified in the settings.

    Args:
        settings (BaseAppSettings, optional): The application settings instance.
        Defaults to the output of get_settings().

    Returns:
        JWTAuthManagerInterface: An instance of JWTAuthManager configured with
        the appropriate secret keys and algorithm.
    """
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    jwt_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
    s3_client: Annotated[S3StorageClient, Depends(get_s3_client)],
) -> AuthService:
    """
        Provides an instance of AuthService with all required collaborators
        (DB, Settings, JWT, S3) injected.
    """
    return AuthService(
        db=db, settings=settings, jwt_manager=jwt_manager, storage_client=s3_client
    )


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/accounts/token/", auto_error=False
)
http_bearer = HTTPBearer(auto_error=False)


async def _get_user_from_request(
    token_oauth: str | None,
    token_bearer: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
    jwt_manager: JWTAuthManagerInterface,
) -> UserDB | None:
    """
        Internal helper to extract and validate a user from a JWT token found
        in either OAuth2 or Bearer headers.

        Verifies token validity, user existence, and account activity status.
    """
    token = None
    if token_bearer:
        token = token_bearer.credentials
    elif token_oauth:
        token = token_oauth

    if token is None:
        return None

    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
        if user_id is None:
            return None
    except Exception:
        return None

    stmt = (
        select(UserDB)
        .options(selectinload(UserDB.group), selectinload(UserDB.profile))
        .where(UserDB.id == int(user_id))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user and not user.is_active:
        return None

    return user


async def get_current_user(
    token_oauth: Annotated[str | None, Depends(oauth2_scheme)],
    token_bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    jwt_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
) -> UserDB:
    """
        Mandatory authentication dependency.

        Extracts the user from the request token.
        :raises HTTPException 401: If the token is invalid or the user is not found.
    """
    user = await _get_user_from_request(token_oauth, token_bearer, db, jwt_manager)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_optional(
    token_oauth: Annotated[str | None, Depends(oauth2_scheme)],
    token_bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    jwt_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
) -> UserDB | None:
    """
        Optional authentication dependency.
        Returns the User object if a valid token is present, otherwise returns None.
    """
    return await _get_user_from_request(token_oauth, token_bearer, db, jwt_manager)


class RoleChecker:
    """
        Authorization dependency to enforce role-based access control (RBAC).

        Checks if the authenticated user belongs to one of the allowed groups.
        :raises HTTPException 403: If the user does not have the required role.
    """
    def __init__(self, allowed_roles: list[UserGroupEnum]):
        """Initialize with a list of roles permitted to access the resource."""
        self.allowed_roles = allowed_roles

    def __call__(self, user: Annotated[UserDB, Depends(get_current_user)]) -> UserDB:
        """Validates the user's role against the allowed list."""
        if user.group.name not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user


allow_admin = RoleChecker([UserGroupEnum.ADMIN])
allow_moderator = RoleChecker([UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN])
