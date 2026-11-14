# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""POST /api/skills/import (User Story 1): success, warnings, rejections, audit."""

import importlib

import pytest
from fixtures.skills import build_fixtures as bf

API_REJECTED = [c for c in bf.REJECTED_CASES if c.id != "total-too-large"]


def _skill_rows(skill_api) -> dict[str, int]:
    return {
        table: skill_api.count_rows(table)
        for table in ("prompts", "skill_packages", "skill_files")
    }


class TestImportSuccess:
    def test_valid_wrapped_archive_returns_201_with_the_detail_shape(
        self, skill_api, skill_owner, skill_zip_valid_wrapped
    ):
        response = skill_api.import_zip(skill_zip_valid_wrapped, skill_owner)
        assert response.status_code == 201, response.text
        body = response.json()
        skill = body["skill"]
        assert body["warnings"] == [] == skill["format_warnings"]
        assert skill["item_type"] == "skill"
        assert skill["title"] == "pdf-tools"
        assert skill["skill_identifier"] == "pdf-tools"
        assert skill["description"] == "Fill PDF forms and extract tables."
        assert skill["file_count"] == 3
        assert skill["total_bytes"] == sum(f["size"] for f in skill["files"])
        assert {f["path"] for f in skill["files"]} == {
            "SKILL.md",
            "scripts/fill.py",
            "references/sample.bin",
        }
        assert "prompt" not in skill
        assert skill["note"] == ""
        assert "<h1>PDF tools</h1>" in skill["instructions_html"]
        assert "${CLAUDE_SKILL_DIR}" in skill["instructions_html"]
        binary = next(f for f in skill["files"] if f["path"].endswith(".bin"))
        assert binary["is_text"] is False
        assert len(binary["sha256"]) == 64

    def test_import_creates_one_item_of_each_kind_of_row(
        self, skill_api, skill_owner, skill_zip_valid_wrapped
    ):
        before = _skill_rows(skill_api)
        skill_api.import_zip(skill_zip_valid_wrapped, skill_owner)
        after = _skill_rows(skill_api)
        assert after["prompts"] == before["prompts"] + 1
        assert after["skill_packages"] == before["skill_packages"] + 1
        assert after["skill_files"] == before["skill_files"] + 3

    def test_stored_skill_md_is_byte_exact_and_private(
        self, skill_api, skill_owner, skill_zip_valid_wrapped
    ):
        skill = skill_api.import_zip(skill_zip_valid_wrapped, skill_owner).json()[
            "skill"
        ]
        from src.db.models import Prompt
        from src.db.session import SessionLocal

        session = SessionLocal()
        try:
            row = session.get(Prompt, skill["id"])
            assert row.item_type == "skill"
            assert row.legacy_public is False
            assert row.prompt == bf.SKILL_MD_VALID
            assert row.user_id == "skill-owner-id"
        finally:
            session.close()

    def test_category_and_tags_are_applied(
        self, skill_api, skill_owner, skill_zip_valid_wrapped
    ):
        skill = skill_api.import_zip(
            skill_zip_valid_wrapped, skill_owner, category="Docs", tags="pdf, forms"
        ).json()["skill"]
        assert skill["category"] == "Docs"
        assert sorted(skill["tags"]) == ["forms", "pdf"]

    def test_new_skill_shows_up_in_the_list_with_a_skill_marker(
        self, skill_api, skill_owner, skill_zip_valid_wrapped
    ):
        skill_id = skill_api.import_zip(skill_zip_valid_wrapped, skill_owner).json()[
            "skill"
        ]["id"]
        listing = skill_api.client.get(
            "/api/prompts?item_type=skill", headers=skill_owner
        ).json()
        assert listing["prompts"][str(skill_id)]["item_type"] == "skill"

    def test_clutter_entries_are_not_stored(
        self, skill_api, skill_owner, skill_zip_with_clutter
    ):
        skill = skill_api.import_zip(skill_zip_with_clutter, skill_owner).json()[
            "skill"
        ]
        assert [f["path"] for f in skill["files"]] == ["SKILL.md"]

    def test_title_is_cut_to_200_characters(
        self, skill_api, skill_owner, make_skill_zip
    ):
        name = "a" * 250
        data = make_skill_zip(
            [("SKILL.md", f"---\nname: {name}\ndescription: d\n---\nbody\n")]
        )
        skill = skill_api.import_zip(data, skill_owner).json()["skill"]
        assert len(skill["title"]) == 200
        assert len(skill["skill_identifier"]) <= 64


class TestLenientImport:
    def test_root_level_skill_is_accepted_with_a_warning(
        self, skill_api, skill_owner, skill_zip_valid_root
    ):
        response = skill_api.import_zip(skill_zip_valid_root, skill_owner)
        assert response.status_code == 201
        assert response.json()["warnings"] == ["no_wrapping_folder"]

    def test_missing_frontmatter_falls_back_to_the_archive_name(
        self, skill_api, skill_owner, skill_zip_no_frontmatter
    ):
        response = skill_api.import_zip(
            skill_zip_no_frontmatter, skill_owner, filename="My Cool Skill.zip"
        )
        assert response.status_code == 201
        body = response.json()
        assert body["warnings"] == ["frontmatter_missing", "no_wrapping_folder"]
        assert body["skill"]["title"] == "My Cool Skill"
        assert body["skill"]["skill_identifier"] == "my-cool-skill"

    def test_invalid_name_still_imports_with_a_slug_identifier(
        self, skill_api, skill_owner, skill_zip_bad_name
    ):
        body = skill_api.import_zip(skill_zip_bad_name, skill_owner).json()
        assert "name_invalid" in body["warnings"]
        assert body["skill"]["title"] == "Bad Name!"
        assert body["skill"]["skill_identifier"] == "bad-name"

    def test_non_utf8_skill_md_imports_with_a_warning(
        self, skill_api, skill_owner, skill_zip_non_utf8
    ):
        body = skill_api.import_zip(skill_zip_non_utf8, skill_owner).json()
        assert "skill_md_not_utf8" in body["warnings"]


class TestRejections:
    @pytest.mark.parametrize("case", API_REJECTED, ids=lambda c: c.id)
    def test_rejected_archive_stores_nothing_and_is_audited(
        self, skill_api, skill_owner, skill_audit, case
    ):
        before = _skill_rows(skill_api)
        response = skill_api.import_zip(case.build(), skill_owner)

        expected_status = 413 if case.code == "LIMIT_UPLOAD_SIZE" else 400
        assert response.status_code == expected_status, response.text
        detail = response.json()["detail"]
        assert detail["code"] == case.code
        assert detail["message"]
        if case.offending_entry is not None:
            assert detail["offending_entry"] == case.offending_entry

        assert _skill_rows(skill_api) == before

        rejected = [e for e in skill_audit if e["action"] == "skill.import.rejected"]
        assert len(rejected) == 1
        event = rejected[0]
        assert event["reason_code"] == case.code
        assert event["status"] == "failure"
        assert event["resource_type"] == "skill"
        assert not any(isinstance(v, bytes | bytearray) for v in event.values())

    def test_missing_archive_field_is_a_validation_error(self, skill_api, skill_owner):
        response = skill_api.client.post("/api/skills/import", headers=skill_owner)
        assert response.status_code == 422


class TestAudit:
    def test_success_writes_one_skill_import_event_without_contents(
        self, skill_api, skill_owner, skill_audit, skill_zip_valid_wrapped
    ):
        skill_api.import_zip(skill_zip_valid_wrapped, skill_owner)
        imported = [e for e in skill_audit if e["action"] == "skill.import"]
        assert len(imported) == 1
        event = imported[0]
        assert event["resource_type"] == "skill"
        assert event["skill_identifier"] == "pdf-tools"
        assert event["file_count"] == 3
        assert event["total_bytes"] > 0
        assert event["actor"] == "skill_owner"
        flattened = " ".join(str(v) for v in event.values())
        assert "references/sample.bin" not in flattened  # no file lists
        assert "fill.py" not in flattened


class TestAuth:
    def test_unauthenticated_import_is_401(self, skill_api, skill_zip_valid_wrapped):
        response = skill_api.client.post(
            "/api/skills/import",
            files={"archive": ("x.zip", skill_zip_valid_wrapped, "application/zip")},
        )
        assert response.status_code == 401
        assert skill_api.count_rows("skill_packages") == 0


class TestRateLimit:
    def test_import_and_replace_use_the_expensive_limit(self, monkeypatch):
        """The limiter decorates at import time, so rebuild the router enabled."""
        from src.web.middleware import rate_limit as rl

        skills_router = importlib.import_module("src.web.routers.skills_router")

        monkeypatch.setenv("DISABLE_RATE_LIMITING", "false")
        try:
            importlib.reload(skills_router)
            actual = rl.limiter._actual_limiter
            keys = set(actual._route_limits) | set(actual._dynamic_route_limits)
            assert "src.web.routers.skills_router.import_skill" in keys
            assert "src.web.routers.skills_router.replace_skill_archive" in keys
        finally:
            monkeypatch.setenv("DISABLE_RATE_LIMITING", "true")
            importlib.reload(skills_router)
