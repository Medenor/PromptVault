# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""SkillRepository and the item_type filter in PromptRepository."""

import hashlib

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from src.db.models import Prompt, SkillFile, SkillPackage
from src.db.repositories.skill_repository import SkillRepository


class _Rec:
    def __init__(self, path: str, content: bytes, is_text: bool = True) -> None:
        self.path = path
        self.content = content
        self.size = len(content)
        self.sha256 = hashlib.sha256(content).hexdigest()
        self.is_text = is_text


def _skill(session, user, title="A skill", body="skill body text") -> Prompt:
    prompt = Prompt(
        title=title, prompt=body, item_type="skill", user_id=user.id, favorite=False
    )
    session.add(prompt)
    session.flush()
    return prompt


def _package(repo, prompt, **overrides):
    from datetime import UTC, datetime

    values = {
        "skill_identifier": "a-skill",
        "description": "d",
        "total_bytes": 0,
        "file_count": 0,
        "format_warnings": [],
        "source_archive_name": "a-skill.zip",
        "files_updated_at": datetime.now(UTC),
    }
    values.update(overrides)
    return repo.upsert_package(prompt.id, **values)


@pytest.fixture
def skill_repo(test_db_session):
    return SkillRepository(test_db_session)


class TestItemTypeFilter:
    def test_default_item_type_is_prompt(self, test_prompt):
        assert test_prompt.item_type == "prompt"

    def test_search_and_count_filter_by_type(
        self, test_db_session, prompt_repo, test_prompt, test_user
    ):
        _skill(test_db_session, test_user)
        assert prompt_repo.count() == 2
        assert prompt_repo.count(item_type="prompt") == 1
        assert prompt_repo.count(item_type="skill") == 1
        found = prompt_repo.search(item_type="skill")
        assert [p.item_type for p, _ in found] == ["skill"]
        assert [p.item_type for p, _ in prompt_repo.search(item_type="prompt")] == [
            "prompt"
        ]
        assert len(prompt_repo.search()) == 2

    def test_filter_applies_with_a_text_query(
        self, test_db_session, prompt_repo, test_prompt, test_user
    ):
        _skill(test_db_session, test_user, body="shared marker in both")
        test_prompt.prompt = "shared marker in both"
        test_db_session.flush()
        both = prompt_repo.search(query="marker", ranked=False)
        assert len(both) == 2
        only_skill = prompt_repo.search(query="marker", ranked=False, item_type="skill")
        assert [p.item_type for p, _ in only_skill] == ["skill"]
        assert prompt_repo.count(query="marker", ranked=False, item_type="skill") == 1

    def test_statistics_report_both_counts(
        self, test_db_session, prompt_repo, test_prompt, test_user
    ):
        _skill(test_db_session, test_user)
        stats = prompt_repo.get_statistics()
        assert stats["total"] == 2
        assert stats["prompt_count"] == 1
        assert stats["skill_count"] == 1

    def test_check_constraint_rejects_unknown_type(self, test_db_session, test_user):
        test_db_session.add(
            Prompt(title="x", prompt="y", item_type="foo", user_id=test_user.id)
        )
        with pytest.raises(IntegrityError):
            test_db_session.flush()
        test_db_session.rollback()


class TestSkillFiles:
    def test_insert_and_list_without_content(
        self, test_db_session, skill_repo, test_user
    ):
        prompt = _skill(test_db_session, test_user)
        skill_repo.insert_files(
            prompt.id,
            [_Rec("SKILL.md", b"# hi"), _Rec("b/two.bin", b"\x00\x01", False)],
        )
        test_db_session.commit()
        test_db_session.expire_all()

        files = skill_repo.list_files(prompt.id)
        assert [f.path for f in files] == ["b/two.bin", "SKILL.md"]
        for file in files:
            assert "content" not in file.__dict__  # deferred: not loaded by listing

    def test_get_file_loads_content(self, test_db_session, skill_repo, test_user):
        prompt = _skill(test_db_session, test_user)
        skill_repo.insert_files(prompt.id, [_Rec("SKILL.md", b"# hello")])
        test_db_session.commit()
        test_db_session.expire_all()

        file = skill_repo.get_file(prompt.id, "SKILL.md")
        assert file is not None
        assert file.content == b"# hello"
        assert skill_repo.get_file(prompt.id, "nope.md") is None

    def test_iter_file_contents_yields_each_file(
        self, test_db_session, skill_repo, test_user
    ):
        prompt = _skill(test_db_session, test_user)
        skill_repo.insert_files(
            prompt.id, [_Rec("b.txt", b"two"), _Rec("a.txt", b"one")]
        )
        test_db_session.commit()
        assert list(skill_repo.iter_file_contents(prompt.id)) == [
            ("a.txt", b"one"),
            ("b.txt", b"two"),
        ]

    def test_path_uniqueness_is_case_insensitive(
        self, test_db_session, skill_repo, test_user
    ):
        prompt = _skill(test_db_session, test_user)
        skill_repo.insert_files(prompt.id, [_Rec("README.md", b"a")])
        with pytest.raises(IntegrityError):
            skill_repo.insert_files(prompt.id, [_Rec("readme.md", b"b")])
        test_db_session.rollback()

    def test_same_path_is_allowed_in_different_skills(
        self, test_db_session, skill_repo, test_user
    ):
        first = _skill(test_db_session, test_user, title="one")
        second = _skill(test_db_session, test_user, title="two")
        skill_repo.insert_files(first.id, [_Rec("SKILL.md", b"a")])
        skill_repo.insert_files(second.id, [_Rec("SKILL.md", b"b")])
        assert len(skill_repo.list_files(first.id)) == 1

    def test_delete_files_removes_only_that_skill(
        self, test_db_session, skill_repo, test_user
    ):
        first = _skill(test_db_session, test_user, title="one")
        second = _skill(test_db_session, test_user, title="two")
        skill_repo.insert_files(first.id, [_Rec("a", b"1"), _Rec("b", b"2")])
        skill_repo.insert_files(second.id, [_Rec("a", b"3")])
        assert skill_repo.delete_files(first.id) == 2
        assert skill_repo.list_files(first.id) == []
        assert len(skill_repo.list_files(second.id)) == 1


class TestSkillPackage:
    def test_upsert_creates_then_updates(self, test_db_session, skill_repo, test_user):
        prompt = _skill(test_db_session, test_user)
        created = _package(skill_repo, prompt, description="first")
        assert created.description == "first"
        updated = _package(skill_repo, prompt, description="second", file_count=3)
        assert updated is created
        assert skill_repo.get_package(prompt.id).description == "second"
        assert skill_repo.get_package(prompt.id).file_count == 3
        assert test_db_session.query(SkillPackage).count() == 1

    def test_get_packages_batches_a_page(self, test_db_session, skill_repo, test_user):
        first = _skill(test_db_session, test_user, title="one")
        second = _skill(test_db_session, test_user, title="two")
        _package(skill_repo, first, skill_identifier="one")
        _package(skill_repo, second, skill_identifier="two")
        packages = skill_repo.get_packages([first.id, second.id, 9999])
        assert {pid: p.skill_identifier for pid, p in packages.items()} == {
            first.id: "one",
            second.id: "two",
        }
        assert skill_repo.get_packages([]) == {}

    def test_format_warnings_round_trip_as_a_list(
        self, test_db_session, skill_repo, test_user
    ):
        prompt = _skill(test_db_session, test_user)
        _package(skill_repo, prompt, format_warnings=["name_missing", "x"])
        test_db_session.commit()
        test_db_session.expire_all()
        assert skill_repo.get_package(prompt.id).format_warnings == [
            "name_missing",
            "x",
        ]


class TestCascade:
    def test_deleting_the_prompt_removes_package_and_files(
        self, test_db_session, skill_repo, test_user
    ):
        # SQLite only enforces ON DELETE CASCADE with the PRAGMA; the ORM
        # relationship cascade (delete-orphan) must work either way.
        prompt = _skill(test_db_session, test_user)
        skill_repo.insert_files(prompt.id, [_Rec("a", b"1")])
        _package(skill_repo, prompt)
        test_db_session.commit()
        test_db_session.expire_all()

        test_db_session.delete(test_db_session.get(Prompt, prompt.id))
        test_db_session.commit()
        assert test_db_session.query(SkillFile).count() == 0
        assert test_db_session.query(SkillPackage).count() == 0

    def test_listing_never_selects_the_content_column(
        self, test_db_session, skill_repo, test_user
    ):
        prompt = _skill(test_db_session, test_user)
        skill_repo.insert_files(prompt.id, [_Rec("a", b"1")])
        test_db_session.commit()
        statements: list[str] = []

        def _capture(conn, cursor, statement, *args):
            statements.append(statement)

        engine = test_db_session.get_bind()
        event.listen(engine, "before_cursor_execute", _capture)
        try:
            skill_repo.list_files(prompt.id)
        finally:
            event.remove(engine, "before_cursor_execute", _capture)
        assert statements
        assert not any("skill_files.content" in s for s in statements)
