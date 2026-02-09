from fastapi import HTTPException


class AppException(HTTPException):
    """Base class for business exceptions."""

    def __init__(self, status_code: int = 400, detail: str = "Application error"):
        super().__init__(status_code=status_code, detail=detail)


class MovieNotFoundException(AppException):
    def __init__(self):
        super().__init__(status_code=404, detail="Movie not found")


class MovieHasOrdersException(AppException):
    def __init__(self):
        super().__init__(
            status_code=400, detail="Cannot delete movie with existing orders"
        )


class GenreNotFoundException(AppException):
    def __init__(self):
        super().__init__(status_code=404, detail="Genre not found")


class GenreInUseException(AppException):
    def __init__(self):
        super().__init__(
            status_code=400, detail="Genre is used by movies and cannot be deleted"
        )


class CertificationNotFoundException(AppException):
    def __init__(self):
        super().__init__(status_code=404, detail="Certification not found")


class CertificationInUseException(AppException):
    def __init__(self):
        super().__init__(
            status_code=400,
            detail="Certification is used by movies and cannot be deleted",
        )
