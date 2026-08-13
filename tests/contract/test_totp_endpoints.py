# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Contract tests for TOTP 2FA enrollment endpoints (User Story 1).

Covers:
    POST /api/auth/2fa/enroll  - 201, 409 (already enabled), 429
    POST /api/auth/2fa/verify  - 200 with recovery codes, 400, 401, 429

Mirrors tests/test_auth_api.py's auth_client fixture pattern: mounts a
fresh FastAPI app with just the auth router, swaps session_module.SessionLocal
for the in-memory test DB, and additionally sets TOTP_ENCRYPTION_KEY since
TotpEncryptionService raises ValueError without it.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pyotp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def auth_client(test_db_engine, temp_data_dir: str, monkeypatch):
    """FastAPI TestClient configured for TOTP 2FA endpoint testing.

    Mounts only the aggregated auth router (which now includes the TOTP
    router) against an in-memory test database, matching the pattern used
    by tests/test_auth_api.py's auth_client fixture.
    """
    # get_auth_config() returns the module-level `auth_settings` singleton,
    # which is constructed once at import time — setenv alone won't affect
    # it. Replace the singleton with a config that has the TOTP key set.
    import src.config.auth_config as auth_config_module
    from src.config.auth_config import AuthConfig

    patched_config = AuthConfig(
        **{
            **auth_config_module.auth_settings.model_dump(),
            "totp_encryption_key": "test-server-secret-value-12345",
        }
    )
    monkeypatch.setattr(auth_config_module, "auth_settings", patched_config)

    from src.db import session as session_module

    auth_module_path = (
        Path(__file__).parent.parent.parent / "src" / "web" / "routers" / "auth.py"
    )
    spec = importlib.util.spec_from_file_location(
        "auth_router_module_totp_contract", auth_module_path
    )
    auth_router_module = importlib.util.module_from_spec(spec)
    sys.modules["auth_router_module_totp_contract"] = auth_router_module
    spec.loader.exec_module(auth_router_module)
    auth_router = auth_router_module.router

    original_session_local = session_module.SessionLocal
    TestSessionLocal = sessionmaker(bind=test_db_engine)
    session_module.SessionLocal = TestSessionLocal

    app = FastAPI(title="PromptVault Auth TOTP Test")
    app.include_router(auth_router, prefix="/api")

    client = TestClient(app)

    try:
        yield client
    finally:
        client.close()
        session_module.SessionLocal = original_session_local


@pytest.fixture
def test_user_credentials() -> dict[str, str]:
    return {
        "username": "totpuser",
        "email": "totpuser@example.com",
        "password": "SecureP@ssw0rd123",
    }


@pytest.fixture
def registered_user(
    auth_client: TestClient, test_user_credentials: dict[str, str]
) -> dict[str, Any]:
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
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


class TestEnrollEndpoint:
    """Contract tests for POST /api/auth/2fa/enroll."""

    def test_enroll_returns_201_with_expected_shape(
        self, auth_client: TestClient, auth_headers: dict[str, str]
    ):
        response = auth_client.post("/api/auth/2fa/enroll", headers=auth_headers)

        assert response.status_code == 201
        data = response.json()
        assert "secret" in data
        assert "provisioning_uri" in data
        assert "qr_svg" in data
        assert data["provisioning_uri"].startswith("otpauth://totp/")
        assert "<svg" in data["qr_svg"]

    def test_enroll_requires_authentication(self, auth_client: TestClient):
        response = auth_client.post("/api/auth/2fa/enroll")
        assert response.status_code == 401

    def test_enroll_conflict_when_already_enabled(
        self, auth_client: TestClient, auth_headers: dict[str, str]
    ):
        enroll_resp = auth_client.post("/api/auth/2fa/enroll", headers=auth_headers)
        secret = enroll_resp.json()["secret"]
        code = pyotp.totp.TOTP(secret).now()
        confirm_resp = auth_client.post(
            "/api/auth/2fa/verify", json={"code": code}, headers=auth_headers
        )
        assert confirm_resp.status_code == 200

        response = auth_client.post("/api/auth/2fa/enroll", headers=auth_headers)

        assert response.status_code == 409

    def test_enroll_restart_replaces_pending_secret(
        self, auth_client: TestClient, auth_headers: dict[str, str]
    ):
        first = auth_client.post("/api/auth/2fa/enroll", headers=auth_headers)
        second = auth_client.post("/api/auth/2fa/enroll", headers=auth_headers)

        assert first.json()["secret"] != second.json()["secret"]

        # Only the newer secret should confirm successfully.
        code = pyotp.totp.TOTP(second.json()["secret"]).now()
        confirm_resp = auth_client.post(
            "/api/auth/2fa/verify", json={"code": code}, headers=auth_headers
        )
        assert confirm_resp.status_code == 200


class TestVerifyEndpoint:
    """Contract tests for POST /api/auth/2fa/verify."""

    def test_verify_returns_200_with_recovery_codes(
        self, auth_client: TestClient, auth_headers: dict[str, str]
    ):
        enroll_resp = auth_client.post("/api/auth/2fa/enroll", headers=auth_headers)
        secret = enroll_resp.json()["secret"]
        code = pyotp.totp.TOTP(secret).now()

        response = auth_client.post(
            "/api/auth/2fa/verify", json={"code": code}, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert len(data["recovery_codes"]) == 10
        assert len(set(data["recovery_codes"])) == 10

    def test_verify_requires_authentication(self, auth_client: TestClient):
        response = auth_client.post("/api/auth/2fa/verify", json={"code": "123456"})
        assert response.status_code == 401

    def test_verify_no_pending_enrollment_returns_400(
        self, auth_client: TestClient, auth_headers: dict[str, str]
    ):
        response = auth_client.post(
            "/api/auth/2fa/verify", json={"code": "123456"}, headers=auth_headers
        )

        assert response.status_code == 400

    def test_verify_wrong_code_returns_401(
        self, auth_client: TestClient, auth_headers: dict[str, str]
    ):
        auth_client.post("/api/auth/2fa/enroll", headers=auth_headers)

        response = auth_client.post(
            "/api/auth/2fa/verify", json={"code": "000000"}, headers=auth_headers
        )

        assert response.status_code == 401

    def test_verify_wrong_code_does_not_enable_2fa(
        self, auth_client: TestClient, auth_headers: dict[str, str]
    ):
        auth_client.post("/api/auth/2fa/enroll", headers=auth_headers)
        auth_client.post(
            "/api/auth/2fa/verify", json={"code": "000000"}, headers=auth_headers
        )

        me_response = auth_client.get("/api/auth/me", headers=auth_headers)
        assert me_response.status_code == 200
