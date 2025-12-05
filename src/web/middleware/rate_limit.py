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
"""

import logging
import time
from typing import Optional, Callable

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from redis import Redis
from redis.exceptions import RedisError

from src.config.auth_config import auth_settings
from src.services.exceptions import RateLimitExceededError

logger = logging.getLogger(__name__)


def get_rate_limit_key(request: Request) -> str:
    """Extract rate limit key from request.

    Uses authenticated user ID when available for more accurate rate limiting.
    Falls back to IP address for unauthenticated requests.

    Args:
        request: FastAPI Request object

    Returns:
        Rate limit key string (user ID or IP address)

    Example:
        >>> key = get_rate_limit_key(request)
        >>> # Returns "user:123" if authenticated
        >>> # Returns "ip:192.168.1.100" if not authenticated
    """
    # Try to get authenticated user from request state
    # This assumes your auth middleware sets request.state.user
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    # Try to get user from custom header (for testing)
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return f"user:{user_id}"

    # Fall back to IP address
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

    Returns:
        Configured Limiter instance

    Example:
        >>> limiter = create_limiter()
        >>> @limiter.limit("10/minute")
        >>> async def my_endpoint(request: Request):
        >>>     return {"status": "ok"}
    """
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


# Global limiter instance
limiter = create_limiter()


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


def api_limit() -> str:
    """Rate limit for general API endpoints (100 requests per minute).

    Example:
        >>> @app.get("/api/prompts")
        >>> @limiter.limit(api_limit)
        >>> async def get_prompts(request: Request):
        >>>     return {"prompts": []}
    """
    return "100/minute"


def admin_limit() -> str:
    """Rate limit for admin endpoints (200 requests per minute).

    Example:
        >>> @app.get("/api/admin/users")
        >>> @limiter.limit(admin_limit)
        >>> async def get_users(request: Request):
        >>>     return {"users": []}
    """
    return "200/minute"


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
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

    # Build response with proper headers
    response = JSONResponse(
        status_code=429,
        content=error.to_dict(),
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(getattr(exc, "limit", "unknown")),
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
    "api_limit",
    "admin_limit",
    "rate_limit_exceeded_handler",
    "add_rate_limit_headers",
    "get_auth_login_limit",
    "get_auth_register_limit",
    "get_password_reset_limit",
]
