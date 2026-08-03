# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Rate limiting middleware for PromptVault.

This module provides comprehensive rate limiting functionality using slowapi
with Redis backend. It protects authentication endpoints from brute force
attacks and general API endpoints from abuse.

Features:
    - Redis-backed rate limiting with persistence
    - IP-based rate limiting by default
    - User-based rate limiting when authenticated
    - Graceful fallback if Redis is unavailable
    - X-RateLimit-* headers in responses
    - 429 Too Many Requests with Retry-After header
    - Pre-configured limiters for different endpoint types
    - Dynamic disable via DISABLE_RATE_LIMITING environment variable

Integration with FastAPI:
    >>> from fastapi import FastAPI, Request
    >>> from src.web.middleware.rate_limit import limiter, rate_limit_exceeded_handler
    >>> from slowapi import _rate_limit_exceeded_handler
    >>> from slowapi.errors import RateLimitExceeded
    >>>
    >>> app = FastAPI()
    >>> app.state.limiter = limiter
    >>> app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    >>>
    >>> # Use in routes
    >>> @app.get("/api/auth/login")
    >>> @limiter.limit("5/minute")
    >>> async def login(request: Request):
    >>>     return {"status": "ok"}

Environment Variables:
    REDIS_URL: Redis connection URL (default: redis://localhost:6379/0)
    RATE_LIMIT_LOGIN_ATTEMPTS: Login attempts per window (default: 5)
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: Login window in seconds (default: 900)
    RATE_LIMIT_REGISTER_ATTEMPTS: Registration attempts per window (default: 3)
    RATE_LIMIT_REGISTER_WINDOW_SECONDS: Registration window in seconds (default: 3600)
    RATE_LIMIT_PASSWORD_RESET_ATTEMPTS: Password reset attempts per window (default: 3)
    RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS: Password reset window in seconds (default: 3600)
    RATE_LIMIT_READ_ATTEMPTS / RATE_LIMIT_READ_WINDOW_SECONDS: Read bucket (default: 300 / 60)
    RATE_LIMIT_WRITE_ATTEMPTS / RATE_LIMIT_WRITE_WINDOW_SECONDS: Write bucket (default: 60 / 60)
    RATE_LIMIT_EXPENSIVE_ATTEMPTS / RATE_LIMIT_EXPENSIVE_WINDOW_SECONDS: Expensive bucket (default: 10 / 60)
    RATE_LIMIT_BULK_ATTEMPTS / RATE_LIMIT_BULK_WINDOW_SECONDS: Bulk bucket (default: 5 / 60)
    DISABLE_RATE_LIMITING: Set to "true" to disable rate limiting (development only)
"""

import logging
import os
import time
from typing import Optional, Callable
from functools import wraps

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from redis import Redis
from redis.exceptions import RedisError

from src.config.auth_config import auth_settings
from src.services.exceptions import RateLimitExceededError

logger = logging.getLogger(__name__)

_TRUE_VALUES = ("true", "1", "yes", "y", "on")
_FALSE_VALUES = ("false", "0", "no", "n", "off")


def _parse_bool_env(name: str) -> Optional[bool]:
    """Parse an environment variable as a boolean.

    Returns:
        True/False when the variable is present and parseable, otherwise None.
    """
    raw = os.getenv(name)
    if raw is None:
        return None
    value = raw.strip().lower()
    if not value:
        return None
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    return None


def is_rate_limiting_disabled() -> bool:
    """Decide whether rate limiting should be disabled.

    Precedence:
      1. `DISABLE_RATE_LIMITING` (explicit on/off)
      2. `.env` / settings value (if present)
      3. `ENVIRONMENT` in development/testing (implicit disable)

    This keeps production safe by requiring an explicit opt-out.
    """
    explicit = _parse_bool_env("DISABLE_RATE_LIMITING")
    if explicit is not None:
        return explicit

    # Support `.env` without requiring a separate dotenv loader: auth_settings
    # reads from env_file=".env" (and is overridden by real env vars).
    try:
        if bool(getattr(auth_settings, "disable_rate_limiting", False)):
            return True
    except Exception:
        # If settings initialization fails for any reason, fall back to env vars.
        pass

    env = os.getenv("ENVIRONMENT") or getattr(auth_settings, "environment", None)
    if env and env.strip().lower() in (
        "development",
        "dev",
        "local",
        "testing",
        "test",
    ):
        return True

    return False


def _jwt_subject_from_request(request: Request) -> Optional[str]:
    """Extract the JWT subject (user id) from a request without a DB hit.

    Decodes the ``access_token`` from either the ``Authorization: Bearer``
    header or the ``access_token`` cookie, mirroring the stateless decode used
    by the logging middleware. Any decode failure (missing/invalid/expired
    token) returns ``None`` so the caller can fall back to IP-based keying.

    Args:
        request: FastAPI Request object

    Returns:
        The ``sub`` claim (user id) as a string, or None if unavailable.
    """
    # Import lazily to avoid a circular import at module load time.
    from src.services.auth.jwt_service import JWTService

    try:
        jwt_service = JWTService(auth_settings)
    except Exception:  # pragma: no cover - misconfiguration guard
        return None

    token: Optional[str] = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        return None

    try:
        payload = jwt_service.validate_access_token(token)
    except Exception:
        # Invalid or expired token — degrade to IP-based keying.
        return None

    sub = payload.get("sub")
    return str(sub) if sub else None


def get_rate_limit_key(request: Request) -> str:
    """Extract rate limit key from request.

    Uses the authenticated user ID when available for per-user rate limiting,
    falling back to the client IP address for anonymous requests. The user id
    is resolved from ``request.state.user`` (if any middleware set it), then a
    test-only ``X-User-ID`` header, then a stateless JWT decode, and finally IP.

    Args:
        request: FastAPI Request object

    Returns:
        Rate limit key string (``user:<id>`` or ``ip:<addr>``)

    Example:
        >>> key = get_rate_limit_key(request)
        >>> # Returns "user:123" if authenticated
        >>> # Returns "ip:192.168.1.100" if not authenticated
    """
    # Prefer an authenticated user object if some middleware populated it.
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    # Test hook: allow forcing a user key via header.
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return f"user:{user_id}"

    # Resolve the JWT subject statelessly (header or cookie).
    sub = _jwt_subject_from_request(request)
    if sub:
        return f"user:{sub}"

    # Fall back to IP address for anonymous requests.
    ip = get_remote_address(request)
    return f"ip:{ip}"


def create_redis_client() -> Optional[Redis]:
    """Create Redis client for rate limiting storage.

    Attempts to connect to Redis using configuration from auth_settings.
    Returns None if connection fails, allowing graceful fallback.

    Returns:
        Redis client instance or None if connection fails

    Example:
        >>> redis_client = create_redis_client()
        >>> if redis_client:
        >>>     redis_client.ping()  # Test connection
    """
    try:
        redis_client = Redis(
            host=auth_settings.redis_host,
            port=auth_settings.redis_port,
            db=auth_settings.redis_db,
            password=auth_settings.redis_password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        # Test connection
        redis_client.ping()
        logger.info(
            f"Successfully connected to Redis at {auth_settings.redis_host}:{auth_settings.redis_port}"
        )
        return redis_client
    except RedisError as e:
        logger.warning(
            f"Failed to connect to Redis for rate limiting: {e}. "
            "Rate limiting will be disabled (fallback mode)."
        )
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error connecting to Redis: {e}. "
            "Rate limiting will be disabled (fallback mode)."
        )
        return None


def create_limiter() -> Limiter:
    """Create and configure slowapi Limiter with Redis backend.

    Initializes limiter with Redis storage if available, otherwise falls back
    to in-memory storage (which won't persist across requests in production).

    Can be disabled for development by setting DISABLE_RATE_LIMITING=true.

    Returns:
        Configured Limiter instance

    Example:
        >>> limiter = create_limiter()
        >>> @limiter.limit("10/minute")
        >>> async def my_endpoint(request: Request):
        >>>     return {"status": "ok"}
    """
    if is_rate_limiting_disabled():
        logger.warning(
            "⚠️  RATE LIMITING IS DISABLED "
            f"(DISABLE_RATE_LIMITING={os.getenv('DISABLE_RATE_LIMITING')!r}, "
            f"ENVIRONMENT={os.getenv('ENVIRONMENT')!r}). "
            "This is only safe for development environments. "
            "Do NOT use in production!"
        )
        # Create a dummy limiter with unlimited storage
        # Use in-memory storage but with very high limits
        limiter = Limiter(
            key_func=get_rate_limit_key,
            storage_uri="memory://",
            default_limits=[
                "10000000/minute"
            ],  # Very high limit effectively disables limiting
            headers_enabled=False,
            strategy="fixed-window",
            swallow_errors=True,
        )
        return limiter

    redis_client = create_redis_client()

    if redis_client:
        logger.info("Initializing rate limiter with Redis backend")
        storage_uri = auth_settings.redis_url
    else:
        logger.warning(
            "Redis not available. Rate limiting will use in-memory storage "
            "(not suitable for production with multiple workers)."
        )
        storage_uri = "memory://"

    # Create limiter with custom key function
    limiter = Limiter(
        key_func=get_rate_limit_key,
        storage_uri=storage_uri,
        default_limits=["100/minute"],  # Default rate limit for all endpoints
        headers_enabled=True,  # Enable X-RateLimit-* headers
        strategy="fixed-window",  # Use fixed window strategy
        swallow_errors=True,  # Don't crash on storage errors
    )

    return limiter


class DynamicLimiter:
    """Wrapper around Limiter that dynamically enables/disables rate limiting.

    This class allows rate limiting to be disabled at runtime (e.g., for tests)
    while still supporting the decorator syntax @limiter.limit("X/minute").
    When DISABLE_RATE_LIMITING is true, decorators become no-ops.
    """

    def __init__(self):
        """Initialize the dynamic limiter."""
        self._actual_limiter = create_limiter()

    def _is_disabled(self) -> bool:
        """Check if rate limiting is disabled."""
        return is_rate_limiting_disabled()

    def limit(self, limit_string: str):
        """Decorator for rate limiting that respects DISABLE_RATE_LIMITING.

        Args:
            limit_string: Rate limit string (e.g., "5/minute")

        Returns:
            Decorator function
        """

        def decorator(func):
            if self._is_disabled():
                # If rate limiting is disabled, return the function unchanged
                return func
            else:
                # Apply the actual rate limit decorator
                return self._actual_limiter.limit(limit_string)(func)

        return decorator

    def __getattr__(self, name):
        """Proxy other attributes to the actual limiter."""
        return getattr(self._actual_limiter, name)


# Global limiter instance (uses DynamicLimiter)
limiter = DynamicLimiter()


def get_auth_login_limit() -> str:
    """Get rate limit string for login endpoint.

    Returns:
        Rate limit string in format "attempts/window"

    Example:
        >>> limit = get_auth_login_limit()
        >>> # Returns "5/15minutes" (5 attempts per 15 minutes)
    """
    attempts = auth_settings.rate_limit_login_attempts
    window_seconds = auth_settings.rate_limit_login_window_seconds

    # Convert seconds to appropriate time unit
    if window_seconds < 60:
        return f"{attempts}/{window_seconds}seconds"
    elif window_seconds < 3600:
        minutes = window_seconds // 60
        return f"{attempts}/{minutes}minutes" if minutes > 1 else f"{attempts}/minute"
    else:
        hours = window_seconds // 3600
        return f"{attempts}/{hours}hour{hours > 1 and 's' or ''}"


def get_auth_register_limit() -> str:
    """Get rate limit string for registration endpoint.

    Returns:
        Rate limit string in format "attempts/window"

    Example:
        >>> limit = get_auth_register_limit()
        >>> # Returns "3/1hour" (3 attempts per hour)
    """
    attempts = auth_settings.rate_limit_register_attempts
    window_seconds = auth_settings.rate_limit_register_window_seconds

    if window_seconds < 60:
        return f"{attempts}/{window_seconds}seconds"
    elif window_seconds < 3600:
        minutes = window_seconds // 60
        return f"{attempts}/{minutes}minutes" if minutes > 1 else f"{attempts}/minute"
    else:
        hours = window_seconds // 3600
        return f"{attempts}/hour" if hours == 1 else f"{attempts}/{hours}hours"


def get_password_reset_limit() -> str:
    """Get rate limit string for password reset endpoint.

    Returns:
        Rate limit string in format "attempts/window"

    Example:
        >>> limit = get_password_reset_limit()
        >>> # Returns "3/1hour" (3 attempts per hour)
    """
    attempts = auth_settings.rate_limit_password_reset_attempts
    window_seconds = auth_settings.rate_limit_password_reset_window_seconds

    if window_seconds < 60:
        return f"{attempts}/{window_seconds}seconds"
    elif window_seconds < 3600:
        minutes = window_seconds // 60
        return f"{attempts}/{minutes}minutes" if minutes > 1 else f"{attempts}/minute"
    else:
        hours = window_seconds // 3600
        return f"{attempts}/{hours}hours" if hours > 1 else f"{attempts}/hour"


def _format_limit(attempts: int, window_seconds: int) -> str:
    """Format an attempts/window pair as a slowapi limit string.

    Chooses the largest whole time unit (hour/minute/second) that the window
    divides into, mirroring the auth limit builders above.

    Args:
        attempts: Number of allowed requests in the window.
        window_seconds: Length of the window in seconds.

    Returns:
        A slowapi-compatible limit string, e.g. "60/minute" or "10/2minutes".
    """
    if window_seconds < 60:
        return f"{attempts}/{window_seconds}seconds"
    if window_seconds < 3600:
        minutes = window_seconds // 60
        return f"{attempts}/{minutes}minutes" if minutes > 1 else f"{attempts}/minute"
    hours = window_seconds // 3600
    return f"{attempts}/hour" if hours == 1 else f"{attempts}/{hours}hours"


def get_read_limit() -> str:
    """Get the rate limit string for read endpoints (default 300/minute)."""
    return _format_limit(
        auth_settings.rate_limit_read_attempts,
        auth_settings.rate_limit_read_window_seconds,
    )


def get_write_limit() -> str:
    """Get the rate limit string for write endpoints (default 60/minute)."""
    return _format_limit(
        auth_settings.rate_limit_write_attempts,
        auth_settings.rate_limit_write_window_seconds,
    )


def get_expensive_limit() -> str:
    """Get the rate limit string for expensive ops (default 10/minute)."""
    return _format_limit(
        auth_settings.rate_limit_expensive_attempts,
        auth_settings.rate_limit_expensive_window_seconds,
    )


def get_bulk_limit() -> str:
    """Get the rate limit string for bulk ops (default 5/minute)."""
    return _format_limit(
        auth_settings.rate_limit_bulk_attempts,
        auth_settings.rate_limit_bulk_window_seconds,
    )


# Pre-configured rate limit decorators for common use cases
def auth_login_limit() -> str:
    """Rate limit for login endpoints (5 attempts per 15 minutes by default).

    Example:
        >>> @app.post("/api/auth/login")
        >>> @limiter.limit(auth_login_limit)
        >>> async def login(request: Request):
        >>>     return {"status": "ok"}
    """
    return get_auth_login_limit()


def auth_register_limit() -> str:
    """Rate limit for registration endpoints (3 attempts per hour by default).

    Example:
        >>> @app.post("/api/auth/register")
        >>> @limiter.limit(auth_register_limit)
        >>> async def register(request: Request):
        >>>     return {"status": "ok"}
    """
    return get_auth_register_limit()


def password_reset_limit() -> str:
    """Rate limit for password reset endpoints (3 attempts per hour by default).

    Example:
        >>> @app.post("/api/auth/password-reset")
        >>> @limiter.limit(password_reset_limit)
        >>> async def reset_password(request: Request):
        >>>     return {"status": "ok"}
    """
    return get_password_reset_limit()


def read_limit() -> str:
    """Rate limit for read endpoints (default 300/minute, configurable).

    Example:
        >>> @app.get("/api/prompts/{prompt_id}")
        >>> @limiter.limit(read_limit)
        >>> async def get_prompt(request: Request):
        >>>     return {"prompt": {}}
    """
    return get_read_limit()


def write_limit() -> str:
    """Rate limit for write endpoints (default 60/minute, configurable).

    Covers create/update/delete/revert of individual resources.

    Example:
        >>> @app.post("/api/prompts")
        >>> @limiter.limit(write_limit)
        >>> async def create_prompt(request: Request):
        >>>     return {"prompt_id": "..."}
    """
    return get_write_limit()


def expensive_limit() -> str:
    """Rate limit for expensive ops (default 10/minute, configurable).

    Covers import/export and backup create/restore/verify.

    Example:
        >>> @app.post("/api/import")
        >>> @limiter.limit(expensive_limit)
        >>> async def import_prompts(request: Request):
        >>>     return {"imported": 0}
    """
    return get_expensive_limit()


def bulk_limit() -> str:
    """Rate limit for bulk ops (default 5/minute, configurable).

    Covers bulk delete, delete-all, and compression.

    Example:
        >>> @app.delete("/api/prompts/bulk")
        >>> @limiter.limit(bulk_limit)
        >>> async def bulk_delete(request: Request):
        >>>     return {"deleted": 0}
    """
    return get_bulk_limit()


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> Response:
    """Custom exception handler for rate limit exceeded errors.

    Converts slowapi RateLimitExceeded to our custom RateLimitExceededError
    with proper HTTP headers and user-friendly error messages.

    Args:
        request: FastAPI Request object
        exc: RateLimitExceeded exception from slowapi

    Returns:
        Response with 429 status code and Retry-After header

    Example:
        >>> app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    """
    from fastapi.responses import JSONResponse

    # Calculate retry_after from rate limit window
    # slowapi provides the limit string like "5 per 15 minutes"
    retry_after = 60  # Default: 1 minute

    try:
        # Try to extract window from exception message
        # Message format: "5 per 15 minutes"
        if hasattr(exc, "limit") and exc.limit:
            limit_str = str(exc.limit)
            if "hour" in limit_str:
                retry_after = 3600
            elif "minute" in limit_str:
                # Extract number of minutes
                parts = limit_str.split()
                for i, part in enumerate(parts):
                    if "minute" in part and i > 0:
                        try:
                            retry_after = int(parts[i - 1]) * 60
                        except (ValueError, IndexError):
                            pass
            elif "second" in limit_str:
                parts = limit_str.split()
                for i, part in enumerate(parts):
                    if "second" in part and i > 0:
                        try:
                            retry_after = int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass
    except Exception as e:
        logger.warning(f"Failed to calculate retry_after from rate limit: {e}")

    # Log rate limit violation
    key = get_rate_limit_key(request)
    logger.warning(
        f"Rate limit exceeded for {key} on {request.url.path}. "
        f"Retry after {retry_after} seconds."
    )

    # Audit-log the threshold breach (actor/endpoint metadata only — no bodies).
    try:
        from src.services.logging_service import logging_service

        logging_service.log_audit_event(
            action="rate_limit.exceeded",
            resource_type="rate_limit",
            resource_id=key,
            status="warning",
            endpoint=str(request.url.path),
            method=request.method,
            retry_after=retry_after,
        )
    except Exception as e:  # pragma: no cover - never let auditing break the 429
        logger.debug(f"Failed to audit-log rate limit breach: {e}")

    # Create custom error with retry_after
    error = RateLimitExceededError(
        message=f"Rate limit exceeded for {request.url.path}",
        user_message="Too many requests. Please slow down and try again later.",
        retry_after=retry_after,
        context={
            "endpoint": str(request.url.path),
            "method": request.method,
            "key": key,
        },
    )

    # Extract the numeric limit for the X-RateLimit-Limit header. slowapi's
    # exc.limit is a Limit wrapper whose .limit is a limits.RateLimitItem with an
    # `.amount`; fall back gracefully rather than leaking a repr like
    # "<slowapi.wrappers.Limit object at 0x...>".
    limit_header = "unknown"
    try:
        exc_limit = getattr(exc, "limit", None)
        rate_item = getattr(exc_limit, "limit", exc_limit)
        amount = getattr(rate_item, "amount", None)
        if amount is not None:
            limit_header = str(amount)
        elif rate_item is not None:
            limit_header = str(rate_item)
    except Exception:  # pragma: no cover - header is best-effort
        pass

    # Build response with proper headers
    response = JSONResponse(
        status_code=429,
        content=error.to_dict(),
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": limit_header,
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time() + retry_after)),
        },
    )

    return response


def add_rate_limit_headers(
    response: Response,
    limit: int,
    remaining: int,
    reset: int,
) -> None:
    """Add X-RateLimit-* headers to response.

    Args:
        response: FastAPI Response object
        limit: Maximum number of requests allowed
        remaining: Number of requests remaining in current window
        reset: Unix timestamp when rate limit resets

    Example:
        >>> response = JSONResponse(content={"status": "ok"})
        >>> add_rate_limit_headers(response, limit=100, remaining=99, reset=int(time.time() + 60))
    """
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset)


# Export all public functions and classes
__all__ = [
    "limiter",
    "get_rate_limit_key",
    "create_limiter",
    "create_redis_client",
    "auth_login_limit",
    "auth_register_limit",
    "password_reset_limit",
    "read_limit",
    "write_limit",
    "expensive_limit",
    "bulk_limit",
    "rate_limit_exceeded_handler",
    "add_rate_limit_headers",
    "get_auth_login_limit",
    "get_auth_register_limit",
    "get_password_reset_limit",
    "get_read_limit",
    "get_write_limit",
    "get_expensive_limit",
    "get_bulk_limit",
]
