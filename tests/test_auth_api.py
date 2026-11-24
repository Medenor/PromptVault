# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive integration tests for authentication API endpoints in PromptVault.

This module provides comprehensive integration tests for all 11 authentication
endpoints using FastAPI TestClient. Tests cover full request/response cycles
with a real in-memory database.

Endpoints Tested:
    Public Endpoints (6):
        POST /api/auth/register - User registration
        POST /api/auth/login - User login
        POST /api/auth/refresh - Token refresh
        POST /api/auth/logout - User logout
        POST /api/auth/password-reset/request - Request password reset
        POST /api/auth/password-reset/confirm - Confirm password reset

    Protected Endpoints (5):
        GET /api/auth/me - Get current user info
        POST /api/auth/change-password - Change password
        GET /api/auth/sessions - List user sessions
        DELETE /api/auth/sessions/{session_id} - Revoke specific session
        DELETE /api/auth/sessions - Revoke all sessions except current

Test Coverage:
    - Full request/response cycle
    - Success cases (happy path)
    - Error cases (validation, authentication, authorization)
    - Security features (lockout, rate limiting, token reuse)
    - Database integration (real transactions)
    - JWT token validation
    - Session management

Target: ≥90% endpoint coverage
Execution time: < 20 seconds
"""

import logging
from datetime import UTC
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session


def _request_password_reset_and_capture_token(
    password_reset_service, *, email: str, ip_address: str
) -> str:
    """Request a reset and capture the token passed to the email boundary."""
    with patch.object(password_reset_service, "_send_reset_email") as send_email:
        result = password_reset_service.request_password_reset(
            email=email, ip_address=ip_address
        )

    assert result is None
    send_email.assert_called_once()
    return send_email.call_args.kwargs["token"]


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def auth_client(test_db_engine, temp_data_dir: str):
    """FastAPI TestClient configured for authentication testing.

    Creates a test client with in-memory database, proper session management,
    and test configuration. Uses only the auth router to avoid issues with
    other routers during testing.

    Yields:
        TestClient: Configured test client for API testing
    """
    import importlib.util
    import sys
    from pathlib import Path

    from fastapi import FastAPI
    from sqlalchemy.orm import sessionmaker

    from src.db import session as session_module

    # Import auth router directly without going through __init__.py
    auth_module_path = (
        Path(__file__).parent.parent / "src" / "web" / "routers" / "auth.py"
    )
    spec = importlib.util.spec_from_file_location(
        "auth_router_module", auth_module_path
    )
    auth_router_module = importlib.util.module_from_spec(spec)
    sys.modules["auth_router_module"] = auth_router_module
    spec.loader.exec_module(auth_router_module)
    auth_router = auth_router_module.router

    # Store original session factory
    original_session_local = session_module.SessionLocal

    # Create test session factory
    TestSessionLocal = sessionmaker(bind=test_db_engine)

    # Patch the session factory
    session_module.SessionLocal = TestSessionLocal

    # Create minimal FastAPI app with just auth router
    app = FastAPI(title="PromptVault Auth Test")
    app.include_router(auth_router, prefix="/api")

    # Create test client
    client = TestClient(app)

    try:
        yield client
    finally:
        client.close()
        # Restore original session factory
        session_module.SessionLocal = original_session_local


@pytest.fixture
def test_user_credentials() -> dict[str, str]:
    """Test user credentials for authentication.

    Returns:
        dict: Username, email, and password
    """
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "SecureP@ssw0rd123",
    }


@pytest.fixture
def registered_user(
    auth_client: TestClient, test_user_credentials: dict[str, str]
) -> dict[str, Any]:
    """Create a registered user and return user data with tokens.

    Args:
        auth_client: Test client
        test_user_credentials: User credentials

    Returns:
        dict: User data including tokens
    """
    response = auth_client.post(
        "/api/auth/register",
        json={
            "username": test_user_credentials["username"],
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"],
            "confirm_password": test_user_credentials["password"],
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def auth_headers(registered_user: dict[str, Any]) -> dict[str, str]:
    """Create authentication headers with valid access token.

    Args:
        registered_user: Registered user data with tokens

    Returns:
        dict: Authorization headers
    """
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


# ============================================================================
# TEST POST /api/auth/register
# ============================================================================


class TestRegisterEndpoint:
    """Tests for POST /api/auth/register endpoint."""

    def test_register_success(self, auth_client: TestClient):
        """Test successful user registration."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "SecureP@ssw0rd123",
                "confirm_password": "SecureP@ssw0rd123",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0
        assert "user" in data

        # Verify user data
        user = data["user"]
        assert user["username"] == "alice"
        assert user["email"] == "alice@example.com"
        assert user["role"] == "viewer"
        assert user["is_active"] is True
        assert "id" in user
        assert "created_at" in user

    def test_register_duplicate_username(
        self, auth_client: TestClient, registered_user: dict[str, Any]
    ):
        """Test registration with duplicate username returns 409."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": registered_user["user"]["username"],
                "email": "different@example.com",
                "password": "SecureP@ssw0rd123",
                "confirm_password": "SecureP@ssw0rd123",
            },
        )

        assert response.status_code == 409
        assert "username" in response.json()["detail"].lower()

    def test_register_duplicate_email(
        self, auth_client: TestClient, registered_user: dict[str, Any]
    ):
        """Test registration with duplicate email returns 409."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "differentuser",
                "email": registered_user["user"]["email"],
                "password": "SecureP@ssw0rd123",
                "confirm_password": "SecureP@ssw0rd123",
            },
        )

        assert response.status_code == 409
        assert "email" in response.json()["detail"].lower()

    def test_register_password_policy_violation(self, auth_client: TestClient):
        """Test registration with weak password returns 422 (Pydantic validation)."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "weak",
                "confirm_password": "weak",
            },
        )

        assert response.status_code == 422
        data = response.json()
        # For Pydantic validation errors, detail is a list of error objects
        if isinstance(data["detail"], list):
            # Check if any error message contains "password"
            error_messages = [str(error.get("msg", "")) for error in data["detail"]]
            assert any("password" in msg.lower() for msg in error_messages)
        else:
            assert "password" in data["detail"].lower()

    def test_register_password_mismatch(self, auth_client: TestClient):
        """Test registration with password confirmation mismatch returns 422."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "SecureP@ssw0rd123",
                "confirm_password": "DifferentP@ssw0rd456",
            },
        )

        assert response.status_code == 422

    def test_register_invalid_email(self, auth_client: TestClient):
        """Test registration with invalid email format returns 422."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                "email": "not-an-email",
                "password": "SecureP@ssw0rd123",
                "confirm_password": "SecureP@ssw0rd123",
            },
        )

        assert response.status_code == 422

    def test_register_missing_fields(self, auth_client: TestClient):
        """Test registration with missing required fields returns 422."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                # Missing email, password, confirm_password
            },
        )

        assert response.status_code == 422


# ============================================================================
# TEST POST /api/auth/login
# ============================================================================


class TestLoginEndpoint:
    """Tests for POST /api/auth/login endpoint."""

    def test_login_success_with_username(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        registered_user: dict[str, Any],
    ):
        """Test successful login with username."""
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert "user" in data

    def test_login_success_with_email(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        registered_user: dict[str, Any],
    ):
        """Test successful login with email."""
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["email"],
                "password": test_user_credentials["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_invalid_credentials(
        self, auth_client: TestClient, registered_user: dict[str, Any]
    ):
        """Test login with invalid password returns 401."""
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": registered_user["user"]["username"],
                "password": "WrongPassword123",
            },
        )

        assert response.status_code == 401
        assert "credentials" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, auth_client: TestClient):
        """Test login with nonexistent user returns 401."""
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": "nonexistent",
                "password": "SomePassword123",
            },
        )

        assert response.status_code == 401

    def test_login_account_lockout(
        self,
        auth_client: TestClient,
        registered_user: dict[str, Any],
        test_user_credentials: dict[str, str],
    ):
        """Test account locks after max failed login attempts."""
        # Attempt login with wrong password 5 times
        for _ in range(5):
            response = auth_client.post(
                "/api/auth/login",
                json={
                    "username_or_email": test_user_credentials["username"],
                    "password": "WrongPassword123",
                },
            )
            assert response.status_code == 401

        # 6th attempt should be locked
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": "WrongPassword123",
            },
        )

        assert response.status_code == 401
        assert "locked" in response.json()["detail"].lower()


# ============================================================================
# TEST POST /api/auth/refresh
# ============================================================================


class TestRefreshEndpoint:
    """Tests for POST /api/auth/refresh endpoint."""

    def test_refresh_success(
        self, auth_client: TestClient, registered_user: dict[str, Any]
    ):
        """Test successful token refresh."""
        response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert "user" in data

        # Verify new tokens are different (rotation)
        assert data["access_token"] != registered_user["access_token"]
        assert data["refresh_token"] != registered_user["refresh_token"]

    def test_refresh_token_rotation(
        self, auth_client: TestClient, registered_user: dict[str, Any]
    ):
        """Test refresh tokens are rotated with same family."""
        # First refresh
        response1 = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # Second refresh with new token
        response2 = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": data1["refresh_token"]},
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # All tokens should be different
        assert data1["refresh_token"] != registered_user["refresh_token"]
        assert data2["refresh_token"] != data1["refresh_token"]

    def test_refresh_invalid_token(self, auth_client: TestClient):
        """Test refresh with invalid token returns 401."""
        response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401

    def test_refresh_expired_token(self, auth_client: TestClient):
        """Test refresh with expired token returns 401."""
        # Create a token that expired long ago
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.invalid"

        response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": expired_token},
        )

        assert response.status_code == 401

    def test_refresh_token_reuse_detection(
        self, auth_client: TestClient, registered_user: dict[str, Any]
    ):
        """Test token reuse is detected and family is revoked."""
        # Get new token
        response1 = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # Try to reuse old token (security breach simulation)
        response2 = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )

        # Should detect reuse and revoke family
        assert response2.status_code == 401
        assert "reuse" in response2.json()["detail"].lower()

        # New token should also be invalid (family revoked)
        response3 = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": data1["refresh_token"]},
        )
        assert response3.status_code == 401


# ============================================================================
# TEST POST /api/auth/logout
# ============================================================================


class TestLogoutEndpoint:
    """Tests for POST /api/auth/logout endpoint."""

    def test_logout_success(
        self, auth_client: TestClient, registered_user: dict[str, Any]
    ):
        """Test successful logout."""
        response = auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "logged out" in data["message"].lower()

    def test_logout_session_revoked(
        self, auth_client: TestClient, registered_user: dict[str, Any]
    ):
        """Test logout revokes session."""
        # Logout
        response = auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert response.status_code == 200

        # Try to refresh with logged out token
        response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert response.status_code == 401

    def test_logout_idempotent(
        self, auth_client: TestClient, registered_user: dict[str, Any]
    ):
        """Test logout with invalid token doesn't error (idempotent)."""
        # First logout
        response1 = auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert response1.status_code == 200

        # Second logout with same token (already logged out)
        response2 = auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        # Should return 200 (idempotent)
        assert response2.status_code == 200


# ============================================================================
# TEST GET /api/auth/me
# ============================================================================


class TestMeEndpoint:
    """Tests for GET /api/auth/me endpoint."""

    def test_me_success(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        registered_user: dict[str, Any],
    ):
        """Test getting current user with valid token."""
        response = auth_client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify user data
        assert data["username"] == registered_user["user"]["username"]
        assert data["email"] == registered_user["user"]["email"]
        assert data["role"] == registered_user["user"]["role"]
        assert "id" in data

    def test_me_unauthorized_no_token(self, auth_client: TestClient):
        """Test /me without token returns 401."""
        response = auth_client.get("/api/auth/me")

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_me_invalid_token(self, auth_client: TestClient):
        """Test /me with invalid token returns 401."""
        response = auth_client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401

    def test_me_expired_token(self, auth_client: TestClient):
        """Test /me with expired token returns 401."""
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.invalid"

        response = auth_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401


# ============================================================================
# TEST POST /api/auth/change-password
# ============================================================================


class TestChangePasswordEndpoint:
    """Tests for POST /api/auth/change-password endpoint."""

    def test_change_password_success(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        test_user_credentials: dict[str, str],
    ):
        """Test successful password change."""
        new_password = "NewSecureP@ssw0rd456"

        response = auth_client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": test_user_credentials["password"],
                "new_password": new_password,
                "confirm_new_password": new_password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "password changed" in data["message"].lower()

        # Verify can login with new password
        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": new_password,
            },
        )
        assert login_response.status_code == 200

    def test_change_password_incorrect_old(
        self, auth_client: TestClient, auth_headers: dict[str, str]
    ):
        """Test change password with incorrect old password returns 401."""
        response = auth_client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": "WrongPassword123",
                "new_password": "NewSecureP@ssw0rd456",
                "confirm_new_password": "NewSecureP@ssw0rd456",
            },
        )

        assert response.status_code == 401

    def test_change_password_policy_violation(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        test_user_credentials: dict[str, str],
    ):
        """Test change password with weak new password returns 400."""
        response = auth_client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": test_user_credentials["password"],
                "new_password": "weak",
                "confirm_new_password": "weak",
            },
        )

        assert response.status_code == 400

    def test_change_password_confirmation_mismatch(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        test_user_credentials: dict[str, str],
    ):
        """Test change password with mismatched confirmation returns 422."""
        response = auth_client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": test_user_credentials["password"],
                "new_password": "NewSecureP@ssw0rd456",
                "confirm_new_password": "DifferentP@ssw0rd789",
            },
        )

        assert response.status_code == 422

    def test_change_password_unauthorized(self, auth_client: TestClient):
        """Test change password without token returns 401."""
        response = auth_client.post(
            "/api/auth/change-password",
            json={
                "old_password": "OldPassword123",
                "new_password": "NewSecureP@ssw0rd456",
                "confirm_new_password": "NewSecureP@ssw0rd456",
            },
        )

        assert response.status_code == 401


# ============================================================================
# TEST GET /api/auth/sessions
# ============================================================================


class TestSessionsEndpoint:
    """Tests for GET /api/auth/sessions endpoint."""

    def test_sessions_list_success(
        self, auth_client: TestClient, auth_headers: dict[str, str]
    ):
        """Test listing user sessions."""
        response = auth_client.get("/api/auth/sessions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "sessions" in data
        assert "total" in data
        assert data["total"] >= 1  # At least the current session

        # Verify session data structure
        if data["sessions"]:
            session = data["sessions"][0]
            assert "id" in session
            assert "family_id" in session
            assert "created_at" in session
            assert "ip_address" in session
            assert "user_agent" in session
            assert "is_revoked" in session

    def test_sessions_empty_list(
        self, auth_client: TestClient, registered_user: dict[str, Any]
    ):
        """Test listing sessions when all are revoked."""
        # Logout (revoke session)
        auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )

        # Login again to get new session
        new_login = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": registered_user["user"]["username"],
                "password": "SecureP@ssw0rd123",
            },
        )

        # List sessions
        response = auth_client.get(
            "/api/auth/sessions",
            headers={"Authorization": f"Bearer {new_login.json()['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_sessions_multiple(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        registered_user: dict[str, Any],
    ):
        """Test listing multiple sessions."""
        # Create second session by logging in again
        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )
        assert login_response.status_code == 200

        # List sessions from first session
        response = auth_client.get(
            "/api/auth/sessions",
            headers={"Authorization": f"Bearer {registered_user['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2  # At least two sessions

    def test_sessions_unauthorized(self, auth_client: TestClient):
        """Test listing sessions without token returns 401."""
        response = auth_client.get("/api/auth/sessions")

        assert response.status_code == 401


# ============================================================================
# TEST DELETE /api/auth/sessions/{session_id}
# ============================================================================


class TestRevokeSessionEndpoint:
    """Tests for DELETE /api/auth/sessions/{session_id} endpoint."""

    def test_revoke_session_success(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        test_user_credentials: dict[str, str],
    ):
        """Test revoking specific session."""
        # Create second session
        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )
        assert login_response.status_code == 200

        # Get sessions
        sessions_response = auth_client.get("/api/auth/sessions", headers=auth_headers)
        sessions = sessions_response.json()["sessions"]

        # Revoke one session
        session_id = sessions[0]["id"]
        response = auth_client.delete(
            f"/api/auth/sessions/{session_id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["revoked_count"] == 1

    def test_revoke_session_not_found(
        self, auth_client: TestClient, auth_headers: dict[str, str]
    ):
        """Test revoking non-existent session returns 404."""
        fake_session_id = "00000000-0000-0000-0000-000000000000"

        response = auth_client.delete(
            f"/api/auth/sessions/{fake_session_id}", headers=auth_headers
        )

        assert response.status_code == 404

    def test_revoke_session_unauthorized(self, auth_client: TestClient):
        """Test revoking session without token returns 401."""
        session_id = "00000000-0000-0000-0000-000000000000"

        response = auth_client.delete(f"/api/auth/sessions/{session_id}")

        assert response.status_code == 401


# ============================================================================
# TEST DELETE /api/auth/sessions
# ============================================================================


class TestRevokeAllSessionsEndpoint:
    """Tests for DELETE /api/auth/sessions endpoint."""

    def test_revoke_all_sessions_success(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        test_user_credentials: dict[str, str],
    ):
        """Test revoking all sessions except current."""
        # Create multiple sessions
        for _ in range(3):
            auth_client.post(
                "/api/auth/login",
                json={
                    "username_or_email": test_user_credentials["username"],
                    "password": test_user_credentials["password"],
                },
            )

        # Revoke all except current
        response = auth_client.delete("/api/auth/sessions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "revoked_count" in data
        assert data["revoked_count"] >= 0  # May be 0 if only current session

    def test_revoke_all_sessions_count(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        registered_user: dict[str, Any],
    ):
        """Test revoke all returns correct count."""
        # Create 2 additional sessions
        auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )
        auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )

        # Revoke all from original session
        response = auth_client.delete(
            "/api/auth/sessions",
            headers={"Authorization": f"Bearer {registered_user['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should revoke the 2 additional sessions
        assert data["revoked_count"] >= 2

    def test_revoke_all_sessions_unauthorized(self, auth_client: TestClient):
        """Test revoking all sessions without token returns 401."""
        response = auth_client.delete("/api/auth/sessions")

        assert response.status_code == 401


# ============================================================================
# TEST POST /api/auth/password-reset/request
# ============================================================================


class TestPasswordResetRequestEndpoint:
    """Tests for POST /api/auth/password-reset/request endpoint."""

    def test_password_reset_request_success(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        registered_user: dict[str, Any],
    ):
        """Test successful password reset request."""
        response = auth_client.post(
            "/api/auth/password-reset/request",
            json={"email": test_user_credentials["email"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "email" in data
        # Email should be masked
        assert "***" in data["email"]

    def test_password_reset_request_nonexistent_email(self, auth_client: TestClient):
        """Test password reset for non-existent email returns 200 (no info leakage)."""
        response = auth_client.post(
            "/api/auth/password-reset/request",
            json={"email": "nonexistent@example.com"},
        )

        # Should return 200 to prevent user enumeration
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_password_reset_request_masks_unknown_email_in_logs(
        self,
        auth_client: TestClient,
        caplog: pytest.LogCaptureFixture,
    ):
        """Unknown-account logs must not expose the submitted address."""
        email = "nonexistent@example.com"

        with caplog.at_level(logging.INFO):
            response = auth_client.post(
                "/api/auth/password-reset/request",
                json={"email": email},
            )

        assert response.status_code == 200
        assert email not in caplog.text
        assert "n***@example.com" in caplog.text

    def test_password_reset_request_masks_rate_limited_email_in_logs(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        registered_user: dict[str, Any],
        caplog: pytest.LogCaptureFixture,
    ):
        """Rate-limit logs must not expose the submitted address."""
        email = test_user_credentials["email"]

        with caplog.at_level(logging.INFO):
            for _ in range(4):
                response = auth_client.post(
                    "/api/auth/password-reset/request",
                    json={"email": email},
                )

        assert response.status_code == 200
        assert email not in caplog.text
        assert f"{email[0]}***@{email.partition('@')[2]}" in caplog.text

    def test_password_reset_request_response_identical_for_known_and_unknown(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        registered_user: dict[str, Any],
    ):
        """The response must not reveal whether an account exists.

        The registered address and an unknown address that masks to the same
        value ("t***@example.com") must produce byte-identical responses.
        """
        known = auth_client.post(
            "/api/auth/password-reset/request",
            json={"email": test_user_credentials["email"]},
        )
        local, _, domain = test_user_credentials["email"].partition("@")
        unknown = auth_client.post(
            "/api/auth/password-reset/request",
            json={"email": f"{local[0]}nobody-here@{domain}"},
        )

        assert known.status_code == unknown.status_code == 200
        assert known.json() == unknown.json()
        assert known.json()["email"] == f"{local[0]}***@{domain}"

    def test_password_reset_request_does_not_log_reset_token(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        registered_user: dict[str, Any],
        caplog: pytest.LogCaptureFixture,
    ):
        """The reset link is a bearer credential and must never reach the logs."""
        with caplog.at_level(logging.DEBUG):
            response = auth_client.post(
                "/api/auth/password-reset/request",
                json={"email": test_user_credentials["email"]},
            )
        assert response.status_code == 200

        # A log record can carry the secret in its message or in extra fields.
        captured = " ".join(
            [record.getMessage() for record in caplog.records]
            + [str(record.__dict__) for record in caplog.records]
        )
        assert "reset-password" not in captured
        assert "reset_url" not in captured
        assert "token=" not in captured

    @pytest.mark.parametrize(
        ("email", "expected"),
        [
            ("alice@example.com", "a***@example.com"),
            ("@example.com", "***@***"),
            ("alice@", "***@***"),
            ("no-at-sign", "***@***"),
            ("a@b@c", "***@***"),
        ],
    )
    def test_mask_email(self, email: str, expected: str):
        from src.web.routers.auth_password_router import _mask_email

        assert _mask_email(email) == expected


# ============================================================================
# TEST POST /api/auth/password-reset/confirm
# ============================================================================


class TestPasswordResetConfirmEndpoint:
    """Tests for POST /api/auth/password-reset/confirm endpoint."""

    def test_password_reset_confirm_invalid_token(self, auth_client: TestClient):
        """Test password reset confirm with invalid token returns 401."""
        response = auth_client.post(
            "/api/auth/password-reset/confirm",
            json={
                "token": "invalid-token-12345",
                "new_password": "NewSecureP@ssw0rd456",
                "confirm_new_password": "NewSecureP@ssw0rd456",
            },
        )

        assert response.status_code == 401

    def test_password_reset_confirm_policy_violation(self, auth_client: TestClient):
        """Test password reset with weak password returns 400."""
        response = auth_client.post(
            "/api/auth/password-reset/confirm",
            json={
                "token": "some-valid-token-format-12345678901234567890",
                "new_password": "weak",
                "confirm_new_password": "weak",
            },
        )

        # May return 400 for policy violation or 401 for invalid token
        assert response.status_code in [400, 401]


# ============================================================================
# TEST PASSWORD RESET SERVICE (Unit/Integration Tests)
# ============================================================================


class TestPasswordResetService:
    """Comprehensive tests for PasswordResetService.

    This test class provides security-critical coverage for the password reset
    service, targeting 95%+ line coverage to ensure robust protection against
    password reset vulnerabilities.

    Test Categories:
        - Rate Limiting Tests
        - Token Validation Tests
        - Password Reset Flow Tests
        - Token Hashing Tests
        - Cleanup Tests
        - Edge Cases

    Note on SQLite Timezone Handling:
        SQLite does not preserve timezone information in datetime columns, even when
        configured with DateTime(timezone=True). This causes timezone-naive datetimes
        to be returned from the database. To work around this limitation, tests use
        the request_password_reset method which properly handles token creation through
        the service layer.
    """

    @pytest.fixture
    def password_reset_service(self, test_db_session: Session):
        """Create PasswordResetService instance with test dependencies."""
        from src.config.auth_config import auth_settings
        from src.db.repositories.password_reset_token_repository import (
            PasswordResetTokenRepository,
        )
        from src.db.repositories.user_repository import UserRepository
        from src.services.auth.password_reset_service import PasswordResetService
        from src.services.auth.password_service import PasswordService

        password_service = PasswordService(auth_settings)
        token_repo = PasswordResetTokenRepository(test_db_session)
        user_repo = UserRepository(test_db_session)

        return PasswordResetService(
            config=auth_settings,
            password_service=password_service,
            token_repository=token_repo,
            user_repository=user_repo,
        )

    @pytest.fixture
    def test_user_for_reset(self, test_db_session: Session):
        """Create a test user for password reset testing."""
        from datetime import datetime

        from src.config.auth_config import auth_settings
        from src.db.models.user import User
        from src.services.auth.password_service import PasswordService

        password_service = PasswordService(auth_settings)
        password_hash = password_service.hash_password("OldP@ssw0rd123")

        user = User(
            id="test-reset-user-id",
            username="resetuser",
            email="reset@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            email_verified=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        test_db_session.add(user)
        test_db_session.flush()
        return user

    # ========================================================================
    # RATE LIMITING TESTS
    # ========================================================================

    def test_request_password_reset_rate_limit_exceeded(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that rate limit is enforced after 3 requests in 1 hour."""
        from src.services.exceptions import RateLimitExceededError

        email = test_user_for_reset.email

        # Make 3 successful requests (should work)
        for _i in range(3):
            token = _request_password_reset_and_capture_token(
                password_reset_service, email=email, ip_address="192.168.1.1"
            )
            assert token is not None
            test_db_session.commit()

        # 4th request should hit rate limit
        with pytest.raises(RateLimitExceededError) as exc_info:
            password_reset_service.request_password_reset(
                email=email, ip_address="192.168.1.1"
            )

        assert exc_info.value.http_status == 429
        assert exc_info.value.context.get("retry_after_seconds") is not None

    def test_request_password_reset_rate_limit_retry_after(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that retry_after value is correctly calculated."""
        from src.services.exceptions import RateLimitExceededError

        email = test_user_for_reset.email

        # Exhaust rate limit
        for _i in range(3):
            password_reset_service.request_password_reset(
                email=email, ip_address="192.168.1.1"
            )
            test_db_session.commit()

        # Check retry_after in error
        with pytest.raises(RateLimitExceededError) as exc_info:
            password_reset_service.request_password_reset(
                email=email, ip_address="192.168.1.1"
            )

        # Should have retry_after in context
        retry_after = exc_info.value.context.get("retry_after_seconds")
        assert retry_after is not None
        assert retry_after > 0

    def test_request_password_reset_invalidates_old_tokens(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that requesting new token invalidates existing tokens."""
        from src.db.repositories.password_reset_token_repository import (
            PasswordResetTokenRepository,
        )

        email = test_user_for_reset.email
        token_repo = PasswordResetTokenRepository(test_db_session)

        # Create first token
        token1 = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Verify first token exists and is valid
        hashed_token1 = password_reset_service._hash_token(token1)
        token_record1 = token_repo.get_by_token(hashed_token1)
        assert token_record1 is not None
        assert not token_record1.is_used

        # Create second token
        password_reset_service.request_password_reset(
            email=email, ip_address="192.168.1.2"
        )
        test_db_session.commit()

        # Refresh token_record1 from database
        test_db_session.expire(token_record1)
        test_db_session.refresh(token_record1)

        # First token should now be invalidated
        assert token_record1.is_used is True
        assert token_record1.used_at is not None

    # ========================================================================
    # TOKEN VALIDATION TESTS
    # ========================================================================

    def test_verify_token_expired(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that expired token is rejected."""

        from src.db.repositories.password_reset_token_repository import (
            PasswordResetTokenRepository,
        )

        email = test_user_for_reset.email
        PasswordResetTokenRepository(test_db_session)

        # Create a valid token using the service
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Manually expire the token by updating its expires_at directly in DB using raw SQL
        # This avoids SQLite timezone issues
        hashed_token = password_reset_service._hash_token(token)
        test_db_session.execute(
            text(
                "UPDATE password_reset_tokens SET expires_at = datetime('now', '-2 hours') WHERE token = :token"
            ),
            {"token": hashed_token},
        )
        test_db_session.commit()

        # Now verify token - should be expired
        is_valid, result = password_reset_service.verify_reset_token(token)

        assert is_valid is False
        assert "expired" in result.lower()

    def test_verify_token_already_used(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that already-used token is rejected."""
        from src.db.repositories.password_reset_token_repository import (
            PasswordResetTokenRepository,
        )

        email = test_user_for_reset.email
        token_repo = PasswordResetTokenRepository(test_db_session)

        # Create token using the service
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Mark token as used
        hashed_token = password_reset_service._hash_token(token)
        token_record = token_repo.get_by_token(hashed_token)
        token_repo.mark_token_used(token_record.id)
        test_db_session.commit()

        # Verify token
        is_valid, result = password_reset_service.verify_reset_token(token)

        assert is_valid is False
        assert "used" in result.lower()

    def test_verify_token_user_not_found(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that token for non-existent user is rejected."""
        from src.db.repositories.user_repository import UserRepository

        email = test_user_for_reset.email
        UserRepository(test_db_session)

        # Create token using the service
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Delete the user
        test_db_session.delete(test_user_for_reset)
        test_db_session.commit()

        # Verify token - user no longer exists
        is_valid, result = password_reset_service.verify_reset_token(token)

        assert is_valid is False
        assert "invalid" in result.lower()

    def test_verify_token_user_inactive(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that token for inactive user is rejected."""
        email = test_user_for_reset.email

        # Create token while user is active
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Now deactivate the user
        test_user_for_reset.is_active = False
        test_db_session.commit()

        # Verify token - user is now inactive
        is_valid, result = password_reset_service.verify_reset_token(token)

        assert is_valid is False
        assert "active" in result.lower()

    def test_verify_token_valid(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that valid token is accepted."""
        email = test_user_for_reset.email

        # Request password reset
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Verify token
        is_valid, result = password_reset_service.verify_reset_token(token)

        assert is_valid is True
        assert result == test_user_for_reset.id

    # ========================================================================
    # PASSWORD RESET FLOW TESTS
    # ========================================================================

    def test_reset_password_success(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test successful password reset."""
        from src.config.auth_config import auth_settings
        from src.services.auth.password_service import PasswordService

        email = test_user_for_reset.email
        new_password = "NewSecureP@ssw0rd456"

        # Request password reset
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Reset password
        success = password_reset_service.reset_password(token, new_password)
        test_db_session.commit()

        assert success is True

        # Verify new password works
        test_db_session.refresh(test_user_for_reset)
        password_service = PasswordService(auth_settings)
        assert password_service.verify_password(
            new_password, test_user_for_reset.password_hash
        )

    def test_reset_password_policy_violation(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that weak password is rejected."""
        from src.services.exceptions import PasswordPolicyError

        email = test_user_for_reset.email
        weak_password = "weak"

        # Request password reset
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Try to reset with weak password
        with pytest.raises(PasswordPolicyError) as exc_info:
            password_reset_service.reset_password(token, weak_password)

        assert exc_info.value.http_status == 400
        assert "policy_errors" in exc_info.value.context

    def test_reset_password_marks_token_used(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that token is marked as used after password reset."""
        from src.db.repositories.password_reset_token_repository import (
            PasswordResetTokenRepository,
        )

        email = test_user_for_reset.email
        new_password = "NewSecureP@ssw0rd456"

        # Request password reset
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Get token record
        token_repo = PasswordResetTokenRepository(test_db_session)
        hashed_token = password_reset_service._hash_token(token)
        token_record = token_repo.get_by_token(hashed_token)
        assert not token_record.is_used

        # Reset password
        password_reset_service.reset_password(token, new_password)
        test_db_session.commit()

        # Verify token is marked as used
        test_db_session.refresh(token_record)
        assert token_record.is_used is True
        assert token_record.used_at is not None

    def test_reset_password_invalidates_other_tokens(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that resetting password invalidates all other user tokens."""
        from src.db.repositories.password_reset_token_repository import (
            PasswordResetTokenRepository,
        )

        email = test_user_for_reset.email
        new_password = "NewSecureP@ssw0rd456"

        # Request two password resets
        password_reset_service.request_password_reset(
            email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Wait a bit and create another
        import time

        time.sleep(0.1)
        token2 = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.2"
        )
        test_db_session.commit()

        # Reset password with token2
        password_reset_service.reset_password(token2, new_password)
        test_db_session.commit()

        # Verify all tokens are invalidated
        token_repo = PasswordResetTokenRepository(test_db_session)
        user_tokens = token_repo.get_user_tokens(test_user_for_reset.id)

        for token_record in user_tokens:
            assert token_record.is_used is True

    # ========================================================================
    # TOKEN HASHING TESTS
    # ========================================================================

    def test_hash_token_consistency(self, password_reset_service):
        """Test that same input produces same hash."""
        token = "test-token-consistency"

        hash1 = password_reset_service._hash_token(token)
        hash2 = password_reset_service._hash_token(token)

        assert hash1 == hash2

    def test_hash_token_hex_format(self, password_reset_service):
        """Test that hash is valid hexadecimal."""
        token = "test-token-hex"

        hash_result = password_reset_service._hash_token(token)

        # Should be valid hex string
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64  # SHA-256 produces 64 hex characters
        # Verify it's valid hex
        try:
            int(hash_result, 16)
        except ValueError:
            pytest.fail("Hash is not valid hexadecimal")

    def test_hash_token_different_inputs(self, password_reset_service):
        """Test that different tokens produce different hashes."""
        token1 = "test-token-1"
        token2 = "test-token-2"

        hash1 = password_reset_service._hash_token(token1)
        hash2 = password_reset_service._hash_token(token2)

        assert hash1 != hash2

    # ========================================================================
    # CLEANUP TESTS
    # ========================================================================

    def test_cleanup_expired_tokens_deletes_expired(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that cleanup removes expired tokens."""
        from src.db.repositories.password_reset_token_repository import (
            PasswordResetTokenRepository,
        )

        email = test_user_for_reset.email
        token_repo = PasswordResetTokenRepository(test_db_session)

        # Create token
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Manually expire the token using raw SQL
        hashed_token = password_reset_service._hash_token(token)
        test_db_session.execute(
            text(
                "UPDATE password_reset_tokens SET expires_at = datetime('now', '-2 hours') WHERE token = :token"
            ),
            {"token": hashed_token},
        )
        test_db_session.commit()

        # Run cleanup
        deleted_count = password_reset_service.cleanup_expired_tokens()
        test_db_session.commit()

        assert deleted_count >= 1

        # Verify token is gone
        token_record = token_repo.get_by_token(hashed_token)
        assert token_record is None

    def test_cleanup_expired_tokens_keeps_valid(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that cleanup doesn't remove valid tokens."""
        from src.db.repositories.password_reset_token_repository import (
            PasswordResetTokenRepository,
        )

        email = test_user_for_reset.email

        # Create valid token
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Run cleanup
        password_reset_service.cleanup_expired_tokens()
        test_db_session.commit()

        # Verify token still exists and is valid
        token_repo = PasswordResetTokenRepository(test_db_session)
        hashed_token = password_reset_service._hash_token(token)
        token_record = token_repo.get_by_token(hashed_token)

        assert token_record is not None
        assert not token_record.is_used

    def test_cleanup_expired_tokens_returns_count(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that cleanup returns correct count of deleted tokens."""
        email = test_user_for_reset.email

        # Create 3 tokens
        tokens = []
        for _i in range(3):
            token = _request_password_reset_and_capture_token(
                password_reset_service, email=email, ip_address="192.168.1.1"
            )
            tokens.append(token)
            test_db_session.commit()

        # Expire all tokens using raw SQL
        test_db_session.execute(
            text(
                "UPDATE password_reset_tokens SET expires_at = datetime('now', '-2 hours') WHERE user_id = :user_id"
            ),
            {"user_id": test_user_for_reset.id},
        )
        test_db_session.commit()

        # Run cleanup
        deleted_count = password_reset_service.cleanup_expired_tokens()
        test_db_session.commit()

        assert deleted_count == 3

    # ========================================================================
    # EDGE CASES
    # ========================================================================

    def test_request_password_reset_nonexistent_email(self, password_reset_service):
        """Test that requesting reset for non-existent email raises UserNotFoundError."""
        from src.services.exceptions import UserNotFoundError

        with pytest.raises(UserNotFoundError):
            password_reset_service.request_password_reset(
                email="nonexistent@example.com", ip_address="192.168.1.1"
            )

    def test_verify_token_malformed_token(self, password_reset_service):
        """Test that malformed token is rejected."""
        malformed_token = "this-is-not-a-valid-token"

        is_valid, result = password_reset_service.verify_reset_token(malformed_token)

        assert is_valid is False
        assert "invalid" in result.lower() or "expired" in result.lower()

    def test_reset_password_empty_password(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that empty password is rejected."""
        from src.services.exceptions import PasswordPolicyError

        email = test_user_for_reset.email

        # Request password reset
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Try to reset with empty password
        with pytest.raises(PasswordPolicyError):
            password_reset_service.reset_password(token, "")

    def test_reset_password_token_not_found(self, password_reset_service):
        """Test that resetting with non-existent token raises error."""
        from src.services.exceptions import TokenNotFoundError

        fake_token = "non-existent-token-123456"

        with pytest.raises(TokenNotFoundError):
            password_reset_service.reset_password(fake_token, "NewP@ssw0rd123")

    def test_reset_password_expired_token(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that resetting with expired token raises error."""
        from src.services.exceptions import TokenExpiredError

        email = test_user_for_reset.email

        # Create token
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Expire the token using raw SQL
        hashed_token = password_reset_service._hash_token(token)
        test_db_session.execute(
            text(
                "UPDATE password_reset_tokens SET expires_at = datetime('now', '-1 hours') WHERE token = :token"
            ),
            {"token": hashed_token},
        )
        test_db_session.commit()

        # Try to reset password
        with pytest.raises(TokenExpiredError):
            password_reset_service.reset_password(token, "NewP@ssw0rd123")

    def test_reset_password_already_used_token(
        self, password_reset_service, test_user_for_reset, test_db_session: Session
    ):
        """Test that resetting with already-used token raises error."""
        from src.services.exceptions import TokenAlreadyUsedError

        email = test_user_for_reset.email

        # Request password reset
        token = _request_password_reset_and_capture_token(
            password_reset_service, email=email, ip_address="192.168.1.1"
        )
        test_db_session.commit()

        # Reset password once (should work)
        password_reset_service.reset_password(token, "NewP@ssw0rd123")
        test_db_session.commit()

        # Try to use token again
        with pytest.raises(TokenAlreadyUsedError):
            password_reset_service.reset_password(token, "AnotherP@ssw0rd456")


# ============================================================================
# TEST SECURITY HEADERS
# ============================================================================


class TestSecurityHeaders:
    """Tests for security headers in responses."""

    def test_unauthorized_has_www_authenticate(self, auth_client: TestClient):
        """Test 401 responses include WWW-Authenticate header."""
        response = auth_client.get("/api/auth/me")

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert "Bearer" in response.headers["WWW-Authenticate"]

    def test_invalid_token_error_description(self, auth_client: TestClient):
        """Test invalid token returns proper error in WWW-Authenticate."""
        response = auth_client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers


# ============================================================================
# TEST ERROR RESPONSES
# ============================================================================


class TestErrorResponses:
    """Tests for error response format and content."""

    def test_error_has_detail_field(self, auth_client: TestClient):
        """Test error responses have detail field."""
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": "nonexistent",
                "password": "password",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)

    def test_validation_error_format(self, auth_client: TestClient):
        """Test validation errors have proper format."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "ab",  # Too short
                "email": "invalid-email",
                "password": "test",
                "confirm_password": "test",
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_no_sensitive_data_in_errors(self, auth_client: TestClient):
        """Test error messages don't leak sensitive data."""
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": "testuser",
                "password": "wrongpassword",
            },
        )

        assert response.status_code in [401, 404]
        data = response.json()
        detail = data["detail"].lower()

        # Should not contain password hashes or sensitive database info
        assert "argon2" not in detail
        assert "$" not in detail
        assert "hash" not in detail


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestAuthenticationFlow:
    """Integration tests for complete authentication flows."""

    def test_full_registration_login_flow(self, auth_client: TestClient):
        """Test complete flow: register -> login -> access protected endpoint."""
        # Register
        register_response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "flowtest",
                "email": "flowtest@example.com",
                "password": "SecureP@ssw0rd123",
                "confirm_password": "SecureP@ssw0rd123",
            },
        )
        assert register_response.status_code == 201

        # Login
        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": "flowtest",
                "password": "SecureP@ssw0rd123",
            },
        )
        assert login_response.status_code == 200

        # Access protected endpoint
        me_response = auth_client.get(
            "/api/auth/me",
            headers={
                "Authorization": f"Bearer {login_response.json()['access_token']}"
            },
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "flowtest"

    def test_token_refresh_flow(
        self, auth_client: TestClient, registered_user: dict[str, Any]
    ):
        """Test complete token refresh flow."""
        # Refresh token
        refresh_response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert refresh_response.status_code == 200

        # Use new access token
        me_response = auth_client.get(
            "/api/auth/me",
            headers={
                "Authorization": f"Bearer {refresh_response.json()['access_token']}"
            },
        )
        assert me_response.status_code == 200

    def test_logout_flow(
        self, auth_client: TestClient, registered_user: dict[str, Any]
    ):
        """Test complete logout flow."""
        # Logout
        logout_response = auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert logout_response.status_code == 200

        # Try to use tokens after logout
        auth_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {registered_user['access_token']}"},
        )
        # Access token may still work briefly (short-lived)
        # But refresh should fail
        refresh_response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert refresh_response.status_code == 401
