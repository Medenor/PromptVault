# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""TotpRepository for TOTP-based two-factor authentication persistence.

Provides CRUD operations for TotpCredential, TotpRecoveryCode,
TotpLoginChallenge, and TotpRolePolicy.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.db.models.totp_credential import TotpCredential
from src.db.models.totp_login_challenge import TotpLoginChallenge
from src.db.models.totp_recovery_code import TotpRecoveryCode
from src.db.models.totp_role_policy import TotpRolePolicy


class TotpRepository:
    """Repository for all TOTP 2FA persistence operations.

    Attributes:
        session: Database session
    """

    def __init__(self, session: Session):
        """Initialize TotpRepository.

        Args:
            session: Database session
        """
        self.session = session

    # -- TotpCredential -----------------------------------------------

    def get_credential(self, user_id: str) -> TotpCredential | None:
        """Get the TOTP credential row for a user, if any.

        Args:
            user_id: User's UUID

        Returns:
            TotpCredential instance or None
        """
        return (
            self.session.query(TotpCredential)
            .filter(TotpCredential.user_id == user_id)
            .first()
        )

    def upsert_pending_credential(
        self, user_id: str, secret_ciphertext: str, secret_nonce: str
    ) -> TotpCredential:
        """Create or replace the pending (unconfirmed) credential for a user.

        Args:
            user_id: User's UUID
            secret_ciphertext: AES-256-GCM ciphertext of the base32 secret
            secret_nonce: GCM nonce, hex-encoded

        Returns:
            The created or updated TotpCredential instance
        """
        credential = self.get_credential(user_id)
        if credential is None:
            credential = TotpCredential(
                id=str(uuid.uuid4()),
                user_id=user_id,
                secret_ciphertext=secret_ciphertext,
                secret_nonce=secret_nonce,
                confirmed=False,
            )
            self.session.add(credential)
        else:
            credential.secret_ciphertext = secret_ciphertext
            credential.secret_nonce = secret_nonce
            credential.confirmed = False
            credential.confirmed_at = None
            credential.last_used_step = None
        self.session.flush()
        return credential

    def confirm_credential(self, credential: TotpCredential) -> TotpCredential:
        """Mark a credential as confirmed.

        Args:
            credential: The TotpCredential to confirm

        Returns:
            The updated TotpCredential instance
        """
        credential.confirmed = True
        credential.confirmed_at = datetime.now(UTC)
        self.session.flush()
        return credential

    def update_last_used_step(
        self, credential: TotpCredential, step: int
    ) -> TotpCredential:
        """Record the last successfully-verified TOTP time-step (replay guard).

        Args:
            credential: The TotpCredential to update
            step: The verified time-step counter

        Returns:
            The updated TotpCredential instance
        """
        credential.last_used_step = step
        self.session.flush()
        return credential

    def delete_credential(self, user_id: str) -> bool:
        """Delete a user's TOTP credential.

        Args:
            user_id: User's UUID

        Returns:
            True if a row was deleted, False if none existed
        """
        credential = self.get_credential(user_id)
        if credential is None:
            return False
        self.session.delete(credential)
        self.session.flush()
        return True

    # -- TotpRecoveryCode -----------------------------------------------

    def insert_recovery_code_batch(
        self, user_id: str, code_hashes: list[str]
    ) -> str:
        """Insert a fresh batch of recovery codes for a user.

        Args:
            user_id: User's UUID
            code_hashes: Argon2id hashes of the plaintext codes

        Returns:
            The generated batch_id
        """
        batch_id = str(uuid.uuid4())
        for code_hash in code_hashes:
            self.session.add(
                TotpRecoveryCode(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    batch_id=batch_id,
                    code_hash=code_hash,
                )
            )
        self.session.flush()
        return batch_id

    def get_latest_batch_codes(self, user_id: str) -> list[TotpRecoveryCode]:
        """Get all recovery codes in a user's latest batch.

        Args:
            user_id: User's UUID

        Returns:
            List of TotpRecoveryCode rows in the latest batch (may be empty)
        """
        latest = (
            self.session.query(TotpRecoveryCode)
            .filter(TotpRecoveryCode.user_id == user_id)
            .order_by(TotpRecoveryCode.created_at.desc())
            .first()
        )
        if latest is None:
            return []
        return (
            self.session.query(TotpRecoveryCode)
            .filter(
                and_(
                    TotpRecoveryCode.user_id == user_id,
                    TotpRecoveryCode.batch_id == latest.batch_id,
                )
            )
            .all()
        )

    def mark_recovery_code_used(self, code: TotpRecoveryCode) -> TotpRecoveryCode:
        """Mark a recovery code as used (single-use consumption).

        Args:
            code: The TotpRecoveryCode row to mark used

        Returns:
            The updated TotpRecoveryCode instance
        """
        code.used_at = datetime.now(UTC)
        self.session.flush()
        return code

    def delete_all_recovery_codes(self, user_id: str) -> int:
        """Delete all recovery codes for a user (disable or regenerate).

        Args:
            user_id: User's UUID

        Returns:
            Number of rows deleted
        """
        count = (
            self.session.query(TotpRecoveryCode)
            .filter(TotpRecoveryCode.user_id == user_id)
            .delete(synchronize_session=False)
        )
        self.session.flush()
        return count

    # -- TotpLoginChallenge -----------------------------------------------

    def create_login_challenge(
        self, challenge_id: str, user_id: str, expires_at: datetime
    ) -> TotpLoginChallenge:
        """Create a new login-challenge row.

        Args:
            challenge_id: UUID matching the challenge JWT's jti claim
            user_id: User's UUID
            expires_at: Expiration timestamp (created_at + 2min)

        Returns:
            The created TotpLoginChallenge instance
        """
        challenge = TotpLoginChallenge(
            id=challenge_id, user_id=user_id, expires_at=expires_at
        )
        self.session.add(challenge)
        self.session.flush()
        return challenge

    def get_valid_challenge(self, challenge_id: str) -> TotpLoginChallenge | None:
        """Get a login challenge if it is unconsumed and unexpired.

        Args:
            challenge_id: The challenge's UUID (jti claim)

        Returns:
            TotpLoginChallenge instance if valid, None otherwise
        """
        now = datetime.now(UTC)
        return (
            self.session.query(TotpLoginChallenge)
            .filter(
                and_(
                    TotpLoginChallenge.id == challenge_id,
                    TotpLoginChallenge.consumed_at.is_(None),
                    TotpLoginChallenge.expires_at > now,
                )
            )
            .first()
        )

    def consume_challenge(
        self, challenge: TotpLoginChallenge
    ) -> TotpLoginChallenge:
        """Mark a login challenge as consumed (single-use).

        Args:
            challenge: The TotpLoginChallenge to consume

        Returns:
            The updated TotpLoginChallenge instance
        """
        challenge.consumed_at = datetime.now(UTC)
        self.session.flush()
        return challenge

    # -- TotpRolePolicy -----------------------------------------------

    def get_role_policy(self, role: str) -> TotpRolePolicy | None:
        """Get the 2FA policy row for a role, if any.

        Args:
            role: Role name

        Returns:
            TotpRolePolicy instance or None (absence == not required)
        """
        return (
            self.session.query(TotpRolePolicy)
            .filter(TotpRolePolicy.role == role)
            .first()
        )

    def get_all_role_policies(self) -> list[TotpRolePolicy]:
        """Get all configured role policies.

        Returns:
            List of TotpRolePolicy rows
        """
        return self.session.query(TotpRolePolicy).all()

    def set_role_policy(
        self, role: str, required: bool, updated_by_user_id: str | None
    ) -> TotpRolePolicy:
        """Create or update the 2FA policy for a role.

        Args:
            role: Role name
            required: Whether members of this role must have 2FA enabled
            updated_by_user_id: Admin user making the change

        Returns:
            The created or updated TotpRolePolicy instance
        """
        policy = self.get_role_policy(role)
        if policy is None:
            policy = TotpRolePolicy(
                role=role,
                required=required,
                updated_by_user_id=updated_by_user_id,
            )
            self.session.add(policy)
        else:
            policy.required = required
            policy.updated_by_user_id = updated_by_user_id
        self.session.flush()
        return policy
