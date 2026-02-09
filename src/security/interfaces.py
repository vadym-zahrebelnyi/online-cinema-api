from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Optional


class JWTAuthManagerInterface(ABC):
    """
    Abstract Base Class defining the contract for JWT (JSON Web Token) management.

    This interface enforces a standard structure for token generation, decoding,
    and validation. Concrete implementations should handle the specific cryptographic
    signing (e.g., HS256, RS256) and secret key management.
    """

    @abstractmethod
    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Generate a new short-lived access token.

        Args:
            data (dict): The payload claims to encode within the token (e.g., user_id, sub).
            expires_delta (Optional[timedelta]): Custom expiration duration. If not provided,
                the default configuration setting should be used.

        Returns:
            str: The encoded JWT string.
        """
        pass

    @abstractmethod
    def create_refresh_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Generate a new long-lived refresh token.

        Used to obtain new access tokens without re-entering credentials.

        Args:
            data (dict): The payload claims to encode within the token.
            expires_delta (Optional[timedelta]): Custom expiration duration.

        Returns:
            str: The encoded JWT string.
        """
        pass

    @abstractmethod
    def decode_access_token(self, token: str) -> dict:
        """
        Decode an access token to retrieve its payload.

        Args:
            token (str): The encoded JWT string.

        Returns:
            dict: The decoded payload claims.

        Raises:
            Exception: If decoding fails (e.g., invalid format).
        """
        pass

    @abstractmethod
    def decode_refresh_token(self, token: str) -> dict:
        """
        Decode a refresh token to retrieve its payload.

        Args:
            token (str): The encoded JWT string.

        Returns:
            dict: The decoded payload claims.

        Raises:
            Exception: If decoding fails (e.g., invalid format).
        """
        pass

    @abstractmethod
    def verify_refresh_token_or_raise(self, token: str) -> None:
        """
        Validate the signature and expiration of a refresh token.

        Args:
            token (str): The token to verify.

        Raises:
            HTTPException: If the token is expired, invalid, or the signature does not match.
        """
        pass

    @abstractmethod
    def verify_access_token_or_raise(self, token: str) -> None:
        """
        Validate the signature and expiration of an access token.

        Args:
            token (str): The token to verify.

        Raises:
            HTTPException: If the token is expired, invalid, or the signature does not match.
        """
        pass
