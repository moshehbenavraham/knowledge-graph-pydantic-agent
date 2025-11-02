"""
Middleware stack for FastAPI application.

Includes correlation IDs, timing, error handling, compression, and rate limiting.
"""

import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

from src.api.models import ErrorDetail, ErrorResponse

# Context variable for correlation ID
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")

logger = structlog.get_logger()


# Create a namespace for request_logging (for test mocking)
class RequestLoggingNamespace:
    logger = logger


request_logging = RequestLoggingNamespace()


def get_correlation_id() -> str:
    """Get current correlation ID from context."""
    return correlation_id_ctx.get()


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to requests.

    Extracts or generates correlation ID and propagates through logging context.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID."""
        # Extract or generate correlation ID
        correlation_id = request.headers.get(
            "X-Correlation-ID", request.headers.get("X-Request-ID", str(uuid.uuid4()))
        )

        # Set in context variable for access throughout request
        correlation_id_ctx.set(correlation_id)

        # Bind to structured logging
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        # Clear context
        structlog.contextvars.clear_contextvars()

        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request timing.

    Adds X-Process-Time header with request duration in milliseconds.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with timing."""
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate duration
        process_time = (time.perf_counter() - start_time) * 1000

        # Add timing header
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        # Log slow requests (>1000ms)
        if process_time > 1000:
            logger.warning(
                "slow_request",
                path=request.url.path,
                method=request.method,
                duration_ms=process_time,
            )

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for standardized error handling.

    Catches exceptions and returns structured error responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error handling."""
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Log exception with context
            logger.exception(
                "request_error",
                path=request.url.path,
                method=request.method,
                error=str(exc),
            )

            # Determine status code
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_code = "internal_error"
            error_message = "An internal error occurred"

            # Check for known exception types
            if hasattr(exc, "status_code"):
                status_code = exc.status_code

            if hasattr(exc, "detail"):
                error_message = exc.detail

            # Create structured error response
            error_detail = ErrorDetail(
                code=error_code,
                message=error_message,
                details={"exception_type": type(exc).__name__},
            )

            error_response = ErrorResponse(error=error_detail, request_id=get_correlation_id())

            return JSONResponse(
                status_code=status_code,
                content=error_response.model_dump(),
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers.

    Adds common security headers to all responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with security headers."""
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class CompressionMiddleware(GZipMiddleware):
    """
    Middleware for response compression.

    Extends GZipMiddleware with configuration.
    """

    def __init__(self, app, minimum_size: int = 1000, compresslevel: int = 5):
        """
        Initialize compression middleware.

        Args:
            app: ASGI application
            minimum_size: Minimum response size to compress (bytes)
            compresslevel: Compression level (1-9, default 5)
        """
        super().__init__(app, minimum_size=minimum_size, compresslevel=compresslevel)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging.

    Logs all requests with relevant metadata.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging."""
        # Extract request info
        client_host = request.client.host if request.client else "unknown"

        # Log request
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client=client_host,
            user_agent=request.headers.get("user-agent", "unknown"),
        )

        # Process request
        response = await call_next(request)

        # Log response
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Basic rate limiting middleware.

    Implements simple in-memory rate limiting per IP address.
    For production, use Redis-backed rate limiting.
    """

    def __init__(self, app, requests_per_minute: int = 60, burst_size: int = 10):
        """
        Initialize rate limit middleware.

        Args:
            app: ASGI application
            requests_per_minute: Max requests per minute per IP
            burst_size: Max burst requests
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self._client_requests: dict = {}
        self._last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for health endpoints
        if request.url.path.startswith("/health"):
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Cleanup old entries every 60 seconds
        current_time = time.time()
        if current_time - self._last_cleanup > 60:
            self._cleanup_old_entries(current_time)
            self._last_cleanup = current_time

        # Check rate limit
        if not self._check_rate_limit(client_ip, current_time):
            logger.warning(
                "rate_limit_exceeded",
                client=client_ip,
                path=request.url.path,
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests",
                    }
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self._get_remaining_requests(client_ip, current_time)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response

    def _check_rate_limit(self, client_ip: str, current_time: float) -> bool:
        """Check if client is within rate limit."""
        if client_ip not in self._client_requests:
            self._client_requests[client_ip] = []

        # Remove requests older than 1 minute
        cutoff_time = current_time - 60
        self._client_requests[client_ip] = [
            ts for ts in self._client_requests[client_ip] if ts > cutoff_time
        ]

        # Check if under limit
        if len(self._client_requests[client_ip]) >= self.requests_per_minute:
            return False

        # Add current request
        self._client_requests[client_ip].append(current_time)
        return True

    def _get_remaining_requests(self, client_ip: str, current_time: float) -> int:
        """Get remaining requests for client."""
        if client_ip not in self._client_requests:
            return self.requests_per_minute

        cutoff_time = current_time - 60
        recent_requests = [ts for ts in self._client_requests[client_ip] if ts > cutoff_time]

        return max(0, self.requests_per_minute - len(recent_requests))

    def _cleanup_old_entries(self, current_time: float):
        """Remove old entries from rate limit tracking."""
        cutoff_time = current_time - 120  # Keep 2 minutes of history

        for client_ip in list(self._client_requests.keys()):
            self._client_requests[client_ip] = [
                ts for ts in self._client_requests[client_ip] if ts > cutoff_time
            ]

            # Remove empty entries
            if not self._client_requests[client_ip]:
                del self._client_requests[client_ip]
