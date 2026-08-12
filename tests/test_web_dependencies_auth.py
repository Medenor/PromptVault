# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for authentication and authorization dependencies.

This test suite verifies the FastAPI dependency functions for:
- Token extraction and validation
- User authentication and authorization
- Role-based access control (RBAC)
- Email verification enforcement
- IP address and user agent extraction
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from src.config.auth_config import AuthConfig
from src.db.models.user import User
from src.services.auth.jwt_service import JWTService
from src.web.dependencies.auth import (
    get_admin_user,
    get_auth_config,
    get_client_ip,
    get_current_active_user,
    get_current_user,
    get_current_user_token,
    get_editor_or_admin_user,
    get_jwt_service,
    get_optional_user,
    get_user_agent,
    require_role,
    require_verified_email,
)


class TestConfigurationDependencies:
    """Test configuration dependency functions."""

    def test_get_auth_config(self):
        """Test get_auth_config returns auth_settings."""
        config = get_auth_config()
        assert isinstance(config, AuthConfig)
        assert config.jwt_algorithm == "ES256"

    def test_get_jwt_service(self):
        """Test get_jwt_service creates JWTService instance."""
        config = get_auth_config()
        jwt_service = get_jwt_service(config)
        assert isinstance(jwt_service, JWTService)
        assert jwt_service.algorithm == "ES256"


class TestTokenExtraction:
    """Test token extraction and validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.jwt_service = Mock(spec=JWTService)

    def test_get_current_user_token_missing_header(self):
        """Test error when Authorization header is missing."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_token(
                authorization=None,
                access_token_cookie=None,
                jwt_service=self.jwt_service,
            )

        assert exc_info.value.status_code == 401
        assert "Missing authentication token" in exc_info.value.detail
        assert "WWW-Authenticate" in exc_info.value.headers

    def test_get_current_user_token_invalid_scheme(self):
        """Test error when Bearer scheme is not used."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_token(
                authorization="Basic dXNlcjpwYXNz", jwt_service=self.jwt_service
            )

        assert exc_info.value.status_code == 401
        assert "Invalid authentication scheme" in exc_info.value.detail

    def test_get_current_user_token_malformed_header(self):
        """Test error when Authorization header is malformed."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_token(authorization="Bearer", jwt_service=self.jwt_service)

        assert exc_info.value.status_code == 401

    def test_get_current_user_token_valid(self):
        """Test successful token extraction and validation."""
        token = "eyJ0eXAiOiJKV1QiLCJhbGc..."
        claims = {
            "sub": "user123",
            "username": "alice",
            "email": "alice@example.com",
            "role": "viewer",
        }

        self.jwt_service.validate_access_token.return_value = claims

        result = get_current_user_token(
            authorization=f"Bearer {token}", jwt_service=self.jwt_service
        )

        assert result == claims
        self.jwt_service.validate_access_token.assert_called_once_with(token)

    def test_get_current_user_token_expired(self):
        """Test error when token is expired."""
        from jwt.exceptions import ExpiredSignatureError

        token = "eyJ0eXAiOiJKV1QiLCJhbGc..."
        self.jwt_service.validate_access_token.side_effect = ExpiredSignatureError()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_token(
                authorization=f"Bearer {token}", jwt_service=self.jwt_service
            )

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_get_current_user_token_invalid_signature(self):
        """Test error when token signature is invalid."""
        from jwt.exceptions import InvalidSignatureError

        token = "eyJ0eXAiOiJKV1QiLCJhbGc..."
        self.jwt_service.validate_access_token.side_effect = InvalidSignatureError()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_token(
                authorization=f"Bearer {token}", jwt_service=self.jwt_service
            )

        assert exc_info.value.status_code == 401
        assert "signature" in exc_info.value.detail.lower()


class TestUserRetrieval:
    """Test user retrieval dependencies."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session = Mock(spec=Session)
        self.user = User(
            id="user123",
            username="alice",
            email="alice@example.com",
            password_hash="$argon2id$...",
            role="viewer",
            is_active=True,
            email_verified=True,
        )

    def test_get_current_user_success(self):
        """Test successful user retrieval."""
        token_data = {"sub": "user123"}

        with patch("src.web.dependencies.token.UserRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = self.user
            mock_repo_class.return_value = mock_repo

            user = get_current_user(token_data, self.session)

            assert user == self.user
            mock_repo.get_by_id.assert_called_once_with("user123")

    def test_get_current_user_missing_sub(self):
        """Test error when token lacks user ID."""
        token_data = {}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token_data, self.session)

        assert exc_info.value.status_code == 401
        assert "missing user identifier" in exc_info.value.detail.lower()

    def test_get_current_user_not_found(self):
        """Test error when user not found in database."""
        token_data = {"sub": "user123"}

        with patch("src.web.dependencies.token.UserRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                get_current_user(token_data, self.session)

            assert exc_info.value.status_code == 401
            assert "User not found" in exc_info.value.detail

    def test_get_current_active_user_success(self):
        """Test successful active user validation."""
        user = get_current_active_user(self.user)
        assert user == self.user

    def test_get_current_active_user_inactive(self):
        """Test error when user is inactive."""
        self.user.is_active = False

        with pytest.raises(HTTPException) as exc_info:
            get_current_active_user(self.user)

        assert exc_info.value.status_code == 401
        assert "deactivated" in exc_info.value.detail.lower()

    def test_get_current_active_user_locked(self):
        """Test error when user account is locked."""
        future_time = datetime.now(UTC) + timedelta(minutes=10)
        self.user.locked_until = future_time

        with pytest.raises(HTTPException) as exc_info:
            get_current_active_user(self.user)

        assert exc_info.value.status_code == 401
        assert "locked" in exc_info.value.detail.lower()

    def test_get_current_active_user_lock_expired(self):
        """Test successful access when lock has expired."""
        past_time = datetime.now(UTC) - timedelta(minutes=10)
        self.user.locked_until = past_time

        user = get_current_active_user(self.user)
        assert user == self.user


class TestOptionalAuthentication:
    """Test optional authentication dependency."""

    def setup_method(self):
        """Set up test fixtures."""
        self.jwt_service = Mock(spec=JWTService)
        self.session = Mock(spec=Session)

    def test_get_optional_user_no_token(self):
        """Test None returned when no token provided."""
        result = get_optional_user(None, self.jwt_service, self.session)
        assert result is None

    def test_get_optional_user_invalid_token(self):
        """Test exception raised for invalid token."""
        from jwt.exceptions import InvalidTokenError

        self.jwt_service.validate_access_token.side_effect = InvalidTokenError()

        with pytest.raises(HTTPException):
            get_optional_user("Bearer invalid", self.jwt_service, self.session)


class TestRoleBasedAccessControl:
    """Test role-based access control dependencies."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user = User(
            id="user123",
            username="alice",
            email="alice@example.com",
            password_hash="$argon2id$...",
            role="viewer",
            is_active=True,
            email_verified=True,
        )

    def test_require_role_authorized(self):
        """Test successful role authorization."""
        self.user.role = "admin"
        check_admin = require_role(["admin"])

        user = check_admin(self.user)
        assert user == self.user

    def test_require_role_unauthorized(self):
        """Test error when user lacks required role."""
        self.user.role = "viewer"
        check_admin = require_role(["admin"])

        with pytest.raises(HTTPException) as exc_info:
            check_admin(self.user)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    def test_require_role_multiple_roles(self):
        """Test authorization with multiple allowed roles."""
        self.user.role = "editor"
        check_editor_or_admin = require_role(["admin", "editor"])

        user = check_editor_or_admin(self.user)
        assert user == self.user

    def test_require_verified_email_success(self):
        """Test successful email verification check."""
        self.user.email_verified = True
        user = require_verified_email(self.user)
        assert user == self.user

    def test_require_verified_email_unverified(self):
        """Test error when email is not verified."""
        self.user.email_verified = False

        with pytest.raises(HTTPException) as exc_info:
            require_verified_email(self.user)

        assert exc_info.value.status_code == 403
        assert "verification required" in exc_info.value.detail.lower()


class TestRequestMetadata:
    """Test request metadata extraction dependencies."""

    def test_get_client_ip_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header."""
        request = Mock(spec=Request)
        request.headers.get.side_effect = lambda h: {
            "X-Forwarded-For": "203.0.113.1, 198.51.100.1",
        }.get(h)

        ip = get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_get_client_ip_real_ip(self):
        """Test IP extraction from X-Real-IP header."""
        request = Mock(spec=Request)
        request.headers.get.side_effect = lambda h: {
            "X-Real-IP": "203.0.113.1",
        }.get(h)

        ip = get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_get_client_ip_direct(self):
        """Test IP extraction from direct connection."""
        request = Mock(spec=Request)
        request.headers.get.return_value = None
        request.client.host = "203.0.113.1"

        ip = get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_get_client_ip_unknown(self):
        """Test fallback when IP cannot be determined."""
        request = Mock(spec=Request)
        request.headers.get.return_value = None
        request.client = None

        ip = get_client_ip(request)
        assert ip == "unknown"

    def test_get_user_agent(self):
        """Test User-Agent extraction."""
        request = Mock(spec=Request)
        request.headers.get.return_value = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

        user_agent = get_user_agent(request)
        assert "Mozilla/5.0" in user_agent

    def test_get_user_agent_truncated(self):
        """Test User-Agent truncation to 255 characters."""
        request = Mock(spec=Request)
        long_ua = "A" * 300
        request.headers.get.return_value = long_ua

        user_agent = get_user_agent(request)
        assert len(user_agent) == 255

    def test_get_user_agent_unknown(self):
        """Test User-Agent fallback when header is missing."""
        request = Mock(spec=Request)
        request.headers.get.side_effect = lambda key, default=None: (
            default if key == "User-Agent" else None
        )

        user_agent = get_user_agent(request)
        assert user_agent == "unknown"


class TestCompositeDependencies:
    """Test composite (convenience) dependencies."""

    def setup_method(self):
        """Set up test fixtures."""
        self.admin_user = User(
            id="admin123",
            username="admin",
            email="admin@example.com",
            password_hash="$argon2id$...",
            role="admin",
            is_active=True,
            email_verified=True,
        )
        self.editor_user = User(
            id="editor123",
            username="editor",
            email="editor@example.com",
            password_hash="$argon2id$...",
            role="editor",
            is_active=True,
            email_verified=True,
        )

    def test_get_admin_user_success(self):
        """Test get_admin_user with admin role."""
        user = get_admin_user(self.admin_user)
        assert user == self.admin_user

    def test_get_admin_user_unauthorized(self):
        """Test get_admin_user with non-admin role."""
        with pytest.raises(HTTPException) as exc_info:
            get_admin_user(self.editor_user)

        assert exc_info.value.status_code == 403

    def test_get_editor_or_admin_user_editor(self):
        """Test get_editor_or_admin_user with editor role."""
        user = get_editor_or_admin_user(self.editor_user)
        assert user == self.editor_user

    def test_get_editor_or_admin_user_admin(self):
        """Test get_editor_or_admin_user with admin role."""
        user = get_editor_or_admin_user(self.admin_user)
        assert user == self.admin_user
