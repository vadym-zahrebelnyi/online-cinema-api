class AccountBaseException(Exception):
    """Base exception class for all account-related errors."""
    pass


class UserAlreadyExistsException(AccountBaseException):
    """Raised when an attempt is made to register an email that is already in the database."""
    pass


class UserNotFoundException(AccountBaseException):
    """Raised when a requested user or profile does not exist in the database."""
    pass


class InvalidCredentialsException(AccountBaseException):
    """Raised when the provided email or password during login is incorrect."""
    pass


class AccountNotActiveException(AccountBaseException):
    """Raised when an unverified/inactive user tries to log in or perform restricted actions."""
    pass


class InvalidTokenException(AccountBaseException):
    """Raised when a security token (activation, reset, or refresh) is malformed, expired, or missing."""
    pass


class BaseAppException(Exception):
    """Base exception class for the entire application."""

    pass


class BaseSecurityError(BaseAppException):
    """Base class for security-related errors."""

    pass


class InvalidTokenError(BaseSecurityError):
    """Raised when a provided token is invalid."""

    pass


class TokenExpiredError(BaseSecurityError):
    """Raised when a provided token has expired."""

    pass
