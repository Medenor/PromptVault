# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""SkillService called directly (no HTTP): audit ordering, ownership, rollback.

The commit-failure cases wrap ``get_db_session`` so the block raises after its
body ran, which rolls the transaction back. FR-025a: no success audit event may
exist for a change that was not stored.
"""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from src.db.session import get_db_session as real_get_db_session
from src.services.skills import skill_service as skill_service_module
from src.services.skills.errors import SkillArchiveError
from src.services.skills.skill_service import (
    SkillLookupError,
    SkillService,
    prepare_skill_deleted_audit,
)


@pytest.fixture
def service() -> SkillService:
    return SkillService()


@pytest.fixture
def owner(skill_api, skill_owner) -> SimpleNamespace:
    return SimpleNamespace(id="skill-owner-id", username="skill_owner", role="user")


@pytest.fixture
def other(skill_api, skill_other) -> SimpleNamespace:
    return SimpleNamespace(id="skill-other-id", username="skill_other", role="user")


@pytest.fixture
def failing_commit(monkeypatch):
    """Make every ``get_db_session`` block fail after its body (rolls back)."""

    @contextmanager
    def _failing():
        with real_get_db_session() as session:
            yield session
            raise RuntimeError("commit failed")

    def _install() -> None:
        monkeypatch.setattr(skill_service_module, "get_db_session", _failing)

    return _install


def _actions(events: list[dict]) -> list[str]:
    return [event["action"] for event in events]


class TestImport:
    def test_success_audits_once_with_metadata_only(
        self, service, owner, skill_zip_valid_wrapped, skill_audit
    ):
        detail = service.import_skill(skill_zip_valid_wrapped, "s.zip", owner)

        assert _actions(skill_audit) == ["skill.import"]
        event = skill_audit[0]
        assert event["resource_id"] == str(detail["id"])
        assert event["actor"] == "skill_owner"
        assert event["file_count"] == len(detail["files"])
        assert "content" not in event

    def test_rejected_archive_audits_the_rejection_only(
        self, service, owner, make_skill_zip, skill_audit, skill_api
    ):
        bad = make_skill_zip([("notes.txt", "no skill file here")])

        with pytest.raises(SkillArchiveError) as caught:
            service.import_skill(bad, "bad.zip", owner)

        assert _actions(skill_audit) == ["skill.import.rejected"]
        assert skill_audit[0]["reason_code"] == caught.value.code
        assert skill_audit[0]["status"] == "failure"
        assert skill_api.count_rows("skill_packages") == 0

    def test_failed_commit_leaves_no_success_event_and_no_rows(
        self,
        service,
        owner,
        skill_zip_valid_wrapped,
        skill_audit,
        skill_api,
        failing_commit,
    ):
        failing_commit()

        with pytest.raises(RuntimeError):
            service.import_skill(skill_zip_valid_wrapped, "s.zip", owner)

        assert "skill.import" not in _actions(skill_audit)
        assert skill_api.count_rows("skill_packages") == 0
        assert skill_api.count_rows("skill_files") == 0


class TestReplace:
    def _imported(self, service, owner, archive) -> int:
        return service.import_skill(archive, "s.zip", owner)["id"]

    def test_success_audits_once(
        self, service, owner, skill_zip_valid_wrapped, skill_zip_valid_root, skill_audit
    ):
        skill_id = self._imported(service, owner, skill_zip_valid_wrapped)
        skill_audit.clear()

        service.replace_skill_archive(skill_id, skill_zip_valid_root, "n.zip", owner)

        assert _actions(skill_audit) == ["skill.replace"]
        assert skill_audit[0]["resource_id"] == str(skill_id)

    def test_not_owner_is_a_404_and_audits_nothing(
        self,
        service,
        owner,
        other,
        skill_zip_valid_wrapped,
        skill_zip_valid_root,
        skill_audit,
    ):
        skill_id = self._imported(service, owner, skill_zip_valid_wrapped)
        skill_audit.clear()

        with pytest.raises(SkillLookupError) as caught:
            service.replace_skill_archive(
                skill_id, skill_zip_valid_root, "n.zip", other
            )

        assert caught.value.code == "SKILL_NOT_FOUND"
        assert skill_audit == []

    def test_rejected_archive_audits_the_rejection_and_keeps_the_skill(
        self, service, owner, skill_zip_valid_wrapped, make_skill_zip, skill_audit
    ):
        skill_id = self._imported(service, owner, skill_zip_valid_wrapped)
        skill_audit.clear()

        with pytest.raises(SkillArchiveError):
            service.replace_skill_archive(
                skill_id, make_skill_zip([("x.txt", "nope")]), "bad.zip", owner
            )

        assert _actions(skill_audit) == ["skill.replace.rejected"]
        assert service.get_skill_detail(skill_id, owner)["id"] == skill_id

    def test_failed_commit_leaves_no_success_event(
        self,
        service,
        owner,
        skill_zip_valid_wrapped,
        skill_zip_valid_root,
        skill_audit,
        failing_commit,
    ):
        skill_id = self._imported(service, owner, skill_zip_valid_wrapped)
        skill_audit.clear()
        failing_commit()

        with pytest.raises(RuntimeError):
            service.replace_skill_archive(
                skill_id, skill_zip_valid_root, "n.zip", owner
            )

        assert skill_audit == []


class TestDelete:
    def _imported(self, service, owner, archive) -> int:
        return service.import_skill(archive, "s.zip", owner)["id"]

    def test_success_audits_once_after_the_row_is_gone(
        self, service, owner, skill_zip_valid_wrapped, skill_audit, skill_api
    ):
        skill_id = self._imported(service, owner, skill_zip_valid_wrapped)
        skill_audit.clear()

        service.delete_skill(skill_id, owner)

        assert _actions(skill_audit) == ["skill.delete"]
        assert skill_audit[0]["resource_id"] == str(skill_id)
        assert skill_audit[0]["skill_identifier"]
        assert skill_api.count_rows("skill_packages") == 0

    def test_not_owner_is_a_404_and_keeps_the_skill(
        self, service, owner, other, skill_zip_valid_wrapped, skill_audit, skill_api
    ):
        skill_id = self._imported(service, owner, skill_zip_valid_wrapped)
        skill_audit.clear()

        with pytest.raises(SkillLookupError):
            service.delete_skill(skill_id, other)

        assert skill_audit == []
        assert skill_api.count_rows("skill_packages") == 1

    def test_failed_commit_leaves_no_event_and_keeps_the_skill(
        self,
        service,
        owner,
        skill_zip_valid_wrapped,
        skill_audit,
        skill_api,
        failing_commit,
    ):
        skill_id = self._imported(service, owner, skill_zip_valid_wrapped)
        skill_audit.clear()
        failing_commit()

        with pytest.raises(RuntimeError):
            service.delete_skill(skill_id, owner)

        assert skill_audit == []
        assert skill_api.count_rows("skill_packages") == 1


class TestPrepareSkillDeletedAudit:
    def test_prompt_rows_are_a_no_op(self, skill_audit):
        prompt = SimpleNamespace(item_type="prompt", id=1, skill_package=None)

        prepare_skill_deleted_audit(prompt, actor="someone")()

        assert skill_audit == []

    def test_nothing_is_logged_until_the_callable_runs(self, skill_audit):
        package = SimpleNamespace(skill_identifier="demo", file_count=2, total_bytes=9)
        skill = SimpleNamespace(item_type="skill", id=7, skill_package=package)

        emit = prepare_skill_deleted_audit(skill, actor="someone")
        assert skill_audit == []

        emit()
        assert skill_audit == [
            {
                "action": "skill.delete",
                "resource_type": "skill",
                "resource_id": "7",
                "actor": "someone",
                "skill_identifier": "demo",
                "file_count": 2,
                "total_bytes": 9,
            }
        ]
