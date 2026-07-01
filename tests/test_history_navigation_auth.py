# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Tests for browser history navigation authentication behavior.

These tests verify the fix for the bug where clicking the browser's
"previous page" button (back navigation) while logged in incorrectly
redirected to the login page. The root cause was that:

1. The login page (``/auth/login``) was cached by the browser and served
   from cache on back navigation, even though the user had a valid session.
2. The home route (``/``) issued a 302 redirect to ``/auth/login`` for
   unauthenticated users, and that redirect could be cached/replayed.

The fix ensures:
- The login page redirects authenticated users (detected via the
  ``access_token`` cookie) back to the app root.
- Both the login page HTML and the home route's 302 redirect include
  ``Cache-Control: no-store`` headers so browsers always re-evaluate
  auth state during history navigation.
"""

from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from src.config.auth_config import auth_settings


# Skip tests that assume authentication is mandatory. When AUTH_ENABLED=false
# the app runs in anonymous mode and these behaviors do not apply.
require_auth = pytest.mark.skipif(
    not auth_settings.auth_enabled,
    reason="AUTH_ENABLED=false: authentication is disabled (anonymous mode)",
)


@pytest.fixture
def registered_user_with_client(
    api_client: TestClient,
) -> Dict[str, Any]:
    """Register a user via the API and return credentials and tokens.

    Args:
        api_client: FastAPI TestClient fixture

    Returns:
        dict with ``access_token``, ``refresh_token``, ``user``, and ``client``
    """
    response = api_client.post(
        "/api/auth/register",
        json={
            "username": "historynav",
            "email": "historynav@example.com",
            "password": "SecureP@ssw0rd123",
            "confirm_password": "SecureP@ssw0rd123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    return {**data, "client": api_client}


class TestLoginPageCacheHeaders:
    """Tests for cache-control headers on the login page."""

    def test_login_page_has_no_store_cache_control(self, api_client: TestClient):
        """The login page must include no-store cache headers."""
        response = api_client.get("/auth/login")

        assert response.status_code == 200
        cache_control = response.headers.get("cache-control", "")
        assert "no-store" in cache_control
        assert "no-cache" in cache_control

    def test_login_page_has_pragma_no_cache(self, api_client: TestClient):
        """The login page should include Pragma: no-cache for older browsers."""
        response = api_client.get("/auth/login")
        assert response.headers.get("pragma") == "no-cache"


@require_auth
class TestLoginPageRedirectsAuthenticatedUsers:
    """Tests that the login page redirects users with a valid session."""

    def test_login_page_redirects_when_cookie_present(
        self, registered_user_with_client: Dict[str, Any]
    ):
        """GET /auth/login with a valid access_token cookie should redirect to /."""
        client: TestClient = registered_user_with_client["client"]
        access_token = registered_user_with_client["access_token"]

        response = client.get(
            "/auth/login",
            cookies={"access_token": access_token},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/"

    def test_login_page_served_when_no_cookie(self, api_client: TestClient):
        """GET /auth/login without a cookie should serve the login page normally."""
        response = api_client.get("/auth/login")
        assert response.status_code == 200

    def test_login_page_served_when_invalid_cookie(self, api_client: TestClient):
        """GET /auth/login with an invalid token cookie should serve login page."""
        response = api_client.get(
            "/auth/login",
            cookies={"access_token": "invalid.token.here"},
        )
        assert response.status_code == 200


@require_auth
class TestHomeRouteRedirectCacheHeaders:
    """Tests for cache-control headers on the home route redirect."""

    def test_home_redirect_has_no_store_cache_control(self, api_client: TestClient):
        """GET / without auth should redirect with no-store cache headers."""
        response = api_client.get("/", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"
        cache_control = response.headers.get("cache-control", "")
        assert "no-store" in cache_control
        assert "no-cache" in cache_control

    def test_home_serves_app_when_authenticated(
        self, registered_user_with_client: Dict[str, Any]
    ):
        """GET / with an access_token cookie should serve the main app."""
        client: TestClient = registered_user_with_client["client"]
        access_token = registered_user_with_client["access_token"]

        response = client.get(
            "/",
            cookies={"access_token": access_token},
            follow_redirects=False,
        )

        assert response.status_code == 200