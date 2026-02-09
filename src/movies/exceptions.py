from fastapi import HTTPException


class AppException(HTTPException):
    """Base class for all application-specific exceptions."""
    def __init__(self, status_code: int = 400, detail: str = "Application error"):
        super().__init__(status_code=status_code, detail=detail)


class MovieNotFoundException(AppException):
    """Raised when a movie is not found."""
    def __init__(self):
        super().__init__(status_code=404, detail="Movie not found")


class MovieHasOrdersException(AppException):
    """Raised when deleting a movie that has existing orders."""
    def __init__(self):
        super().__init__(status_code=400, detail="Cannot delete movie with existing orders")


class GenreNotFoundException(AppException):
    """Raised when a genre is not found."""
    def __init__(self):
        super().__init__(status_code=404, detail="Genre not found")


class GenreInUseException(AppException):
    """Raised when a genre is used by movies and cannot be deleted."""
    def __init__(self):
        super().__init__(status_code=400, detail="Genre is used by movies and cannot be deleted")


class CertificationNotFoundException(AppException):
    """Raised when a certification is not found."""
    def __init__(self):
        super().__init__(status_code=404, detail="Certification not found")


class CertificationInUseException(AppException):
    """Raised when a certification is used by movies and cannot be deleted."""
    def __init__(self):
        super().__init__(status_code=400, detail="Certification is used by movies and cannot be deleted")
