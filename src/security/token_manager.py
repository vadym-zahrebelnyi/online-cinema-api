from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import ExpiredSignatureError, JWTError, jwt

from src.accounts.exceptions import InvalidTokenError, TokenExpiredError
from src.security.interfaces import JWTAuthManagerInterface


class JWTAuthManager(JWTAuthManagerInterface):
    """
    Implementation of the JWT authentication manager.

    This class handles the lifecycle of JSON Web Tokens (JWTs), including
    generation, signing, decoding, and validation. It supports distinct
    secrets for access and refresh tokens to enhance security.

    Attributes:
        _ACCESS_KEY_TIMEDELTA_MINUTES (int): Default lifespan of an access token (60 min).
        _REFRESH_KEY_TIMEDELTA_MINUTES (int): Default lifespan of a refresh token (7 days).
    """

    _ACCESS_KEY_TIMEDELTA_MINUTES = 60
    _REFRESH_KEY_TIMEDELTA_MINUTES = 60 * 24 * 7

    def __init__(
        self,
        secret_key_access: str,
        secret_key_refresh: str,
        algorithm: str = "HS256",
    ):
        """
        Initialize the JWT manager with cryptographic keys.

        Args:
            secret_key_access (str): Secret key used to sign access tokens.
            secret_key_refresh (str): Secret key used to sign refresh tokens.
            algorithm (str): The signing algorithm (default: HS256).
        """
        self._secret_key_access = secret_key_access
        self._secret_key_refresh = secret_key_refresh
        self._algorithm = algorithm

    def _create_token(
        self, data: dict, secret_key: str, expires_delta: timedelta
    ) -> str:
        """
        Internal helper to encode a payload into a JWT string.

        Args:
            data (dict): Claims to include in the token payload.
            secret_key (str): The key used for signing.
            expires_delta (timedelta): Duration until the token expires.

        Returns:
            str: The encoded JWT string.
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, secret_key, algorithm=self._algorithm)

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Generate a short-lived access token.

        Args:
            data (dict): Payload data (e.g., user ID).
            expires_delta (Optional[timedelta]): Custom expiration time.
                If None, defaults to _ACCESS_KEY_TIMEDELTA_MINUTES.

        Returns:
            str: Signed access token.
        """
        return self._create_token(
            data,
            self._secret_key_access,
            expires_delta or timedelta(minutes=self._ACCESS_KEY_TIMEDELTA_MINUTES),
        )

    def create_refresh_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Generate a long-lived refresh token.

        Args:
            data (dict): Payload data.
            expires_delta (Optional[timedelta]): Custom expiration time.
                If None, defaults to _REFRESH_KEY_TIMEDELTA_MINUTES.

        Returns:
            str: Signed refresh token.
        """
        return self._create_token(
            data,
            self._secret_key_refresh,
            expires_delta or timedelta(minutes=self._REFRESH_KEY_TIMEDELTA_MINUTES),
        )

    def decode_access_token(self, token: str) -> dict:
        """
        Decode and validate an access token.

        Args:
            token (str): The encoded JWT string.

        Returns:
            dict: The decoded payload.

        Raises:
            TokenExpiredError: If the token's 'exp' claim is in the past.
            InvalidTokenError: If the signature is invalid or the token is malformed.
        """
        try:
            return jwt.decode(
                token,
                self._secret_key_access,
                algorithms=[self._algorithm],
            )
        except ExpiredSignatureError:
            raise TokenExpiredError()
        except JWTError:
            raise InvalidTokenError()

    def decode_refresh_token(self, token: str) -> dict:
        """
        Decode and validate a refresh token.

        Uses the refresh secret key for validation.

        Args:
            token (str): The encoded JWT string.

        Returns:
            dict: The decoded payload.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid.
        """
        try:
            return jwt.decode(
                token,
                self._secret_key_refresh,
                algorithms=[self._algorithm],
            )
        except ExpiredSignatureError:
            raise TokenExpiredError()
        except JWTError:
            raise InvalidTokenError()

    def verify_refresh_token_or_raise(self, token: str) -> None:
        """
        Ensure the refresh token is valid without returning its payload.

        Useful for middleware or checks where the data itself isn't needed immediately.

        Args:
            token (str): The token to verify.

        Raises:
            TokenExpiredError: If expired.
            InvalidTokenError: If invalid.
        """
        self.decode_refresh_token(token)

    def verify_access_token_or_raise(self, token: str) -> None:
        """
        Ensure the access token is valid without returning its payload.

        Args:
            token (str): The token to verify.

        Raises:
            TokenExpiredError: If expired.
            InvalidTokenError: If invalid.
        """
        self.decode_access_token(token)
