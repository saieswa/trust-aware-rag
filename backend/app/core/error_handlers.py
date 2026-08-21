"""
Global exception handlers.

Registered once in app/main.py via `register_exception_handlers(app)`. These
turn any raised exception into a consistent `ErrorResponse` JSON body,
instead of leaking raw stack traces or FastAPI's default (inconsistent)
error formats to the client.

Three layers are handled:
1. Our own `AppError` subclasses (app/core/exceptions.py) — expected,
   domain-specific errors with a known status code.
2. FastAPI/Starlette's built-in `HTTPException` and request validation
   errors — so third-party/framework errors still come back in our shape.
3. Anything else (`Exception`) — an unexpected bug. We log the full
   traceback server-side but only ever return a generic message to the
   client, so internal details never leak.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.schemas.common import ErrorResponse


def _error_body(error_code: str, message: str, details: dict | None = None) -> dict:
    return ErrorResponse(error_code=error_code, message=message, details=details).model_dump()


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            f"AppError on {request.method} {request.url.path}: "
            f"{exc.error_code} — {exc.message}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error_code, exc.message),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        logger.warning(
            f"HTTPException on {request.method} {request.url.path}: "
            f"{exc.status_code} — {exc.detail}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("http_error", str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(
            f"Validation error on {request.method} {request.url.path}: {exc.errors()}"
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                "validation_error",
                "Request validation failed.",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Full traceback goes to the logs; the client only ever sees a
        # generic message. This prevents leaking internals (stack traces,
        # file paths, DB connection strings, etc.) in API responses.
        logger.exception(
            f"Unhandled exception on {request.method} {request.url.path}: {exc}"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "internal_error",
                "An unexpected error occurred. Please try again later.",
            ),
        )
