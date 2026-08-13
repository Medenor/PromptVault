# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Integration test: full TOTP 2FA enroll -> confirm -> recovery-codes flow
(User Story 1).

Exercises the enrollment endpoints end-to-end against a real in-memory
database, verifying the full lifecycle described in data-model.md and
contracts/totp-api.md §1-2: register -> enroll -> confirm -> recovery codes
issued exactly once -> re-enrollment is blocked while active.
"""

import importlib.util
import sys
from pathlib import Path

import pyotp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def auth_client(test_db_engine, temp_data_dir: str, monkeypatch):
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
        "auth_router_module_totp_integration", auth_module_path
    )
    auth_router_module = importlib.util.module_from_spec(spec)
    sys.modules["auth_router_module_totp_integration"] = auth_router_module
    spec.loader.exec_module(auth_router_module)
    auth_router = auth_router_module.router

    original_session_local = session_module.SessionLocal
    TestSessionLocal = sessionmaker(bind=test_db_engine)
    session_module.SessionLocal = TestSessionLocal

    app = FastAPI(title="PromptVault Auth TOTP Integration Test")
    app.include_router(auth_router, prefix="/api")

    client = TestClient(app)

    try:
        yield client
    finally:
        client.close()
        session_module.SessionLocal = original_session_local


def _register(client: TestClient) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "username": "integrationuser",
            "email": "integration@example.com",
            "password": "SecureP@ssw0rd123",
            "confirm_password": "SecureP@ssw0rd123",
        },
    )
    assert response.status_code == 201
    return response.json()


class TestFullEnrollmentFlow:
    def test_enroll_confirm_recovery_codes_end_to_end(self, auth_client: TestClient):
        user_data = _register(auth_client)
        headers = {"Authorization": f"Bearer {user_data['access_token']}"}

        # Step 1: user info shows 2FA not yet enabled.
        me_before = auth_client.get("/api/auth/me", headers=headers)
        assert me_before.status_code == 200

        # Step 2: start enrollment.
        enroll_response = auth_client.post("/api/auth/2fa/enroll", headers=headers)
        assert enroll_response.status_code == 201
        enroll_data = enroll_response.json()
        secret = enroll_data["secret"]
        assert enroll_data["provisioning_uri"].startswith("otpauth://totp/")
        assert "<svg" in enroll_data["qr_svg"]

        # Step 3: confirm with a valid TOTP code.
        code = pyotp.totp.TOTP(secret).now()
        confirm_response = auth_client.post(
            "/api/auth/2fa/verify", json={"code": code}, headers=headers
        )
        assert confirm_response.status_code == 200
        confirm_data = confirm_response.json()
        assert confirm_data["enabled"] is True

        recovery_codes = confirm_data["recovery_codes"]
        assert len(recovery_codes) == 10
        assert len(set(recovery_codes)) == 10
        for rc in recovery_codes:
            assert len(rc) == 9
            assert rc[4] == "-"

        # Step 4: re-enrollment is now blocked (2FA already active).
        second_enroll = auth_client.post("/api/auth/2fa/enroll", headers=headers)
        assert second_enroll.status_code == 409

    def test_recovery_codes_are_not_retrievable_again(self, auth_client: TestClient):
        user_data = _register(auth_client)
        headers = {"Authorization": f"Bearer {user_data['access_token']}"}

        enroll_response = auth_client.post("/api/auth/2fa/enroll", headers=headers)
        secret = enroll_response.json()["secret"]
        code = pyotp.totp.TOTP(secret).now()
        first_confirm = auth_client.post(
            "/api/auth/2fa/verify", json={"code": code}, headers=headers
        )
        assert first_confirm.status_code == 200

        # Confirming again (already-confirmed credential) is rejected, so
        # there is no way to re-fetch the recovery codes via this endpoint.
        second_confirm = auth_client.post(
            "/api/auth/2fa/verify", json={"code": code}, headers=headers
        )
        assert second_confirm.status_code == 400

    def test_wrong_code_does_not_advance_enrollment_state(
        self, auth_client: TestClient
    ):
        user_data = _register(auth_client)
        headers = {"Authorization": f"Bearer {user_data['access_token']}"}

        auth_client.post("/api/auth/2fa/enroll", headers=headers)
        wrong_confirm = auth_client.post(
            "/api/auth/2fa/verify", json={"code": "000000"}, headers=headers
        )
        assert wrong_confirm.status_code == 401

        # A fresh enroll attempt is still allowed (2FA was never activated).
        retry_enroll = auth_client.post("/api/auth/2fa/enroll", headers=headers)
        assert retry_enroll.status_code == 201
