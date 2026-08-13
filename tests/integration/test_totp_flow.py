# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Integration test: full TOTP 2FA flow (User Stories 1 and 2).

Exercises the enrollment and login-enforcement endpoints end-to-end against
a real in-memory database, verifying the full lifecycle described in
data-model.md and contracts/totp-api.md §1-2, §5-6:
    - register -> enroll -> confirm -> recovery codes issued exactly once
      -> re-enrollment is blocked while active (US1)
    - password -> challenge -> wrong code retry -> correct code -> tokens
    - recovery-code exchange (single-use)
    - expired challenge
    - code replay (US2)
"""

import importlib.util
import sys
import time
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


def _next_window_code(secret: str) -> str:
    """A TOTP code for a step guaranteed later than the one confirm() used."""
    totp = pyotp.totp.TOTP(secret)
    return totp.at(time.time() + totp.interval)


class TestLoginEnforcementFlow:
    """Integration coverage for User Story 2: 2FA-gated login."""

    LOGIN_PASSWORD = "SecureP@ssw0rd123"

    def _register_and_enroll(self, auth_client: TestClient) -> dict:
        user_data = _register(auth_client)
        headers = {"Authorization": f"Bearer {user_data['access_token']}"}

        enroll_response = auth_client.post("/api/auth/2fa/enroll", headers=headers)
        secret = enroll_response.json()["secret"]
        code = pyotp.totp.TOTP(secret).now()
        confirm_response = auth_client.post(
            "/api/auth/2fa/verify", json={"code": code}, headers=headers
        )
        assert confirm_response.status_code == 200

        return {
            "username": "integrationuser",
            "secret": secret,
            "recovery_codes": confirm_response.json()["recovery_codes"],
        }

    def test_password_challenge_wrong_then_correct_code_then_tokens(
        self, auth_client: TestClient
    ):
        enrolled = self._register_and_enroll(auth_client)

        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": enrolled["username"],
                "password": self.LOGIN_PASSWORD,
            },
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "challenge_token" in login_data
        assert "access_token" not in login_data
        challenge_token = login_data["challenge_token"]

        # Wrong code first — challenge stays open for retry.
        wrong_response = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": "000000"},
        )
        assert wrong_response.status_code == 401

        # Correct code on the SAME challenge succeeds.
        correct_code = _next_window_code(enrolled["secret"])
        success_response = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": correct_code},
        )
        assert success_response.status_code == 200
        success_data = success_response.json()
        assert "access_token" in success_data
        assert "refresh_token" in success_data
        assert success_data["user"]["username"] == enrolled["username"]

    def test_recovery_code_exchange(self, auth_client: TestClient):
        enrolled = self._register_and_enroll(auth_client)

        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": enrolled["username"],
                "password": self.LOGIN_PASSWORD,
            },
        )
        challenge_token = login_response.json()["challenge_token"]

        response = auth_client.post(
            "/api/auth/login/2fa",
            json={
                "challenge_token": challenge_token,
                "code": enrolled["recovery_codes"][0],
            },
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

        # The consumed recovery code cannot be reused on a fresh challenge.
        second_login = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": enrolled["username"],
                "password": self.LOGIN_PASSWORD,
            },
        )
        second_challenge = second_login.json()["challenge_token"]
        replay = auth_client.post(
            "/api/auth/login/2fa",
            json={
                "challenge_token": second_challenge,
                "code": enrolled["recovery_codes"][0],
            },
        )
        assert replay.status_code == 401

    def test_expired_challenge_rejected(self, auth_client: TestClient, monkeypatch):
        enrolled = self._register_and_enroll(auth_client)

        # Force newly-issued challenges to already be expired by patching
        # the TTL used at issuance to a negative window.
        import src.services.auth.totp_service as totp_service_module

        monkeypatch.setattr(totp_service_module, "LOGIN_CHALLENGE_TTL_SECONDS", -10)

        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": enrolled["username"],
                "password": self.LOGIN_PASSWORD,
            },
        )
        challenge_token = login_response.json()["challenge_token"]

        code = _next_window_code(enrolled["secret"])
        response = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": code},
        )
        assert response.status_code == 410

    def test_challenge_replay_after_success_rejected(self, auth_client: TestClient):
        enrolled = self._register_and_enroll(auth_client)

        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": enrolled["username"],
                "password": self.LOGIN_PASSWORD,
            },
        )
        challenge_token = login_response.json()["challenge_token"]

        first_code = _next_window_code(enrolled["secret"])
        first = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": first_code},
        )
        assert first.status_code == 200

        second_code = pyotp.totp.TOTP(enrolled["secret"]).at(
            time.time() + 2 * pyotp.totp.TOTP(enrolled["secret"]).interval
        )
        replay = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": second_code},
        )
        assert replay.status_code == 410

    def test_non_enrolled_user_login_unaffected(self, auth_client: TestClient):
        _register(auth_client)
        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": "integrationuser",
                "password": self.LOGIN_PASSWORD,
            },
        )
        assert login_response.status_code == 200
        data = login_response.json()
        assert "access_token" in data
        assert "challenge_token" not in data


class TestDisableAndRegenerateFlow:
    """Integration coverage for User Story 3: disable 2FA and regenerate codes."""

    LOGIN_PASSWORD = "SecureP@ssw0rd123"

    def _register_and_enroll(self, auth_client: TestClient) -> dict:
        user_data = _register(auth_client)
        headers = {"Authorization": f"Bearer {user_data['access_token']}"}

        enroll_response = auth_client.post("/api/auth/2fa/enroll", headers=headers)
        secret = enroll_response.json()["secret"]
        code = pyotp.totp.TOTP(secret).now()
        confirm_response = auth_client.post(
            "/api/auth/2fa/verify", json={"code": code}, headers=headers
        )
        assert confirm_response.status_code == 200

        return {
            "username": "integrationuser",
            "headers": headers,
            "secret": secret,
            "recovery_codes": confirm_response.json()["recovery_codes"],
        }

    def test_enroll_disable_login_shows_no_challenge(self, auth_client: TestClient):
        enrolled = self._register_and_enroll(auth_client)
        code = _next_window_code(enrolled["secret"])

        disable_response = auth_client.post(
            "/api/auth/2fa/disable",
            json={"password": self.LOGIN_PASSWORD, "code": code},
            headers=enrolled["headers"],
        )
        assert disable_response.status_code == 204

        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": enrolled["username"],
                "password": self.LOGIN_PASSWORD,
            },
        )
        assert login_response.status_code == 200
        data = login_response.json()
        assert "access_token" in data
        assert "challenge_token" not in data

    def test_enroll_regenerate_old_code_fails_new_code_works(
        self, auth_client: TestClient
    ):
        enrolled = self._register_and_enroll(auth_client)
        code = _next_window_code(enrolled["secret"])

        regen_response = auth_client.post(
            "/api/auth/2fa/recovery-codes/regenerate",
            json={"password": self.LOGIN_PASSWORD, "code": code},
            headers=enrolled["headers"],
        )
        assert regen_response.status_code == 200
        new_codes = regen_response.json()["recovery_codes"]
        assert set(new_codes).isdisjoint(enrolled["recovery_codes"])

        # Old recovery code no longer works.
        old_login = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": enrolled["username"],
                "password": self.LOGIN_PASSWORD,
            },
        )
        old_challenge = old_login.json()["challenge_token"]
        old_exchange = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": old_challenge, "code": enrolled["recovery_codes"][0]},
        )
        assert old_exchange.status_code == 401

        # New recovery code works.
        new_login = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": enrolled["username"],
                "password": self.LOGIN_PASSWORD,
            },
        )
        new_challenge = new_login.json()["challenge_token"]
        new_exchange = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": new_challenge, "code": new_codes[0]},
        )
        assert new_exchange.status_code == 200
