"""
Custom exception hierarchy for the application.

Instead of raising raw HTTPException everywhere (which mixes "what went
wrong" with "how it's presented over HTTP"), route/service code raises one
of these domain-specific exceptions. app/core/error_handlers.py then maps
each exception type to a consistent JSON error response and the right
HTTP status code.

This separation matters once the RAG/agent logic is added later: a
"RetrievalTimeoutError" or "TrustScoreUnavailableError" can be raised deep
inside a service function without that function needing to know anything
about FastAPI or HTTP status codes at all.
"""


class AppError(Exception):
    """Base class for all application-specific errors."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str = "An unexpected error occurred."):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"

    def __init__(self, message: str = "Requested resource was not found."):
        super().__init__(message)


class ValidationError(AppError):
    status_code = 422
    error_code = "validation_error"

    def __init__(self, message: str = "Request validation failed."):
        super().__init__(message)


class DatabaseConnectionError(AppError):
    status_code = 503
    error_code = "database_unavailable"

    def __init__(self, message: str = "Database is currently unavailable."):
        super().__init__(message)


class CacheConnectionError(AppError):
    status_code = 503
    error_code = "cache_unavailable"

    def __init__(self, message: str = "Cache service is currently unavailable."):
        super().__init__(message)


class ServiceUnavailableError(AppError):
    status_code = 503
    error_code = "service_unavailable"

    def __init__(self, message: str = "A required upstream service is unavailable."):
        super().__init__(message)
