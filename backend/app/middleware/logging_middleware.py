"""
Request logging middleware.

Logs one line per request: method, path, status code, and how long it
took. Also attaches a unique `X-Request-ID` header to every response, which
becomes essential later for tracing a single question through the full
agent pipeline (retriever → critic → synthesizer → verifier) across logs.
"""

import time
import uuid

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        logger.bind(request_id=request_id).info(
            f"→ {request.method} {request.url.path}"
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.bind(request_id=request_id).exception(
                f"✗ {request.method} {request.url.path} failed after {duration_ms:.1f}ms"
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.bind(request_id=request_id).info(
            f"← {request.method} {request.url.path} "
            f"status={response.status_code} took={duration_ms:.1f}ms"
        )
        response.headers["X-Request-ID"] = request_id
        return response
