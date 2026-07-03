# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for optional (facultative) authentication via ``AUTH_ENABLED``.

These tests cover two concerns:

1. **Configuration** (always run): the ``auth_enabled`` field defaults to
   ``True`` and rejects invalid values with a ``ValidationError``.

2. **Anonymous mode** (only run when ``AUTH_ENABLED=false``): the auth/admin
   API routes are unmounted (404), data endpoints are publicly accessible, the
   home route serves the app without redirecting, and a startup warning is
   emitted.

To exercise the anonymous-mode tests run::

    AUTH_ENABLED=false pytest tests/test_auth_optional.py --no-cov
"""

import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.config.auth_config import AuthConfig, auth_settings


# ---------------------------------------------------------------------------
# Configuration tests (run in every environment)
# ---------------------------------------------------------------------------


def test_default_auth_enabled_is_true(monkeypatch):
    """``auth_enabled`` must default to ``True`` (backward compatible)."""
    monkeypatch.delenv("AUTH_ENABLED", raising=False)
    # Pass _env_file=None to prevent .env from overriding the field default.
    config = AuthConfig(_env_file=None)
    assert config.auth_enabled is True


def test_auth_enabled_accepts_false(monkeypatch):
    """``AUTH_ENABLED=false`` is parsed correctly."""
    monkeypatch.setenv("AUTH_ENABLED", "false")
    config = AuthConfig()
    assert config.auth_enabled is False


def test_invalid_auth_enabled_raises_validation_error(monkeypatch):
    """An unparseable ``AUTH_ENABLED`` value prevents startup."""
    monkeypatch.setenv("AUTH_ENABLED", "not-a-bool")
    with pytest.raises(ValidationError):
        AuthConfig()


# ---------------------------------------------------------------------------
# Anonymous-mode tests (skipped unless AUTH_ENABLED=false)
# ---------------------------------------------------------------------------

anonymous_only = pytest.mark.skipif(
    auth_settings.auth_enabled,
    reason="Requires AUTH_ENABLED=false (anonymous mode)",
)


@anonymous_only
class TestAnonymousMode:
    """Behavioral tests that only apply when authentication is disabled."""

    def test_prompts_accessible_without_credentials(self, api_client: TestClient):
        """``GET /api/prompts`` returns 200 with no credentials."""
        response = api_client.get("/api/prompts")
        assert response.status_code == 200

    def test_auth_login_returns_404_when_disabled(self, api_client: TestClient):
        """``POST /api/auth/login`` is unmounted (404) in anonymous mode."""
        response = api_client.post(
            "/api/auth/login",
            json={"username": "someone", "password": "whatever"},
        )
        assert response.status_code == 404

    def test_admin_users_returns_404_when_disabled(self, api_client: TestClient):
        """``GET /api/admin/users`` is unmounted (404) in anonymous mode."""
        response = api_client.get("/api/admin/users")
        assert response.status_code == 404

    def test_home_serves_app_without_redirect(self, api_client: TestClient):
        """``GET /`` serves the app (200) instead of redirecting to login."""
        response = api_client.get("/", follow_redirects=False)
        assert response.status_code == 200

    def test_startup_warning_logged(self, caplog):
        """A WARNING is emitted when authentication is disabled."""
        from src.web.app import _warn_if_auth_disabled

        # The "promptvault" logger has propagate=False, so attach caplog's
        # handler directly to it instead of relying on root propagation.
        pv_logger = logging.getLogger("promptvault")
        pv_logger.addHandler(caplog.handler)
        try:
            with caplog.at_level(logging.WARNING, logger="promptvault"):
                _warn_if_auth_disabled()
        finally:
            pv_logger.removeHandler(caplog.handler)

        assert any(
            "AUTH_ENABLED=false" in record.message for record in caplog.records
        )


# ---------------------------------------------------------------------------
# Enabled-mode sanity checks (skipped when AUTH_ENABLED=false)
# ---------------------------------------------------------------------------

enabled_only = pytest.mark.skipif(
    not auth_settings.auth_enabled,
    reason="Requires AUTH_ENABLED=true (default)",
)


@enabled_only
class TestEnabledModeSmoke:
    """Quick backward-compatibility checks for the default (auth enabled) mode."""

    def test_prompts_still_accessible(self, api_client: TestClient):
        """``GET /api/prompts`` remains public (200) when auth is enabled."""
        response = api_client.get("/api/prompts")
        assert response.status_code == 200

    def test_auth_routes_mounted(self, api_client: TestClient):
        """Auth endpoints are mounted (not 404) when auth is enabled."""
        # A GET on the login endpoint returns 405 (method not allowed) when
        # mounted, but 404 when unmounted.
        response = api_client.get("/api/auth/login")
        assert response.status_code != 404
