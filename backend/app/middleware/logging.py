"""Structured JSON logging middleware."""
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Attach request_id to structlog context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        logger.info(
            "HTTP request",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None,
        )

        structlog.contextvars.unbind_contextvars("request_id")
        response.headers["X-Request-ID"] = request_id
        return response
