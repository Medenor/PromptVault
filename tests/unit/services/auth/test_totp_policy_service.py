# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for TotpPolicyService (User Story 4).

Covers:
- get_all() reports every known role, defaulting absent rows to required=False
- set() creates/updates a role's policy and rejects unknown roles
- is_required_for() reflects the configured policy (or False when absent)
"""

import pytest

from src.services.auth.totp_policy_service import TotpPolicyService


class _FakePolicy:
    def __init__(self, role: str, required: bool):
        self.role = role
        self.required = required
        self.updated_by_user_id: str | None = None


class FakeTotpRepository:
    """In-memory fake standing in for TotpRepository's role-policy methods."""

    def __init__(self):
        self.policies: dict[str, _FakePolicy] = {}

    def get_role_policy(self, role: str):
        return self.policies.get(role)

    def get_all_role_policies(self):
        return list(self.policies.values())

    def set_role_policy(self, role: str, required: bool, updated_by_user_id):
        policy = self.policies.get(role)
        if policy is None:
            policy = _FakePolicy(role, required)
            self.policies[role] = policy
        else:
            policy.required = required
        policy.updated_by_user_id = updated_by_user_id
        return policy


@pytest.fixture
def repository():
    return FakeTotpRepository()


@pytest.fixture
def service(repository):
    return TotpPolicyService(repository)


class TestGetAll:
    def test_reports_all_roles_default_false_when_unconfigured(self, service):
        entries = service.get_all()

        assert {(e.role, e.required) for e in entries} == {
            ("viewer", False),
            ("editor", False),
            ("admin", False),
        }

    def test_reports_configured_role_as_required(self, service, repository):
        repository.set_role_policy("admin", True, "admin-user-id")

        entries = {e.role: e.required for e in service.get_all()}

        assert entries["admin"] is True
        assert entries["viewer"] is False
        assert entries["editor"] is False


class TestSet:
    def test_creates_new_policy_row(self, service, repository):
        entry = service.set("admin", True, "admin-user-id")

        assert entry.role == "admin"
        assert entry.required is True
        assert repository.policies["admin"].updated_by_user_id == "admin-user-id"

    def test_updates_existing_policy_row(self, service):
        service.set("admin", True, "admin-user-id")

        entry = service.set("admin", False, "admin-user-id")

        assert entry.required is False

    def test_rejects_unknown_role(self, service):
        with pytest.raises(ValueError, match="Unknown role"):
            service.set("superadmin", True, "admin-user-id")


class TestIsRequiredFor:
    def test_false_when_no_policy_row(self, service):
        assert service.is_required_for("admin") is False

    def test_true_when_policy_requires(self, service):
        service.set("editor", True, "admin-user-id")

        assert service.is_required_for("editor") is True

    def test_false_after_policy_disabled(self, service):
        service.set("editor", True, "admin-user-id")
        service.set("editor", False, "admin-user-id")

        assert service.is_required_for("editor") is False
