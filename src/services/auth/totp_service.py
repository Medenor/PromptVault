# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""TOTP two-factor authentication service for PromptVault.

Orchestrates enrollment and confirmation of TOTP-based 2FA (User Story 1):
generating a new secret, rendering the enrollment QR code, verifying the
user's confirmation code, and issuing one-time recovery codes.

Security:
    - The plaintext TOTP secret is never persisted; only the AES-256-GCM
      ciphertext (via TotpEncryptionService) is stored.
    - The plaintext secret and recovery codes are returned to the caller
      exactly once (at enroll / confirm time respectively) and never logged.
    - Recovery codes are hashed with the same Argon2id hasher used for
      passwords (PasswordService) before being persisted.

Commit convention:
    Following AuthService/PasswordResetService, this service does not commit
    the session itself — the caller (router) commits after a successful call,
    matching the session-per-request pattern used throughout the codebase.
"""

import logging
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta

import pyotp
from jwt.exceptions import InvalidTokenError as JWTInvalidTokenError

from src.db.models.user import User
from src.db.repositories.totp_repository import TotpRepository
from src.services.auth.jwt_service import JWTService
from src.services.auth.password_service import PasswordService
from src.services.auth.totp_encryption_service import TotpEncryptionService
from src.services.auth.totp_qr import render_qr_svg
from src.services.exceptions import (
    TotpAlreadyEnabledError,
    TotpChallengeExpiredError,
    TotpCodeInvalidError,
    TotpEnrollmentNotFoundError,
    TotpReauthFailedError,
)

logger = logging.getLogger(__name__)

ISSUER_NAME = "PromptVault"
RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
LOGIN_CHALLENGE_TTL_SECONDS = 120


class TotpEnrollResult:
    """Result of starting TOTP enrollment.

    Attributes:
        secret: Plaintext base32 TOTP secret (returned once, never stored)
        provisioning_uri: otpauth:// URI for authenticator apps
        qr_svg: Inline SVG QR code encoding provisioning_uri
    """

    def __init__(self, secret: str, provisioning_uri: str, qr_svg: str) -> None:
        self.secret = secret
        self.provisioning_uri = provisioning_uri
        self.qr_svg = qr_svg


class TotpConfirmResult:
    """Result of confirming TOTP enrollment.

    Attributes:
        recovery_codes: Plaintext recovery codes (returned once, never stored)
    """

    def __init__(self, recovery_codes: list[str]) -> None:
        self.recovery_codes = recovery_codes


class TotpChallengeResult:
    """Result of issuing a 2FA login challenge.

    Attributes:
        challenge_token: Signed, short-lived JWT identifying the challenge
        expires_in: Challenge lifetime in seconds
    """

    def __init__(self, challenge_token: str, expires_in: int) -> None:
        self.challenge_token = challenge_token
        self.expires_in = expires_in


class TotpCodeVerificationResult:
    """Result of verifying a TOTP or recovery code.

    Attributes:
        user: The user the code belongs to
        used_recovery_code: True if verified via a recovery code rather than
            a live TOTP code (used for audit-log event naming, FR-017)
    """

    def __init__(self, user: User, used_recovery_code: bool) -> None:
        self.user = user
        self.used_recovery_code = used_recovery_code


class TotpService:
    """Service for TOTP 2FA enrollment and confirmation.

    Attributes:
        totp_repository: Repository for TOTP persistence
        encryption_service: Service for encrypting/decrypting TOTP secrets
        password_service: Service for hashing recovery codes (Argon2id)
        jwt_service: Service for signing/validating 2FA login-challenge tokens
    """

    def __init__(
        self,
        totp_repository: TotpRepository,
        encryption_service: TotpEncryptionService,
        password_service: PasswordService,
        jwt_service: JWTService | None = None,
    ) -> None:
        """Initialize TotpService.

        Args:
            totp_repository: Repository for TOTP persistence
            encryption_service: Service for encrypting/decrypting TOTP secrets
            password_service: Service for hashing recovery codes (Argon2id)
            jwt_service: Service for 2FA login-challenge tokens (required for
                issue_login_challenge / exchange_challenge; optional so
                enrollment-only callers/tests need not construct one)
        """
        self.totp_repository = totp_repository
        self.encryption_service = encryption_service
        self.password_service = password_service
        self.jwt_service = jwt_service

    def enroll(self, user: User) -> TotpEnrollResult:
        """Start (or restart) TOTP enrollment for a user.

        Generates a fresh base32 secret, builds the otpauth:// provisioning
        URI, encrypts the secret at rest, and upserts a pending (unconfirmed)
        credential row — replacing any prior pending secret.

        Args:
            user: The authenticated user starting enrollment

        Returns:
            TotpEnrollResult with the plaintext secret, provisioning URI, and QR SVG

        Raises:
            TotpAlreadyEnabledError: If the user already has 2FA enabled (409)
        """
        if user.totp_enabled:
            raise TotpAlreadyEnabledError(
                context={"user_id": user.id},
            )

        secret = pyotp.random_base32()
        account_name = user.email or user.username
        provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=account_name, issuer_name=ISSUER_NAME
        )
        qr_svg = render_qr_svg(provisioning_uri)

        ciphertext, nonce = self.encryption_service.encrypt_secret(secret)
        self.totp_repository.upsert_pending_credential(user.id, ciphertext, nonce)

        logger.info(
            "TOTP enrollment started for user_id=%s",
            user.id,
        )

        return TotpEnrollResult(
            secret=secret,
            provisioning_uri=provisioning_uri,
            qr_svg=qr_svg,
        )

    def confirm(self, user: User, code: str) -> TotpConfirmResult:
        """Confirm a pending TOTP enrollment with a verification code.

        Verifies the code against the pending credential's decrypted secret
        (±1 time-step tolerance per FR-006). On success, marks the credential
        confirmed, enables 2FA on the user, and issues a fresh batch of
        recovery codes. State is never mutated on an invalid code.

        Args:
            user: The authenticated user confirming enrollment
            code: The 6-digit TOTP code from the user's authenticator app

        Returns:
            TotpConfirmResult with the plaintext recovery codes

        Raises:
            TotpEnrollmentNotFoundError: No pending enrollment exists (400)
            TotpCodeInvalidError: Code is incorrect or outside the valid window (401)
        """
        credential = self.totp_repository.get_credential(user.id)
        if credential is None or credential.confirmed:
            raise TotpEnrollmentNotFoundError(context={"user_id": user.id})

        secret = self.encryption_service.decrypt_secret(
            credential.secret_ciphertext, credential.secret_nonce
        )
        totp = pyotp.totp.TOTP(secret)
        if not totp.verify(code, valid_window=1):
            logger.info(
                "TOTP confirmation failed (invalid code) for user_id=%s", user.id
            )
            raise TotpCodeInvalidError(context={"user_id": user.id})

        self.totp_repository.confirm_credential(credential)
        current_step = int(time.time()) // totp.interval
        self.totp_repository.update_last_used_step(credential, current_step)
        user.totp_enabled = True

        plaintext_codes = self._generate_recovery_codes()
        hashes = [self.password_service.hash_password(c) for c in plaintext_codes]
        self.totp_repository.insert_recovery_code_batch(user.id, hashes)

        logger.info("TOTP 2FA enabled for user_id=%s", user.id)

        return TotpConfirmResult(recovery_codes=plaintext_codes)

    def disable(self, user: User, password: str, code: str) -> None:
        """Disable TOTP 2FA for a user, re-authenticated with password + code.

        Verifies the current password and a current TOTP-or-recovery code
        before deleting the credential and all recovery codes and flipping
        ``users.totp_enabled=False`` (FR-012). Failures are reported
        generically (neither factor's failure is distinguished) per
        contracts/totp-api.md §3.

        Args:
            user: The authenticated user requesting to disable 2FA
            password: The user's current password
            code: A current TOTP code or an unused recovery code

        Raises:
            TotpReauthFailedError: Password or code incorrect (401)
        """
        self._reauth(user, password, code)

        self.totp_repository.delete_credential(user.id)
        self.totp_repository.delete_all_recovery_codes(user.id)
        user.totp_enabled = False

        logger.info("TOTP 2FA disabled for user_id=%s", user.id)

    def regenerate_recovery_codes(
        self, user: User, password: str, code: str
    ) -> TotpConfirmResult:
        """Regenerate recovery codes, invalidating all previously issued codes.

        Verifies the current password and a current TOTP-or-recovery code,
        then deletes the existing recovery-code batch and issues a fresh
        batch of 10 (FR-013). Failures are reported generically per
        contracts/totp-api.md §4.

        Args:
            user: The authenticated user requesting regeneration
            password: The user's current password
            code: A current TOTP code or an unused recovery code

        Returns:
            TotpConfirmResult with the new plaintext recovery codes

        Raises:
            TotpReauthFailedError: Password or code incorrect (401)
        """
        self._reauth(user, password, code)

        self.totp_repository.delete_all_recovery_codes(user.id)
        plaintext_codes = self._generate_recovery_codes()
        hashes = [self.password_service.hash_password(c) for c in plaintext_codes]
        self.totp_repository.insert_recovery_code_batch(user.id, hashes)

        logger.info("TOTP recovery codes regenerated for user_id=%s", user.id)

        return TotpConfirmResult(recovery_codes=plaintext_codes)

    def _reauth(self, user: User, password: str, code: str) -> None:
        """Verify password + TOTP-or-recovery code, raising generically on failure.

        Shared by disable/regenerate (contracts/totp-api.md §3-4): neither
        endpoint reveals which factor was wrong, to avoid leaking which
        credential an attacker got right.

        Args:
            user: The authenticated user re-authenticating
            password: The user's current password
            code: A current TOTP code or an unused recovery code

        Raises:
            TotpReauthFailedError: Password or code incorrect (401)
        """
        if not self.password_service.verify_password(password, user.password_hash):
            logger.info("TOTP re-authentication failed (bad password) for user_id=%s", user.id)
            raise TotpReauthFailedError(context={"user_id": user.id})

        try:
            self._verify_totp_or_recovery_code(user.id, code)
        except TotpCodeInvalidError as e:
            raise TotpReauthFailedError(context={"user_id": user.id}) from e

    def issue_login_challenge(self, user: User) -> TotpChallengeResult:
        """Issue a short-lived 2FA login challenge for a totp_enabled user.

        Called after password validation succeeds for a user with
        ``totp_enabled=True``, in place of issuing full access/refresh
        tokens. Creates a server-side ``TotpLoginChallenge`` row (single-use
        tracking) and signs a matching JWT whose ``jti`` is the row's id.

        Args:
            user: The user who just passed password validation

        Returns:
            TotpChallengeResult with the signed challenge token and its TTL

        Raises:
            RuntimeError: If constructed without a JWTService
        """
        if self.jwt_service is None:
            raise RuntimeError("TotpService requires a JWTService to issue challenges")

        challenge_id = str(uuid.uuid4())
        expires_at = datetime.now(UTC) + timedelta(seconds=LOGIN_CHALLENGE_TTL_SECONDS)
        self.totp_repository.create_login_challenge(challenge_id, user.id, expires_at)

        challenge_token = self.jwt_service.generate_2fa_challenge_token(
            user_id=user.id,
            challenge_id=challenge_id,
            expires_in_seconds=LOGIN_CHALLENGE_TTL_SECONDS,
        )

        logger.info("2FA login challenge issued for user_id=%s", user.id)

        return TotpChallengeResult(
            challenge_token=challenge_token, expires_in=LOGIN_CHALLENGE_TTL_SECONDS
        )

    def exchange_challenge(
        self, challenge_token: str, code: str
    ) -> TotpCodeVerificationResult:
        """Exchange a 2FA login challenge for its associated user.

        Validates the challenge JWT, looks up the matching server-side
        ``TotpLoginChallenge`` row (unconsumed and unexpired), then accepts
        either a current TOTP code or an unused recovery code. On success
        the challenge is atomically consumed to prevent replay (FR-009).

        Args:
            challenge_token: The signed challenge JWT from /api/auth/login
            code: A 6-digit TOTP code or an ``xxxx-xxxx`` recovery code

        Returns:
            TotpCodeVerificationResult with the user (caller issues real
            tokens) and whether a recovery code was used (audit logging)

        Raises:
            TotpChallengeExpiredError: Challenge is malformed, unknown,
                expired, or already consumed (410)
            TotpCodeInvalidError: The code is wrong (401)
            RuntimeError: If constructed without a JWTService
        """
        if self.jwt_service is None:
            raise RuntimeError(
                "TotpService requires a JWTService to exchange challenges"
            )

        try:
            claims = self.jwt_service.validate_2fa_challenge_token(challenge_token)
        except JWTInvalidTokenError as e:
            raise TotpChallengeExpiredError(context={"reason": str(e)}) from e

        challenge_id = claims["jti"]
        user_id = claims["sub"]

        challenge = self.totp_repository.get_valid_challenge(challenge_id)
        if challenge is None:
            raise TotpChallengeExpiredError(context={"challenge_id": challenge_id})

        result = self._verify_totp_or_recovery_code(user_id, code)

        self.totp_repository.consume_challenge(challenge)

        logger.info("2FA login challenge exchanged for user_id=%s", user_id)

        return result

    def _verify_totp_or_recovery_code(
        self, user_id: str, code: str
    ) -> TotpCodeVerificationResult:
        """Verify a TOTP or recovery code for a user, raising on failure.

        Accepts either a current TOTP code (±1 time-step tolerance, applying
        the replay guard via ``last_used_step``) or an unused recovery code
        (single-use, marked consumed on success).

        Args:
            user_id: The user's id (from the validated challenge/session)
            code: A 6-digit TOTP code or an ``xxxx-xxxx`` recovery code

        Returns:
            The associated User instance

        Raises:
            TotpCodeInvalidError: Neither a valid TOTP code nor an unused
                recovery code matched
        """
        credential = self.totp_repository.get_credential(user_id)
        if credential is not None and credential.confirmed:
            secret = self.encryption_service.decrypt_secret(
                credential.secret_ciphertext, credential.secret_nonce
            )
            totp = pyotp.totp.TOTP(secret)
            matched_step = self._matching_totp_step(
                totp, code, credential.last_used_step
            )
            if matched_step is not None:
                self.totp_repository.update_last_used_step(credential, matched_step)
                return TotpCodeVerificationResult(
                    user=credential.user, used_recovery_code=False
                )

        for recovery_code in self.totp_repository.get_latest_batch_codes(user_id):
            if recovery_code.used_at is not None:
                continue
            if self.password_service.verify_password(code, recovery_code.code_hash):
                self.totp_repository.mark_recovery_code_used(recovery_code)
                return TotpCodeVerificationResult(
                    user=recovery_code.user, used_recovery_code=True
                )

        logger.info("TOTP/recovery code verification failed for user_id=%s", user_id)
        raise TotpCodeInvalidError(context={"user_id": user_id})

    @staticmethod
    def _matching_totp_step(
        totp: pyotp.totp.TOTP, code: str, last_used_step: int | None
    ) -> int | None:
        """Find the time-step (within ±1) that ``code`` matches, if any.

        Checks each candidate step individually (rather than delegating to
        ``TOTP.verify(..., valid_window=1)``) so the replay guard can be
        applied against the step the code actually corresponds to, not just
        wall-clock "now" — a code for step+1 must still be rejected if
        step+1 was already accepted, and a code that only matches an
        already-used step must be rejected even if it is otherwise within
        the ±1 tolerance window (FR-006, FR-007).

        Args:
            totp: TOTP instance for the user's decrypted secret
            code: The submitted code to check
            last_used_step: The last time-step accepted for this credential

        Returns:
            The matching step if valid and not already used, else None
        """
        now = time.time()
        current_step = int(now) // totp.interval
        for step in (current_step - 1, current_step, current_step + 1):
            if last_used_step is not None and step <= last_used_step:
                continue
            if secrets.compare_digest(totp.at(step * totp.interval), code):
                return step
        return None

    @staticmethod
    def _generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
        """Generate cryptographically secure recovery codes.

        Format: ``xxxx-xxxx`` where x is a lowercase alphanumeric character
        (8 significant characters total), per research.md §4.

        Args:
            count: Number of codes to generate

        Returns:
            List of plaintext recovery codes
        """
        codes = []
        for _ in range(count):
            raw = "".join(secrets.choice(RECOVERY_CODE_ALPHABET) for _ in range(8))
            codes.append(f"{raw[:4]}-{raw[4:]}")
        return codes
