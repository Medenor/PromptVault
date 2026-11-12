# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Compare-and-set semantics of the TOTP single-use guards (FR-007, FR-009).

Two concurrent requests presenting the same challenge, TOTP step or recovery
code must not both succeed. The repository enforces this with conditional
UPDATEs; the second claimant sees zero affected rows. These tests drive the
second claim directly on a real database, which is what a lost race looks like.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.db.repositories.totp_repository import TotpRepository


@pytest.fixture
def repo(test_db_session):
    return TotpRepository(test_db_session)


class TestChallengeConsumption:
    def test_second_consume_of_same_challenge_loses(self, repo, test_user):
        challenge = repo.create_login_challenge(
            "challenge-1", test_user.id, datetime.now(UTC) + timedelta(minutes=2)
        )

        assert repo.consume_challenge(challenge) is True
        assert repo.consume_challenge(challenge) is False

    def test_delete_expired_challenges_keeps_live_ones(self, repo, test_user):
        repo.create_login_challenge(
            "expired", test_user.id, datetime.now(UTC) - timedelta(seconds=1)
        )
        repo.create_login_challenge(
            "live", test_user.id, datetime.now(UTC) + timedelta(minutes=2)
        )

        assert repo.delete_expired_challenges() == 1
        assert repo.get_valid_challenge("live") is not None
        assert repo.get_valid_challenge("expired") is None


class TestTotpStepReplayGuard:
    def _credential(self, repo, user):
        credential = repo.upsert_pending_credential(user.id, "ciphertext", "nonce")
        repo.confirm_credential(credential)
        return credential

    def test_same_step_cannot_be_advanced_twice(self, repo, test_user):
        credential = self._credential(repo, test_user)

        assert repo.advance_last_used_step(credential, 100) is True
        assert repo.advance_last_used_step(credential, 100) is False

    def test_older_step_cannot_be_accepted_after_a_newer_one(self, repo, test_user):
        credential = self._credential(repo, test_user)

        assert repo.advance_last_used_step(credential, 100) is True
        assert repo.advance_last_used_step(credential, 99) is False
        assert repo.advance_last_used_step(credential, 101) is True

    def test_advance_updates_the_loaded_object(self, repo, test_user):
        credential = self._credential(repo, test_user)

        repo.advance_last_used_step(credential, 42)

        assert credential.last_used_step == 42


class TestRecoveryCodeClaim:
    def test_recovery_code_can_be_claimed_only_once(self, repo, test_user):
        repo.insert_recovery_code_batch(test_user.id, ["hash-a", "hash-b"])
        code = repo.get_latest_batch_codes(test_user.id)[0]

        assert repo.claim_recovery_code(code) is True
        assert repo.claim_recovery_code(code) is False
        assert code.used_at is not None
