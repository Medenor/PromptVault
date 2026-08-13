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

import pyotp

from src.db.models.user import User
from src.db.repositories.totp_repository import TotpRepository
from src.services.auth.password_service import PasswordService
from src.services.auth.totp_encryption_service import TotpEncryptionService
from src.services.auth.totp_qr import render_qr_svg
from src.services.exceptions import (
    TotpAlreadyEnabledError,
    TotpCodeInvalidError,
    TotpEnrollmentNotFoundError,
)

logger = logging.getLogger(__name__)

ISSUER_NAME = "PromptVault"
RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


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


class TotpService:
    """Service for TOTP 2FA enrollment and confirmation.

    Attributes:
        totp_repository: Repository for TOTP persistence
        encryption_service: Service for encrypting/decrypting TOTP secrets
        password_service: Service for hashing recovery codes (Argon2id)
    """

    def __init__(
        self,
        totp_repository: TotpRepository,
        encryption_service: TotpEncryptionService,
        password_service: PasswordService,
    ) -> None:
        """Initialize TotpService.

        Args:
            totp_repository: Repository for TOTP persistence
            encryption_service: Service for encrypting/decrypting TOTP secrets
            password_service: Service for hashing recovery codes (Argon2id)
        """
        self.totp_repository = totp_repository
        self.encryption_service = encryption_service
        self.password_service = password_service

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
