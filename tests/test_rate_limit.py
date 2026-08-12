# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for rate limiting middleware.

This module contains unit tests for the rate limiting functionality,
including Redis backend, rate limit key generation, and exception handling.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from src.web.middleware.rate_limit import (
    add_rate_limit_headers,
    auth_login_limit,
    auth_register_limit,
    bulk_limit,
    create_limiter,
    create_redis_client,
    expensive_limit,
    get_auth_login_limit,
    get_auth_register_limit,
    get_password_reset_limit,
    get_rate_limit_key,
    password_reset_limit,
    rate_limit_exceeded_handler,
    read_limit,
    write_limit,
)


class TestRateLimitKey:
    """Tests for rate limit key generation."""

    def test_get_rate_limit_key_with_authenticated_user(self):
        """Should use user ID when user is authenticated."""
        # Create mock request with authenticated user
        request = Mock(spec=Request)
        user = Mock()
        user.id = 123
        request.state = Mock()
        request.state.user = user

        key = get_rate_limit_key(request)
        assert key == "user:123"

    def test_get_rate_limit_key_with_user_header(self):
        """Should use X-User-ID header if present."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = None
        request.headers = {"X-User-ID": "456"}

        key = get_rate_limit_key(request)
        assert key == "user:456"

    def test_get_rate_limit_key_with_ip_fallback(self):
        """Should fall back to IP address when no user is authenticated."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = None
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        with patch("src.web.middleware.rate_limit.get_remote_address") as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.100"
            key = get_rate_limit_key(request)
            assert key == "ip:192.168.1.100"


class TestRedisClient:
    """Tests for Redis client creation."""

    @patch("src.web.middleware.rate_limit.Redis")
    def test_create_redis_client_success(self, mock_redis):
        """Should create Redis client successfully."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        client = create_redis_client()

        assert client is not None
        mock_client.ping.assert_called_once()

    @patch("src.web.middleware.rate_limit.Redis")
    def test_create_redis_client_connection_failure(self, mock_redis):
        """Should return None when Redis connection fails."""
        mock_redis.side_effect = Exception("Connection failed")

        client = create_redis_client()

        assert client is None


class TestRateLimitHelpers:
    """Tests for rate limit helper functions."""

    def test_get_auth_login_limit(self):
        """Should return login rate limit string."""
        limit = get_auth_login_limit()
        # Default: 5 attempts per 15 minutes (900 seconds)
        assert limit == "5/15minutes"

    def test_get_auth_register_limit(self):
        """Should return registration rate limit string."""
        limit = get_auth_register_limit()
        # Default: 3 attempts per 1 hour (3600 seconds)
        assert limit == "3/hour"

    def test_get_password_reset_limit(self):
        """Should return password reset rate limit string."""
        limit = get_password_reset_limit()
        # Default: 3 attempts per 1 hour (3600 seconds)
        assert limit == "3/hour"

    def test_auth_login_limit_callable(self):
        """Should return callable rate limit."""
        limit = auth_login_limit()
        assert isinstance(limit, str)
        assert limit == "5/15minutes"

    def test_auth_register_limit_callable(self):
        """Should return callable rate limit."""
        limit = auth_register_limit()
        assert isinstance(limit, str)
        assert limit == "3/hour"

    def test_password_reset_limit_callable(self):
        """Should return callable rate limit."""
        limit = password_reset_limit()
        assert isinstance(limit, str)
        assert limit == "3/hour"

    def test_read_limit_callable(self):
        """Should return the read-bucket rate limit (default 300/minute)."""
        assert read_limit() == "300/minute"

    def test_write_limit_callable(self):
        """Should return the write-bucket rate limit (default 60/minute)."""
        assert write_limit() == "60/minute"

    def test_expensive_limit_callable(self):
        """Should return the expensive-bucket rate limit (default 10/minute)."""
        assert expensive_limit() == "10/minute"

    def test_bulk_limit_callable(self):
        """Should return the bulk-bucket rate limit (default 5/minute)."""
        assert bulk_limit() == "5/minute"


class TestRateLimitExceptionHandler:
    """Tests for rate limit exception handler."""

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_handler(self):
        """Should return 429 response with proper headers."""
        # Create mock request
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/auth/login"
        request.method = "POST"
        request.state = Mock()
        request.state.user = None
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Create mock exception with mock limit object
        mock_limit = Mock()
        mock_limit.error_message = None
        exc = RateLimitExceeded(limit=mock_limit)
        exc.limit = "5 per 15 minutes"

        with patch("src.web.middleware.rate_limit.get_rate_limit_key") as mock_key:
            mock_key.return_value = "ip:192.168.1.100"

            response = await rate_limit_exceeded_handler(request, exc)

            assert response.status_code == 429
            assert "Retry-After" in response.headers
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers


class TestAddRateLimitHeaders:
    """Tests for adding rate limit headers."""

    def test_add_rate_limit_headers(self):
        """Should add X-RateLimit-* headers to response."""
        from fastapi.responses import JSONResponse

        response = JSONResponse(content={"status": "ok"})
        add_rate_limit_headers(response, limit=100, remaining=99, reset=1234567890)

        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "99"
        assert response.headers["X-RateLimit-Reset"] == "1234567890"


class TestLimiterIntegration:
    """Integration tests for rate limiter with FastAPI."""

    def test_limiter_creation(self):
        """Should create limiter successfully."""
        limiter = create_limiter()
        assert limiter is not None
        assert limiter._key_func is not None

    @pytest.mark.asyncio
    async def test_rate_limit_integration_with_fastapi(self):
        """Should integrate with FastAPI application."""
        from fastapi.responses import JSONResponse

        from src.web.middleware.rate_limit import create_limiter

        # Create a fresh limiter for testing
        limiter = create_limiter()

        app = FastAPI()
        app.state.limiter = limiter

        @app.get("/test")
        @limiter.limit("5/minute")
        async def test_endpoint(request: Request):
            # Return a proper Response object for the limiter to work with
            return JSONResponse(content={"status": "ok"})

        client = TestClient(app)

        # First request should succeed
        response = client.get("/test")
        assert response.status_code == 200

        # Verify response content
        assert response.json() == {"status": "ok"}


class TestRateLimitConfiguration:
    """Tests for rate limit configuration."""

    def test_rate_limit_string_conversion_seconds(self):
        """Should convert seconds to proper rate limit string."""
        # Test with seconds
        from src.web.middleware.rate_limit import get_auth_login_limit

        with patch("src.web.middleware.rate_limit.auth_settings") as mock_settings:
            mock_settings.rate_limit_login_attempts = 10
            mock_settings.rate_limit_login_window_seconds = 30

            limit = get_auth_login_limit()
            assert limit == "10/30seconds"

    def test_rate_limit_string_conversion_minutes(self):
        """Should convert minutes to proper rate limit string."""
        from src.web.middleware.rate_limit import get_auth_login_limit

        with patch("src.web.middleware.rate_limit.auth_settings") as mock_settings:
            mock_settings.rate_limit_login_attempts = 10
            mock_settings.rate_limit_login_window_seconds = 300  # 5 minutes

            limit = get_auth_login_limit()
            assert limit == "10/5minutes"

    def test_rate_limit_string_conversion_hours(self):
        """Should convert hours to proper rate limit string."""
        from src.web.middleware.rate_limit import get_auth_login_limit

        with patch("src.web.middleware.rate_limit.auth_settings") as mock_settings:
            mock_settings.rate_limit_login_attempts = 10
            mock_settings.rate_limit_login_window_seconds = 7200  # 2 hours

            limit = get_auth_login_limit()
            assert limit == "10/2hours"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
