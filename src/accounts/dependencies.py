from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.exceptions import InvalidTokenException
from src.accounts.services import AuthService
from src.core.database import get_db
from src.core.settings import Settings, get_settings

# from src.notifications import EmailSenderInterface
from src.security.interfaces import JWTAuthManagerInterface
from src.security.token_manager import JWTAuthManager


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
) -> AuthService:
    return AuthService(db=db, settings=settings, jwt_manager=jwt_manager)


# async def get_current_user_id(
#     token: Annotated[str, Depends(get_token)],
#     jwt_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
# ) -> int:
#     try:
#         payload = jwt_manager.decode_access_token(token)
#         user_id = payload.get("user_id")
#         if user_id is None:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Token payload is missing user_id",
#             )
#         return user_id
#     except Exception:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid or expired access token",
#         )

security = HTTPBearer()


async def get_current_user_id(
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
) -> int:
    try:
        payload = jwt_manager.decode_access_token(token.credentials)
        user_id = payload.get("user_id")
        if user_id is None:
            raise InvalidTokenException()
        return user_id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
