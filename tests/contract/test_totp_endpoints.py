# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Contract tests for TOTP 2FA endpoints (User Stories 1 and 2).

Covers:
    POST /api/auth/2fa/enroll  - 201, 409 (already enabled), 429
    POST /api/auth/2fa/verify  - 200 with recovery codes, 400, 401, 429
    POST /api/auth/login       - challenge-issuance branch (US2)
    POST /api/auth/login/2fa   - 200, 401 (+lockout counting), 410, 423, 429

Mirrors tests/test_auth_api.py's auth_client fixture pattern: mounts a
fresh FastAPI app with just the auth router, swaps session_module.SessionLocal
for the in-memory test DB, and additionally sets TOTP_ENCRYPTION_KEY since
TotpEncryptionService raises ValueError without it.
"""

import importlib.util
import sys
import time
from pathlib import Path
from typing import Any

import pyotp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker


def _next_window_code(secret: str) -> str:
    """Generate a TOTP code for a time-step guaranteed later than "now".

    Enrollment confirmation (totp_enrolled_user) already consumes the
    current time-step as its last_used_step (FR-007 replay guard). Tests
    that need a *fresh* valid code afterwards must use one from a later
    step, or the replay guard correctly (and confusingly, for a naive test)
    rejects it.
    """
    totp = pyotp.totp.TOTP(secret)
    return totp.at(time.time() + totp.interval)


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

    def test_enroll_race_returns_409_not_500(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch,
    ):
        # Two concurrent enroll requests (double-click) race on the single
        # pending credential per user; the loser's UNIQUE violation must map
        # to 409 rather than a generic 500.
        from sqlalchemy.exc import IntegrityError

        from src.services.auth.totp_service import TotpService

        def _raise_integrity_error(self, user):
            raise IntegrityError(
                "INSERT INTO totp_credentials", {}, Exception("unique")
            )

        monkeypatch.setattr(TotpService, "enroll", _raise_integrity_error)

        response = auth_client.post("/api/auth/2fa/enroll", headers=auth_headers)

        assert response.status_code == 409
        assert "in progress" in response.json()["detail"].lower()

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


@pytest.fixture
def totp_enrolled_user(
    auth_client: TestClient,
    test_user_credentials: dict[str, str],
    auth_headers: dict[str, str],
) -> dict[str, Any]:
    """Enroll and confirm 2FA for the registered user, returning recovery codes."""
    enroll_resp = auth_client.post("/api/auth/2fa/enroll", headers=auth_headers)
    secret = enroll_resp.json()["secret"]
    code = pyotp.totp.TOTP(secret).now()
    confirm_resp = auth_client.post(
        "/api/auth/2fa/verify", json={"code": code}, headers=auth_headers
    )
    assert confirm_resp.status_code == 200
    return {
        "secret": secret,
        "recovery_codes": confirm_resp.json()["recovery_codes"],
    }


class TestLoginChallengeIssuance:
    """Contract tests for the POST /api/auth/login challenge-issuance branch (US2)."""

    def test_login_returns_challenge_shape_when_2fa_enabled(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "challenge_token" in data
        assert data["expires_in"] == 120
        assert "access_token" not in data
        assert "refresh_token" not in data

    def test_login_unchanged_when_2fa_not_enabled(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        registered_user: dict[str, Any],
    ):
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "challenge_token" not in data

    def test_login_401_on_bad_password_unaffected_by_2fa(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401


class TestLoginTwoFactorExchange:
    """Contract tests for POST /api/auth/login/2fa (US2)."""

    def _get_challenge_token(
        self, auth_client: TestClient, test_user_credentials: dict[str, str]
    ) -> str:
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )
        assert response.status_code == 200
        return response.json()["challenge_token"]

    def test_exchange_with_valid_totp_code_returns_tokens(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        challenge_token = self._get_challenge_token(auth_client, test_user_credentials)
        code = _next_window_code(totp_enrolled_user["secret"])

        response = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": code},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == test_user_credentials["username"]

    def test_exchange_with_valid_recovery_code_returns_tokens(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        challenge_token = self._get_challenge_token(auth_client, test_user_credentials)
        recovery_code = totp_enrolled_user["recovery_codes"][0]

        response = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": recovery_code},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_recovery_code_is_single_use(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        recovery_code = totp_enrolled_user["recovery_codes"][0]

        first_challenge = self._get_challenge_token(auth_client, test_user_credentials)
        first_response = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": first_challenge, "code": recovery_code},
        )
        assert first_response.status_code == 200

        second_challenge = self._get_challenge_token(auth_client, test_user_credentials)
        second_response = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": second_challenge, "code": recovery_code},
        )
        assert second_response.status_code == 401

    def test_exchange_wrong_code_returns_401(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        challenge_token = self._get_challenge_token(auth_client, test_user_credentials)

        response = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": "000000"},
        )

        assert response.status_code == 401

    def test_exchange_wrong_code_counts_toward_lockout(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        # Per spec Acceptance Scenario 3, a wrong code leaves the challenge
        # open for retry (until expiry/lockout) — so exhaust the shared
        # max_login_attempts=5 counter by retrying the SAME challenge.
        # Logging in again with the correct password would reset the
        # counter (reset_failed_login on password success), which is not
        # what we're testing here.
        challenge_token = self._get_challenge_token(auth_client, test_user_credentials)

        last_response = None
        for _ in range(5):
            last_response = auth_client.post(
                "/api/auth/login/2fa",
                json={"challenge_token": challenge_token, "code": "000000"},
            )

        # Once the shared lockout threshold is reached, the account is
        # locked and the response switches from 401 (invalid code) to
        # 423 (locked) per contracts/totp-api.md.
        assert last_response.status_code == 423

        # Even a correct password now reports the account as locked.
        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )
        assert login_response.status_code == 401

    def test_wrong_codes_across_fresh_logins_still_lock_account(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        # FR-010 regression: a correct password must not reset the shared
        # counter for a 2FA-enabled account. An attacker who knows the
        # password could otherwise re-login before every guess and never
        # reach the lockout threshold.
        statuses: list[int] = []
        for _ in range(6):
            login_response = auth_client.post(
                "/api/auth/login",
                json={
                    "username_or_email": test_user_credentials["username"],
                    "password": test_user_credentials["password"],
                },
            )
            if login_response.status_code != 200:
                statuses.append(login_response.status_code)
                break
            response = auth_client.post(
                "/api/auth/login/2fa",
                json={
                    "challenge_token": login_response.json()["challenge_token"],
                    "code": "000000",
                },
            )
            statuses.append(response.status_code)
            if response.status_code == 423:
                break

        # The loop only exits early once the account is locked (423 from the
        # exchange, or a refused password login); exhausting all 6 rounds
        # means the counter kept getting reset.
        assert len(statuses) < 6, f"account never locked: {statuses}"

    def test_exchange_consumed_challenge_returns_410(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        challenge_token = self._get_challenge_token(auth_client, test_user_credentials)
        code = _next_window_code(totp_enrolled_user["secret"])

        first = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": code},
        )
        assert first.status_code == 200

        second_code = pyotp.totp.TOTP(totp_enrolled_user["secret"]).now()
        replay = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": second_code},
        )
        assert replay.status_code == 410

    def test_exchange_malformed_challenge_token_returns_410(
        self, auth_client: TestClient
    ):
        response = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": "not-a-real-token", "code": "123456"},
        )
        assert response.status_code == 410


class TestDisableEndpoint:
    """Contract tests for POST /api/auth/2fa/disable."""

    def test_disable_with_valid_password_and_code_returns_204(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        code = _next_window_code(totp_enrolled_user["secret"])

        response = auth_client.post(
            "/api/auth/2fa/disable",
            json={"password": test_user_credentials["password"], "code": code},
            headers=auth_headers,
        )

        assert response.status_code == 204

    def test_disable_requires_authentication(self, auth_client: TestClient):
        response = auth_client.post(
            "/api/auth/2fa/disable", json={"password": "x", "code": "123456"}
        )
        assert response.status_code == 401

    def test_disable_with_wrong_password_returns_401(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        code = _next_window_code(totp_enrolled_user["secret"])

        response = auth_client.post(
            "/api/auth/2fa/disable",
            json={"password": "WrongPassword123!", "code": code},
            headers=auth_headers,
        )

        assert response.status_code == 401

    def test_disable_with_wrong_code_returns_401(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        response = auth_client.post(
            "/api/auth/2fa/disable",
            json={"password": test_user_credentials["password"], "code": "000000"},
            headers=auth_headers,
        )

        assert response.status_code == 401

    def test_disable_removes_2fa_and_login_no_longer_challenges(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        code = _next_window_code(totp_enrolled_user["secret"])
        disable_resp = auth_client.post(
            "/api/auth/2fa/disable",
            json={"password": test_user_credentials["password"], "code": code},
            headers=auth_headers,
        )
        assert disable_resp.status_code == 204

        login_resp = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()
        assert "challenge_token" not in login_resp.json()


class TestRegenerateRecoveryCodesEndpoint:
    """Contract tests for POST /api/auth/2fa/recovery-codes/regenerate."""

    def test_regenerate_with_valid_password_and_code_returns_new_codes(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        code = _next_window_code(totp_enrolled_user["secret"])

        response = auth_client.post(
            "/api/auth/2fa/recovery-codes/regenerate",
            json={"password": test_user_credentials["password"], "code": code},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["recovery_codes"]) == 10
        assert set(data["recovery_codes"]).isdisjoint(
            totp_enrolled_user["recovery_codes"]
        )

    def test_regenerate_requires_authentication(self, auth_client: TestClient):
        response = auth_client.post(
            "/api/auth/2fa/recovery-codes/regenerate",
            json={"password": "x", "code": "123456"},
        )
        assert response.status_code == 401

    def test_regenerate_with_wrong_password_returns_401(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        code = _next_window_code(totp_enrolled_user["secret"])

        response = auth_client.post(
            "/api/auth/2fa/recovery-codes/regenerate",
            json={"password": "WrongPassword123!", "code": code},
            headers=auth_headers,
        )

        assert response.status_code == 401

    def test_regenerate_invalidates_old_codes(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        code = _next_window_code(totp_enrolled_user["secret"])
        regen_resp = auth_client.post(
            "/api/auth/2fa/recovery-codes/regenerate",
            json={"password": test_user_credentials["password"], "code": code},
            headers=auth_headers,
        )
        assert regen_resp.status_code == 200

        login_resp = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )
        challenge_token = login_resp.json()["challenge_token"]

        old_code = totp_enrolled_user["recovery_codes"][0]
        exchange_resp = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": old_code},
        )
        assert exchange_resp.status_code == 401


@pytest.fixture
def admin_client(test_db_engine, temp_data_dir: str, monkeypatch):
    """FastAPI TestClient with both the auth router and the admin 2FA policy
    router mounted, for exercising GET/PUT /api/admin/2fa/policy (US4).
    """
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
        "auth_router_module_totp_policy_contract", auth_module_path
    )
    auth_router_module = importlib.util.module_from_spec(spec)
    sys.modules["auth_router_module_totp_policy_contract"] = auth_router_module
    spec.loader.exec_module(auth_router_module)
    auth_router = auth_router_module.router

    from src.web.routers.admin_totp_policy_router import (
        router as admin_totp_policy_router,
    )

    original_session_local = session_module.SessionLocal
    TestSessionLocal = sessionmaker(bind=test_db_engine)
    session_module.SessionLocal = TestSessionLocal

    app = FastAPI(title="PromptVault Auth TOTP Policy Test")
    app.include_router(auth_router, prefix="/api")
    app.include_router(admin_totp_policy_router, prefix="/api")

    client = TestClient(app)

    try:
        yield client
    finally:
        client.close()
        session_module.SessionLocal = original_session_local


def _promote_to_admin(test_db_engine, user_id: str) -> None:
    """Directly flip a test user's role to admin (bypassing the API)."""
    from src.db.models.user import User

    TestSessionLocal = sessionmaker(bind=test_db_engine)
    with TestSessionLocal() as session:
        user = session.get(User, user_id)
        user.role = "admin"
        session.commit()


class TestAdminTotpPolicyEndpoint:
    """Contract tests for GET/PUT /api/admin/2fa/policy (User Story 4)."""

    def test_get_policy_returns_all_roles_default_false(
        self,
        admin_client: TestClient,
        test_db_engine,
        registered_user: dict[str, Any],
        auth_headers: dict[str, str],
    ):
        _promote_to_admin(test_db_engine, registered_user["user"]["id"])
        # Role changed after token issuance; re-login to get an admin-scoped token.
        login_resp = admin_client.post(
            "/api/auth/login",
            json={
                "username_or_email": registered_user["user"]["username"],
                "password": "SecureP@ssw0rd123",
            },
        )
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        response = admin_client.get("/api/admin/2fa/policy", headers=headers)

        assert response.status_code == 200
        data = response.json()
        roles = {entry["role"]: entry["required"] for entry in data["roles"]}
        assert roles == {"viewer": False, "editor": False, "admin": False}

    def test_get_policy_requires_admin_role(
        self, admin_client: TestClient, auth_headers: dict[str, str]
    ):
        response = admin_client.get("/api/admin/2fa/policy", headers=auth_headers)
        assert response.status_code == 403

    def test_put_policy_updates_role(
        self,
        admin_client: TestClient,
        test_db_engine,
        registered_user: dict[str, Any],
    ):
        _promote_to_admin(test_db_engine, registered_user["user"]["id"])
        login_resp = admin_client.post(
            "/api/auth/login",
            json={
                "username_or_email": registered_user["user"]["username"],
                "password": "SecureP@ssw0rd123",
            },
        )
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        response = admin_client.put(
            "/api/admin/2fa/policy",
            json={"role": "admin", "required": True},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json() == {"role": "admin", "required": True}

        get_resp = admin_client.get("/api/admin/2fa/policy", headers=headers)
        roles = {entry["role"]: entry["required"] for entry in get_resp.json()["roles"]}
        assert roles["admin"] is True

    def test_put_policy_emits_audit_event(
        self,
        admin_client: TestClient,
        test_db_engine,
        registered_user: dict[str, Any],
        monkeypatch,
    ):
        from src.services import logging_service as logging_service_module

        events: list[dict[str, Any]] = []
        monkeypatch.setattr(
            logging_service_module.logging_service,
            "log_audit_event",
            lambda **kwargs: events.append(kwargs),
        )
        _promote_to_admin(test_db_engine, registered_user["user"]["id"])
        login_resp = admin_client.post(
            "/api/auth/login",
            json={
                "username_or_email": registered_user["user"]["username"],
                "password": "SecureP@ssw0rd123",
            },
        )
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
        events.clear()

        response = admin_client.put(
            "/api/admin/2fa/policy",
            json={"role": "editor", "required": True},
            headers=headers,
        )

        assert response.status_code == 200
        assert [e["action"] for e in events] == ["2fa.policy_updated"]
        assert events[0]["resource_id"] == "editor"
        assert events[0]["required"] is True

    def test_put_policy_requires_admin_role(
        self, admin_client: TestClient, auth_headers: dict[str, str]
    ):
        response = admin_client.put(
            "/api/admin/2fa/policy",
            json={"role": "admin", "required": True},
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_put_policy_unknown_role_returns_422(
        self,
        admin_client: TestClient,
        test_db_engine,
        registered_user: dict[str, Any],
    ):
        _promote_to_admin(test_db_engine, registered_user["user"]["id"])
        login_resp = admin_client.post(
            "/api/auth/login",
            json={
                "username_or_email": registered_user["user"]["username"],
                "password": "SecureP@ssw0rd123",
            },
        )
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        response = admin_client.put(
            "/api/admin/2fa/policy",
            json={"role": "superadmin", "required": True},
            headers=headers,
        )

        assert response.status_code == 422


class TestCodeReviewRegressions:
    """Regression tests for the post-review hardening of the 2FA flow."""

    @staticmethod
    def _login(
        auth_client: TestClient,
        creds: dict[str, str],
        remember_me: bool = False,
    ):
        return auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": creds["username"],
                "password": creds["password"],
                "remember_me": remember_me,
            },
        )

    def test_challenge_token_is_not_accepted_as_bearer_token(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        # A password-only login yields a challenge token; it must not
        # authenticate any request (it shares key, issuer and audience with
        # access tokens, so only the type check keeps it out).
        challenge_token = self._login(auth_client, test_user_credentials).json()[
            "challenge_token"
        ]

        response = auth_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {challenge_token}"}
        )

        assert response.status_code == 401

    def test_password_step_does_not_update_last_login_for_2fa_account(
        self,
        auth_client: TestClient,
        test_db_engine,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        from src.db.models.user import User

        Session = sessionmaker(bind=test_db_engine)

        def last_login():
            with Session() as session:
                return (
                    session.query(User)
                    .filter(User.username == test_user_credentials["username"])
                    .one()
                    .last_login
                )

        before = last_login()
        challenge_token = self._login(auth_client, test_user_credentials).json()[
            "challenge_token"
        ]
        assert last_login() == before

        code = _next_window_code(totp_enrolled_user["secret"])
        exchange = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": code},
        )
        assert exchange.status_code == 200
        assert last_login() != before

    def test_remember_me_survives_the_2fa_exchange(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        import src.config.auth_config as auth_config_module

        settings = auth_config_module.auth_settings
        challenge_token = self._login(
            auth_client, test_user_credentials, remember_me=True
        ).json()["challenge_token"]
        code = _next_window_code(totp_enrolled_user["secret"])

        response = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": code},
        )

        assert response.status_code == 200
        cookies = " ".join(response.headers.get_list("set-cookie"))
        assert (
            f"Max-Age={settings.jwt_refresh_token_remember_me_expire_seconds}"
            in cookies
        )

    def test_non_ascii_code_returns_401_not_500(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        challenge_token = self._login(auth_client, test_user_credentials).json()[
            "challenge_token"
        ]

        response = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": "１２３４５６"},
        )

        assert response.status_code == 401

    def test_uppercase_recovery_code_is_accepted(
        self,
        auth_client: TestClient,
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        challenge_token = self._login(auth_client, test_user_credentials).json()[
            "challenge_token"
        ]
        recovery_code = totp_enrolled_user["recovery_codes"][0].upper()

        response = auth_client.post(
            "/api/auth/login/2fa",
            json={"challenge_token": challenge_token, "code": recovery_code},
        )

        assert response.status_code == 200

    def test_failed_disable_attempts_count_toward_lockout(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        # FR-010: an attacker holding only an access token must not be able to
        # guess codes at the disable endpoint without ever locking the account.
        statuses: list[int] = []
        for _ in range(8):
            response = auth_client.post(
                "/api/auth/2fa/disable",
                json={
                    "password": test_user_credentials["password"],
                    "code": "000000",
                },
                headers=auth_headers,
            )
            statuses.append(response.status_code)
            if response.status_code != 401:
                break

        assert statuses[-1] != 401, f"account never locked: {statuses}"

    def test_failed_regenerate_attempts_count_toward_lockout(
        self,
        auth_client: TestClient,
        auth_headers: dict[str, str],
        test_user_credentials: dict[str, str],
        totp_enrolled_user: dict[str, Any],
    ):
        statuses: list[int] = []
        for _ in range(8):
            response = auth_client.post(
                "/api/auth/2fa/recovery-codes/regenerate",
                json={
                    "password": test_user_credentials["password"],
                    "code": "000000",
                },
                headers=auth_headers,
            )
            statuses.append(response.status_code)
            if response.status_code != 401:
                break

        assert statuses[-1] != 401, f"account never locked: {statuses}"
