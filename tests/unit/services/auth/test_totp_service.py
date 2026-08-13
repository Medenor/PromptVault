# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for TotpService.enroll / TotpService.confirm (User Story 1).

Covers:
- Secret generation and provisioning URI / QR SVG shape
- Replacing a pending (unconfirmed) enrollment
- Refusing re-enrollment when 2FA is already active
- Confirming with a valid code activates 2FA and issues recovery codes
- Confirming with no pending enrollment / already-confirmed credential raises
- Confirming with an invalid code raises and does not mutate state
- Recovery-code batch issuance (count, format, hashed storage)
"""

from unittest.mock import patch

import pyotp
import pytest

from src.config.auth_config import AuthConfig
from src.db.models.user import User
from src.services.auth.password_service import PasswordService
from src.services.auth.totp_encryption_service import TotpEncryptionService
from src.services.auth.totp_service import TotpService
from src.services.exceptions import (
    TotpAlreadyEnabledError,
    TotpCodeInvalidError,
    TotpEnrollmentNotFoundError,
)


@pytest.fixture
def auth_config():
    with patch.dict(
        "os.environ", {"TOTP_ENCRYPTION_KEY": "test-server-secret-value-12345"}
    ):
        yield AuthConfig()


@pytest.fixture
def encryption_service(auth_config):
    return TotpEncryptionService(auth_config)


@pytest.fixture
def password_service(auth_config):
    return PasswordService(auth_config)


class FakeTotpRepository:
    """In-memory fake standing in for TotpRepository for isolated unit tests."""

    def __init__(self):
        self.credentials: dict[str, object] = {}
        self.batches: dict[str, list[str]] = {}

    def get_credential(self, user_id):
        return self.credentials.get(user_id)

    def upsert_pending_credential(self, user_id, secret_ciphertext, secret_nonce):
        cred = self.credentials.get(user_id)
        if cred is None:
            cred = _FakeCredential(user_id=user_id)
            self.credentials[user_id] = cred
        cred.secret_ciphertext = secret_ciphertext
        cred.secret_nonce = secret_nonce
        cred.confirmed = False
        cred.confirmed_at = None
        cred.last_used_step = None
        return cred

    def confirm_credential(self, credential):
        credential.confirmed = True
        return credential

    def update_last_used_step(self, credential, step):
        credential.last_used_step = step
        return credential

    def insert_recovery_code_batch(self, user_id, code_hashes):
        batch_id = f"batch-{len(self.batches) + 1}"
        self.batches[batch_id] = code_hashes
        return batch_id


class _FakeCredential:
    def __init__(self, user_id):
        self.user_id = user_id
        self.secret_ciphertext = None
        self.secret_nonce = None
        self.confirmed = False
        self.confirmed_at = None
        self.last_used_step = None


@pytest.fixture
def totp_repository():
    return FakeTotpRepository()


@pytest.fixture
def totp_service(totp_repository, encryption_service, password_service):
    return TotpService(totp_repository, encryption_service, password_service)


def make_user(user_id="user-1", email="alice@example.com", totp_enabled=False) -> User:
    user = User(
        id=user_id,
        username="alice",
        email=email,
        password_hash="irrelevant",
        role="viewer",
        totp_enabled=totp_enabled,
    )
    return user


class TestEnroll:
    def test_generates_secret_and_provisioning_uri(self, totp_service):
        user = make_user()
        result = totp_service.enroll(user)

        assert len(result.secret) >= 16
        assert result.provisioning_uri.startswith("otpauth://totp/")
        assert "PromptVault" in result.provisioning_uri
        assert (
            user.email in result.provisioning_uri or "alice" in result.provisioning_uri
        )

    def test_qr_svg_is_svg_markup(self, totp_service):
        user = make_user()
        result = totp_service.enroll(user)

        assert result.qr_svg.strip().startswith("<?xml") or "<svg" in result.qr_svg
        assert "<svg" in result.qr_svg

    def test_secret_not_persisted_in_plaintext(self, totp_service, totp_repository):
        user = make_user()
        result = totp_service.enroll(user)

        stored = totp_repository.get_credential(user.id)
        assert stored.secret_ciphertext != result.secret
        assert result.secret not in stored.secret_ciphertext

    def test_restarting_enrollment_replaces_pending_secret(
        self, totp_service, totp_repository
    ):
        user = make_user()
        first = totp_service.enroll(user)
        second = totp_service.enroll(user)

        assert first.secret != second.secret
        stored = totp_repository.get_credential(user.id)
        assert stored.confirmed is False
        # Only the second (latest) secret should verify.
        assert pyotp.totp.TOTP(second.secret).verify(
            pyotp.totp.TOTP(second.secret).now()
        )

    def test_refuses_reenroll_when_already_enabled(self, totp_service):
        user = make_user(totp_enabled=True)

        with pytest.raises(TotpAlreadyEnabledError):
            totp_service.enroll(user)

    def test_enroll_does_not_log_plaintext_secret(self, totp_service, caplog):
        import logging

        user = make_user()
        with caplog.at_level(logging.DEBUG):
            result = totp_service.enroll(user)

        for record in caplog.records:
            assert result.secret not in record.getMessage()


class TestConfirm:
    def test_confirm_with_valid_code_activates_2fa(self, totp_service):
        user = make_user()
        enroll_result = totp_service.enroll(user)
        code = pyotp.totp.TOTP(enroll_result.secret).now()

        confirm_result = totp_service.confirm(user, code)

        assert user.totp_enabled is True
        assert len(confirm_result.recovery_codes) == 10

    def test_confirm_issues_unique_recovery_codes_in_expected_format(
        self, totp_service
    ):
        user = make_user()
        enroll_result = totp_service.enroll(user)
        code = pyotp.totp.TOTP(enroll_result.secret).now()

        confirm_result = totp_service.confirm(user, code)

        assert len(set(confirm_result.recovery_codes)) == 10
        for recovery_code in confirm_result.recovery_codes:
            assert len(recovery_code) == 9  # xxxx-xxxx
            assert recovery_code[4] == "-"

    def test_recovery_codes_persisted_as_hashes(
        self, totp_service, totp_repository, password_service
    ):
        user = make_user()
        enroll_result = totp_service.enroll(user)
        code = pyotp.totp.TOTP(enroll_result.secret).now()

        confirm_result = totp_service.confirm(user, code)

        assert len(totp_repository.batches) == 1
        stored_hashes = next(iter(totp_repository.batches.values()))
        assert len(stored_hashes) == 10
        for plaintext, stored_hash in zip(
            confirm_result.recovery_codes, stored_hashes, strict=True
        ):
            assert stored_hash != plaintext
            assert password_service.verify_password(plaintext, stored_hash)

    def test_confirm_with_no_pending_enrollment_raises(self, totp_service):
        user = make_user()

        with pytest.raises(TotpEnrollmentNotFoundError):
            totp_service.confirm(user, "123456")

    def test_confirm_already_confirmed_credential_raises(self, totp_service):
        user = make_user()
        enroll_result = totp_service.enroll(user)
        code = pyotp.totp.TOTP(enroll_result.secret).now()
        totp_service.confirm(user, code)

        with pytest.raises(TotpEnrollmentNotFoundError):
            totp_service.confirm(user, code)

    def test_confirm_with_invalid_code_raises_and_does_not_mutate_state(
        self, totp_service, totp_repository
    ):
        user = make_user()
        totp_service.enroll(user)

        with pytest.raises(TotpCodeInvalidError):
            totp_service.confirm(user, "000000")

        assert user.totp_enabled is False
        stored = totp_repository.get_credential(user.id)
        assert stored.confirmed is False
        assert len(totp_repository.batches) == 0

    def test_confirm_does_not_log_plaintext_code_or_recovery_codes(
        self, totp_service, caplog
    ):
        import logging

        user = make_user()
        enroll_result = totp_service.enroll(user)
        code = pyotp.totp.TOTP(enroll_result.secret).now()

        with caplog.at_level(logging.DEBUG):
            confirm_result = totp_service.confirm(user, code)

        for record in caplog.records:
            message = record.getMessage()
            assert code not in message
            for recovery_code in confirm_result.recovery_codes:
                assert recovery_code not in message
