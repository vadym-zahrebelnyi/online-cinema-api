class AccountBaseException(Exception):
    pass


class UserAlreadyExistsException(AccountBaseException):
    pass


class UserNotFoundException(AccountBaseException):
    pass


class InvalidCredentialsException(AccountBaseException):
    pass


class AccountNotActiveException(AccountBaseException):
    pass


class InvalidTokenException(AccountBaseException):
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
