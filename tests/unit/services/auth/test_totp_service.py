# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for TotpService (User Stories 1 and 2).

Covers:
- Secret generation and provisioning URI / QR SVG shape
- Replacing a pending (unconfirmed) enrollment
- Refusing re-enrollment when 2FA is already active
- Confirming with a valid code activates 2FA and issues recovery codes
- Confirming with no pending enrollment / already-confirmed credential raises
- Confirming with an invalid code raises and does not mutate state
- Recovery-code batch issuance (count, format, hashed storage)
- Login-challenge issuance and exchange (replay guard, single-use recovery
  codes, expiry) — User Story 2
"""

import time
from unittest.mock import patch

import pyotp
import pytest

from src.config.auth_config import AuthConfig
from src.db.models.user import User
from src.services.auth.jwt_service import JWTService
from src.services.auth.password_service import PasswordService
from src.services.auth.totp_encryption_service import TotpEncryptionService
from src.services.auth.totp_service import TotpService
from src.services.exceptions import (
    TotpAlreadyEnabledError,
    TotpChallengeExpiredError,
    TotpCodeInvalidError,
    TotpEnrollmentNotFoundError,
    TotpReauthFailedError,
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
        self.recovery_codes: dict[str, list["_FakeRecoveryCode"]] = {}
        self.challenges: dict[str, "_FakeChallenge"] = {}
        self.users: dict[str, User] = {}

    def register_user(self, user: User) -> None:
        self.users[user.id] = user

    def get_credential(self, user_id):
        return self.credentials.get(user_id)

    def upsert_pending_credential(self, user_id, secret_ciphertext, secret_nonce):
        cred = self.credentials.get(user_id)
        if cred is None:
            cred = _FakeCredential(user_id=user_id, repo=self)
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

    def advance_last_used_step(self, credential, step):
        if credential.last_used_step is not None and credential.last_used_step >= step:
            return False
        credential.last_used_step = step
        return True

    def insert_recovery_code_batch(self, user_id, code_hashes):
        batch_id = f"batch-{len(self.batches) + 1}"
        self.batches[batch_id] = code_hashes
        self.recovery_codes[user_id] = [
            _FakeRecoveryCode(user_id=user_id, code_hash=h, repo=self)
            for h in code_hashes
        ]
        return batch_id

    def get_latest_batch_codes(self, user_id):
        return self.recovery_codes.get(user_id, [])

    def mark_recovery_code_used(self, code):
        from datetime import UTC, datetime

        code.used_at = datetime.now(UTC)
        return code

    def claim_recovery_code(self, code):
        from datetime import UTC, datetime

        if code.used_at is not None:
            return False
        code.used_at = datetime.now(UTC)
        return True

    def delete_credential(self, user_id):
        existed = self.credentials.pop(user_id, None) is not None
        return existed

    def delete_all_recovery_codes(self, user_id):
        count = len(self.recovery_codes.get(user_id, []))
        self.recovery_codes[user_id] = []
        return count

    def create_login_challenge(self, challenge_id, user_id, expires_at):
        challenge = _FakeChallenge(
            id=challenge_id, user_id=user_id, expires_at=expires_at
        )
        self.challenges[challenge_id] = challenge
        return challenge

    def get_valid_challenge(self, challenge_id):
        from datetime import UTC, datetime

        challenge = self.challenges.get(challenge_id)
        if challenge is None:
            return None
        if challenge.consumed_at is not None:
            return None
        if challenge.expires_at <= datetime.now(UTC):
            return None
        return challenge

    def consume_challenge(self, challenge):
        from datetime import UTC, datetime

        if challenge.consumed_at is not None:
            return False
        challenge.consumed_at = datetime.now(UTC)
        return True

    def delete_expired_challenges(self):
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        expired = [k for k, c in self.challenges.items() if c.expires_at <= now]
        for key in expired:
            del self.challenges[key]
        return len(expired)


class _FakeCredential:
    def __init__(self, user_id, repo: FakeTotpRepository):
        self.user_id = user_id
        self.secret_ciphertext = None
        self.secret_nonce = None
        self.confirmed = False
        self.confirmed_at = None
        self.last_used_step = None
        self._repo = repo

    @property
    def user(self) -> User:
        return self._repo.users[self.user_id]


class _FakeRecoveryCode:
    def __init__(self, user_id, code_hash, repo: FakeTotpRepository):
        self.user_id = user_id
        self.code_hash = code_hash
        self.used_at = None
        self._repo = repo

    @property
    def user(self) -> User:
        return self._repo.users[self.user_id]


class _FakeChallenge:
    def __init__(self, id, user_id, expires_at):
        self.id = id
        self.user_id = user_id
        self.expires_at = expires_at
        self.consumed_at = None


@pytest.fixture
def totp_repository():
    return FakeTotpRepository()


@pytest.fixture
def jwt_service(auth_config, tmp_path):
    """JWTService backed by freshly generated, temp-file ES256 test keys."""
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_key_path = tmp_path / "test_private_key.pem"
    public_key_path = tmp_path / "test_public_key.pem"
    private_key_path.write_bytes(private_pem)
    public_key_path.write_bytes(public_pem)

    config = AuthConfig(
        **{
            **auth_config.model_dump(),
            "jwt_private_key_path": str(private_key_path),
            "jwt_public_key_path": str(public_key_path),
        }
    )
    return JWTService(config)


@pytest.fixture
def totp_service(totp_repository, encryption_service, password_service, jwt_service):
    return TotpService(
        totp_repository, encryption_service, password_service, jwt_service
    )


def make_user(
    user_id="user-1",
    email="alice@example.com",
    totp_enabled=False,
    repository: FakeTotpRepository | None = None,
    password_hash: str = "irrelevant",
) -> User:
    user = User(
        id=user_id,
        username="alice",
        email=email,
        password_hash=password_hash,
        role="viewer",
        totp_enabled=totp_enabled,
    )
    if repository is not None:
        repository.register_user(user)
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


def _enroll_and_confirm(totp_service, totp_repository, user):
    """Enroll + confirm 2FA for user, returning (secret, recovery_codes)."""
    enroll_result = totp_service.enroll(user)
    code = pyotp.totp.TOTP(enroll_result.secret).now()
    confirm_result = totp_service.confirm(user, code)
    return enroll_result.secret, confirm_result.recovery_codes


def _next_window_code(secret: str) -> str:
    """A TOTP code for a step guaranteed later than the one confirm() used."""
    totp = pyotp.totp.TOTP(secret)
    return totp.at(time.time() + totp.interval)


class TestIssueLoginChallenge:
    def test_issues_challenge_token_and_creates_challenge_row(
        self, totp_service, totp_repository
    ):
        user = make_user(repository=totp_repository)
        _enroll_and_confirm(totp_service, totp_repository, user)

        result = totp_service.issue_login_challenge(user)

        assert result.challenge_token
        assert result.expires_in == 120
        assert len(totp_repository.challenges) == 1

    def test_raises_without_jwt_service(
        self, totp_repository, encryption_service, password_service
    ):
        service = TotpService(totp_repository, encryption_service, password_service)
        user = make_user(repository=totp_repository)

        with pytest.raises(RuntimeError):
            service.issue_login_challenge(user)


class TestExchangeChallenge:
    def test_valid_totp_code_returns_user_and_consumes_challenge(
        self, totp_service, totp_repository
    ):
        user = make_user(repository=totp_repository)
        secret, _ = _enroll_and_confirm(totp_service, totp_repository, user)
        challenge = totp_service.issue_login_challenge(user)

        code = _next_window_code(secret)
        result = totp_service.exchange_challenge(challenge.challenge_token, code)

        assert result.user.id == user.id
        assert result.used_recovery_code is False
        (stored_challenge,) = totp_repository.challenges.values()
        assert stored_challenge.consumed_at is not None

    def test_valid_recovery_code_returns_user_and_marks_code_used(
        self, totp_service, totp_repository
    ):
        user = make_user(repository=totp_repository)
        _secret, recovery_codes = _enroll_and_confirm(
            totp_service, totp_repository, user
        )
        challenge = totp_service.issue_login_challenge(user)

        result = totp_service.exchange_challenge(
            challenge.challenge_token, recovery_codes[0]
        )

        assert result.user.id == user.id
        assert result.used_recovery_code is True
        stored_codes = totp_repository.get_latest_batch_codes(user.id)
        assert stored_codes[0].used_at is not None

    def test_recovery_code_is_single_use(self, totp_service, totp_repository):
        user = make_user(repository=totp_repository)
        _secret, recovery_codes = _enroll_and_confirm(
            totp_service, totp_repository, user
        )

        first_challenge = totp_service.issue_login_challenge(user)
        totp_service.exchange_challenge(
            first_challenge.challenge_token, recovery_codes[0]
        )

        second_challenge = totp_service.issue_login_challenge(user)
        with pytest.raises(TotpCodeInvalidError):
            totp_service.exchange_challenge(
                second_challenge.challenge_token, recovery_codes[0]
            )

    def test_replay_of_same_code_step_is_rejected(self, totp_service, totp_repository):
        user = make_user(repository=totp_repository)
        secret, _ = _enroll_and_confirm(totp_service, totp_repository, user)

        code = _next_window_code(secret)
        first_challenge = totp_service.issue_login_challenge(user)
        totp_service.exchange_challenge(first_challenge.challenge_token, code)

        second_challenge = totp_service.issue_login_challenge(user)
        with pytest.raises(TotpCodeInvalidError):
            totp_service.exchange_challenge(second_challenge.challenge_token, code)

    def test_wrong_code_raises_totp_code_invalid(self, totp_service, totp_repository):
        user = make_user(repository=totp_repository)
        _enroll_and_confirm(totp_service, totp_repository, user)
        challenge = totp_service.issue_login_challenge(user)

        with pytest.raises(TotpCodeInvalidError):
            totp_service.exchange_challenge(challenge.challenge_token, "000000")

    def test_wrong_code_does_not_consume_challenge(self, totp_service, totp_repository):
        user = make_user(repository=totp_repository)
        _enroll_and_confirm(totp_service, totp_repository, user)
        challenge = totp_service.issue_login_challenge(user)

        with pytest.raises(TotpCodeInvalidError):
            totp_service.exchange_challenge(challenge.challenge_token, "000000")

        (stored_challenge,) = totp_repository.challenges.values()
        assert stored_challenge.consumed_at is None

    def test_expired_challenge_raises_totp_challenge_expired(
        self, totp_service, totp_repository
    ):
        from datetime import UTC, datetime, timedelta

        user = make_user(repository=totp_repository)
        secret, _ = _enroll_and_confirm(totp_service, totp_repository, user)
        challenge = totp_service.issue_login_challenge(user)

        # Force the server-side row to already be expired.
        (stored_challenge,) = totp_repository.challenges.values()
        stored_challenge.expires_at = datetime.now(UTC) - timedelta(seconds=1)

        code = _next_window_code(secret)
        with pytest.raises(TotpChallengeExpiredError):
            totp_service.exchange_challenge(challenge.challenge_token, code)

    def test_consumed_challenge_cannot_be_reused(self, totp_service, totp_repository):
        user = make_user(repository=totp_repository)
        secret, _ = _enroll_and_confirm(totp_service, totp_repository, user)
        challenge = totp_service.issue_login_challenge(user)

        code = _next_window_code(secret)
        totp_service.exchange_challenge(challenge.challenge_token, code)

        replay_code = pyotp.totp.TOTP(secret).at(time.time() + 2 * 30)
        with pytest.raises(TotpChallengeExpiredError):
            totp_service.exchange_challenge(challenge.challenge_token, replay_code)

    def test_malformed_challenge_token_raises_totp_challenge_expired(
        self, totp_service
    ):
        with pytest.raises(TotpChallengeExpiredError):
            totp_service.exchange_challenge("not-a-real-token", "123456")

    def test_raises_without_jwt_service(
        self, totp_repository, encryption_service, password_service
    ):
        service = TotpService(totp_repository, encryption_service, password_service)

        with pytest.raises(RuntimeError):
            service.exchange_challenge("token", "123456")


PASSWORD = "SecureP@ssw0rd123"


def _make_enrolled_user(totp_service, totp_repository, password_service):
    """Register, enroll, and confirm 2FA for a user with a real password hash."""
    user = make_user(
        repository=totp_repository,
        password_hash=password_service.hash_password(PASSWORD),
    )
    secret, recovery_codes = _enroll_and_confirm(totp_service, totp_repository, user)
    return user, secret, recovery_codes


class TestDisable:
    def test_disable_with_valid_password_and_code_disables_2fa(
        self, totp_service, totp_repository, password_service
    ):
        user, secret, _ = _make_enrolled_user(
            totp_service, totp_repository, password_service
        )
        code = _next_window_code(secret)

        totp_service.disable(user, PASSWORD, code)

        assert user.totp_enabled is False

    def test_disable_deletes_credential_and_recovery_codes(
        self, totp_service, totp_repository, password_service
    ):
        user, secret, _ = _make_enrolled_user(
            totp_service, totp_repository, password_service
        )
        code = _next_window_code(secret)

        totp_service.disable(user, PASSWORD, code)

        assert totp_repository.get_credential(user.id) is None
        assert totp_repository.get_latest_batch_codes(user.id) == []

    def test_disable_with_recovery_code_also_works(
        self, totp_service, totp_repository, password_service
    ):
        user, _secret, recovery_codes = _make_enrolled_user(
            totp_service, totp_repository, password_service
        )

        totp_service.disable(user, PASSWORD, recovery_codes[0])

        assert user.totp_enabled is False

    def test_disable_with_wrong_password_raises_generic_error(
        self, totp_service, totp_repository, password_service
    ):
        user, secret, _ = _make_enrolled_user(
            totp_service, totp_repository, password_service
        )
        code = _next_window_code(secret)

        with pytest.raises(TotpReauthFailedError):
            totp_service.disable(user, "WrongPassword123!", code)

        assert user.totp_enabled is True

    def test_disable_with_wrong_code_raises_generic_error(
        self, totp_service, totp_repository, password_service
    ):
        user, _secret, _ = _make_enrolled_user(
            totp_service, totp_repository, password_service
        )

        with pytest.raises(TotpReauthFailedError):
            totp_service.disable(user, PASSWORD, "000000")

        assert user.totp_enabled is True
        assert totp_repository.get_credential(user.id) is not None


class TestRegenerateRecoveryCodes:
    def test_regenerate_with_valid_password_and_code_returns_new_codes(
        self, totp_service, totp_repository, password_service
    ):
        user, secret, old_codes = _make_enrolled_user(
            totp_service, totp_repository, password_service
        )
        code = _next_window_code(secret)

        result = totp_service.regenerate_recovery_codes(user, PASSWORD, code)

        assert len(result.recovery_codes) == 10
        assert len(set(result.recovery_codes)) == 10
        assert set(result.recovery_codes).isdisjoint(old_codes)

    def test_regenerate_invalidates_old_codes(
        self, totp_service, totp_repository, password_service
    ):
        user, secret, old_codes = _make_enrolled_user(
            totp_service, totp_repository, password_service
        )
        code = _next_window_code(secret)

        totp_service.regenerate_recovery_codes(user, PASSWORD, code)

        challenge = totp_service.issue_login_challenge(user)
        with pytest.raises(TotpCodeInvalidError):
            totp_service.exchange_challenge(challenge.challenge_token, old_codes[0])

    def test_regenerate_new_codes_work(
        self, totp_service, totp_repository, password_service
    ):
        user, secret, _old_codes = _make_enrolled_user(
            totp_service, totp_repository, password_service
        )
        code = _next_window_code(secret)

        result = totp_service.regenerate_recovery_codes(user, PASSWORD, code)

        challenge = totp_service.issue_login_challenge(user)
        exchange_result = totp_service.exchange_challenge(
            challenge.challenge_token, result.recovery_codes[0]
        )
        assert exchange_result.user.id == user.id

    def test_regenerate_with_wrong_password_raises_generic_error(
        self, totp_service, totp_repository, password_service
    ):
        user, secret, old_codes = _make_enrolled_user(
            totp_service, totp_repository, password_service
        )
        code = _next_window_code(secret)

        with pytest.raises(TotpReauthFailedError):
            totp_service.regenerate_recovery_codes(user, "WrongPassword123!", code)

        # Old codes remain valid since regeneration never happened.
        challenge = totp_service.issue_login_challenge(user)
        exchange_result = totp_service.exchange_challenge(
            challenge.challenge_token, old_codes[0]
        )
        assert exchange_result.user.id == user.id

    def test_regenerate_with_wrong_code_raises_generic_error(
        self, totp_service, totp_repository, password_service
    ):
        user, _secret, _old_codes = _make_enrolled_user(
            totp_service, totp_repository, password_service
        )

        with pytest.raises(TotpReauthFailedError):
            totp_service.regenerate_recovery_codes(user, PASSWORD, "000000")


class TestSingleUseGuardsHoldUnderRaces:
    """A lost compare-and-set (a concurrent request won) must be rejected."""

    def test_lost_totp_step_race_is_rejected_as_invalid_code(
        self, totp_service, totp_repository
    ):
        user = make_user(repository=totp_repository)
        secret, _ = _enroll_and_confirm(totp_service, totp_repository, user)
        challenge = totp_service.issue_login_challenge(user)
        code = _next_window_code(secret)

        with patch.object(
            totp_repository, "advance_last_used_step", return_value=False
        ):
            with pytest.raises(TotpCodeInvalidError):
                totp_service.exchange_challenge(challenge.challenge_token, code)

        (stored,) = totp_repository.challenges.values()
        assert stored.consumed_at is None

    def test_lost_challenge_consume_race_returns_no_session(
        self, totp_service, totp_repository
    ):
        user = make_user(repository=totp_repository)
        secret, _ = _enroll_and_confirm(totp_service, totp_repository, user)
        challenge = totp_service.issue_login_challenge(user)
        code = _next_window_code(secret)

        with patch.object(totp_repository, "consume_challenge", return_value=False):
            with pytest.raises(TotpChallengeExpiredError):
                totp_service.exchange_challenge(challenge.challenge_token, code)

    def test_lost_recovery_code_claim_is_rejected(self, totp_service, totp_repository):
        user = make_user(repository=totp_repository)
        _secret, recovery_codes = _enroll_and_confirm(
            totp_service, totp_repository, user
        )
        challenge = totp_service.issue_login_challenge(user)

        with patch.object(totp_repository, "claim_recovery_code", return_value=False):
            with pytest.raises(TotpCodeInvalidError):
                totp_service.exchange_challenge(
                    challenge.challenge_token, recovery_codes[0]
                )


class TestCodeInputHandling:
    def test_non_ascii_code_is_rejected_not_a_type_error(
        self, totp_service, totp_repository
    ):
        user = make_user(repository=totp_repository)
        _enroll_and_confirm(totp_service, totp_repository, user)
        challenge = totp_service.issue_login_challenge(user)

        with pytest.raises(TotpCodeInvalidError):
            totp_service.exchange_challenge(challenge.challenge_token, "１２３４５６")

    def test_recovery_code_matching_is_case_insensitive(
        self, totp_service, totp_repository
    ):
        user = make_user(repository=totp_repository)
        _secret, recovery_codes = _enroll_and_confirm(
            totp_service, totp_repository, user
        )
        challenge = totp_service.issue_login_challenge(user)

        result = totp_service.exchange_challenge(
            challenge.challenge_token, f"  {recovery_codes[0].upper()} "
        )

        assert result.used_recovery_code is True

    def test_wrong_totp_code_does_not_trigger_argon2_verifications(
        self, totp_service, totp_repository, password_service
    ):
        user = make_user(repository=totp_repository)
        _enroll_and_confirm(totp_service, totp_repository, user)
        challenge = totp_service.issue_login_challenge(user)

        with patch.object(
            password_service, "verify_password", wraps=password_service.verify_password
        ) as verify:
            with pytest.raises(TotpCodeInvalidError):
                totp_service.exchange_challenge(challenge.challenge_token, "000000")

        verify.assert_not_called()


class TestRememberMeAndChallengePurge:
    def test_remember_me_is_carried_through_the_challenge(
        self, totp_service, totp_repository
    ):
        user = make_user(repository=totp_repository)
        secret, _ = _enroll_and_confirm(totp_service, totp_repository, user)
        challenge = totp_service.issue_login_challenge(user, remember_me=True)

        result = totp_service.exchange_challenge(
            challenge.challenge_token, _next_window_code(secret)
        )

        assert result.remember_me is True

    def test_remember_me_defaults_to_false(self, totp_service, totp_repository):
        user = make_user(repository=totp_repository)
        secret, _ = _enroll_and_confirm(totp_service, totp_repository, user)
        challenge = totp_service.issue_login_challenge(user)

        result = totp_service.exchange_challenge(
            challenge.challenge_token, _next_window_code(secret)
        )

        assert result.remember_me is False

    def test_issuing_a_challenge_purges_expired_ones(
        self, totp_service, totp_repository
    ):
        from datetime import UTC, datetime, timedelta

        user = make_user(repository=totp_repository)
        _enroll_and_confirm(totp_service, totp_repository, user)
        totp_repository.create_login_challenge(
            "stale", user.id, datetime.now(UTC) - timedelta(minutes=5)
        )

        totp_service.issue_login_challenge(user)

        assert "stale" not in totp_repository.challenges


class TestReauthFailuresCountTowardLockout:
    def _service_with_lockout(
        self, totp_repository, encryption_service, password_service, jwt_service
    ):
        from unittest.mock import MagicMock

        lockout = MagicMock()
        service = TotpService(
            totp_repository,
            encryption_service,
            password_service,
            jwt_service,
            lockout,
        )
        return service, lockout

    def test_wrong_code_records_a_failure(
        self, totp_repository, encryption_service, password_service, jwt_service
    ):
        service, lockout = self._service_with_lockout(
            totp_repository, encryption_service, password_service, jwt_service
        )
        user, _secret, _ = _make_enrolled_user(
            service, totp_repository, password_service
        )

        with pytest.raises(TotpReauthFailedError):
            service.disable(user, PASSWORD, "000000")

        lockout.record_2fa_challenge_failure.assert_called_once_with(user)

    def test_wrong_password_records_a_failure(
        self, totp_repository, encryption_service, password_service, jwt_service
    ):
        service, lockout = self._service_with_lockout(
            totp_repository, encryption_service, password_service, jwt_service
        )
        user, secret, _ = _make_enrolled_user(
            service, totp_repository, password_service
        )

        with pytest.raises(TotpReauthFailedError):
            service.regenerate_recovery_codes(
                user, "WrongPassword123!", _next_window_code(secret)
            )

        lockout.record_2fa_challenge_failure.assert_called_once_with(user)

    def test_successful_reauth_records_nothing(
        self, totp_repository, encryption_service, password_service, jwt_service
    ):
        service, lockout = self._service_with_lockout(
            totp_repository, encryption_service, password_service, jwt_service
        )
        user, secret, _ = _make_enrolled_user(
            service, totp_repository, password_service
        )

        service.disable(user, PASSWORD, _next_window_code(secret))

        lockout.record_2fa_challenge_failure.assert_not_called()
