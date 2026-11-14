# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Editing, replacing and deleting skills (User Story 4)."""

import pytest
from fixtures.skills import build_fixtures as bf


@pytest.fixture
def imported(skill_api, skill_owner, skill_zip_valid_wrapped) -> dict:
    return skill_api.import_zip(skill_zip_valid_wrapped, skill_owner).json()["skill"]


def _snapshot(skill_api, headers, skill_id) -> dict:
    """Everything observable about a skill, for before/after comparisons."""
    detail = skill_api.client.get(f"/api/skills/{skill_id}", headers=headers).json()
    download = skill_api.client.get(
        f"/api/skills/{skill_id}/download", headers=headers
    ).content
    return {"detail": detail, "download": download}


NEW_ZIP_NAME_DIFFERS = bf.build_zip(
    [
        (
            "pdf-tools-v2/SKILL.md",
            "---\nname: pdf-tools-v2\ndescription: The second generation.\n---\n"
            "# Version two\nFresh pelican instructions.\n",
        ),
        ("pdf-tools-v2/new.txt", "brand new"),
    ]
)


class TestPatch:
    def test_allowed_fields_are_applied(self, skill_api, skill_owner, imported):
        response = skill_api.client.patch(
            f"/api/skills/{imported['id']}",
            headers=skill_owner,
            json={
                "title": "Renamed",
                "category": "Docs",
                "tags": ["pdf", "forms"],
                "note": "my note",
                "favorite": True,
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["title"] == "Renamed"
        assert body["category"] == "Docs"
        assert sorted(body["tags"]) == ["forms", "pdf"]
        assert body["note"] == "my note"
        assert body["favorite"] is True
        assert body["skill_identifier"] == "pdf-tools"  # untouched
        assert body["file_count"] == 3

    def test_only_present_fields_change(self, skill_api, skill_owner, imported):
        skill_api.client.patch(
            f"/api/skills/{imported['id']}",
            headers=skill_owner,
            json={"title": "T", "tags": ["a"], "note": "n"},
        )
        body = skill_api.client.patch(
            f"/api/skills/{imported['id']}",
            headers=skill_owner,
            json={"favorite": True},
        ).json()
        assert (body["title"], body["tags"], body["note"]) == ("T", ["a"], "n")

    def test_null_category_clears_it(self, skill_api, skill_owner, imported):
        skill_api.client.patch(
            f"/api/skills/{imported['id']}", headers=skill_owner, json={"category": "X"}
        )
        body = skill_api.client.patch(
            f"/api/skills/{imported['id']}",
            headers=skill_owner,
            json={"category": None},
        ).json()
        assert body["category"] == ""

    def test_empty_tag_list_clears_tags(self, skill_api, skill_owner, imported):
        skill_api.client.patch(
            f"/api/skills/{imported['id']}", headers=skill_owner, json={"tags": ["a"]}
        )
        body = skill_api.client.patch(
            f"/api/skills/{imported['id']}", headers=skill_owner, json={"tags": []}
        ).json()
        assert body["tags"] == []

    @pytest.mark.parametrize(
        "payload",
        [
            {"prompt": "new text"},
            {"description": "changed"},
            {"skill_identifier": "other"},
            {"files": []},
            {"title": ""},
            {"title": "x" * 201},
            {"title": "   "},
        ],
    )
    def test_forbidden_or_invalid_fields_are_422(
        self, skill_api, skill_owner, imported, payload
    ):
        response = skill_api.client.patch(
            f"/api/skills/{imported['id']}", headers=skill_owner, json=payload
        )
        assert response.status_code == 422

    def test_patch_never_creates_a_version(self, skill_api, skill_owner, imported):
        before = skill_api.count_rows("prompt_versions")
        skill_api.client.patch(
            f"/api/skills/{imported['id']}", headers=skill_owner, json={"title": "N"}
        )
        assert skill_api.count_rows("prompt_versions") == before


class TestReplace:
    def test_user_metadata_is_kept_and_derived_fields_refresh(
        self, skill_api, skill_owner, skill_audit, imported
    ):
        skill_api.client.patch(
            f"/api/skills/{imported['id']}",
            headers=skill_owner,
            json={
                "title": "My PDF helper",
                "note": "keep me",
                "tags": ["pdf"],
                "category": "Docs",
                "favorite": True,
            },
        )
        response = skill_api.client.put(
            f"/api/skills/{imported['id']}/archive",
            headers=skill_owner,
            files={"archive": ("v2.zip", NEW_ZIP_NAME_DIFFERS, "application/zip")},
        )
        assert response.status_code == 200, response.text
        skill = response.json()["skill"]
        assert skill["title"] == "My PDF helper"
        assert skill["note"] == "keep me"
        assert skill["tags"] == ["pdf"]
        assert skill["category"] == "Docs"
        assert skill["favorite"] is True
        assert skill["skill_identifier"] == "pdf-tools-v2"
        assert skill["description"] == "The second generation."
        assert {f["path"] for f in skill["files"]} == {"SKILL.md", "new.txt"}
        assert skill["file_count"] == 2
        assert "pelican" in skill["instructions_html"]
        replaced = [e for e in skill_audit if e["action"] == "skill.replace"]
        assert len(replaced) == 1
        assert replaced[0]["skill_identifier"] == "pdf-tools-v2"

    def test_old_files_are_gone_and_new_ones_are_readable(
        self, skill_api, skill_owner, imported
    ):
        skill_api.client.put(
            f"/api/skills/{imported['id']}/archive",
            headers=skill_owner,
            files={"archive": ("v2.zip", NEW_ZIP_NAME_DIFFERS, "application/zip")},
        )
        old = skill_api.client.get(
            f"/api/skills/{imported['id']}/files/content",
            headers=skill_owner,
            params={"path": "scripts/fill.py"},
        )
        new = skill_api.client.get(
            f"/api/skills/{imported['id']}/files/content",
            headers=skill_owner,
            params={"path": "new.txt"},
        )
        assert old.status_code == 404
        assert new.json()["text"] == "brand new"
        assert skill_api.count_rows("skill_files") == 2

    @pytest.mark.parametrize(
        "case",
        [
            c
            for c in bf.REJECTED_CASES
            if c.id
            in {"corrupt", "symlink", "path-traversal", "no-skill-md", "too-deep"}
        ],
        ids=lambda c: c.id,
    )
    def test_rejected_replacement_leaves_the_skill_byte_identical(
        self, skill_api, skill_owner, skill_audit, imported, case
    ):
        before = _snapshot(skill_api, skill_owner, imported["id"])
        response = skill_api.client.put(
            f"/api/skills/{imported['id']}/archive",
            headers=skill_owner,
            files={"archive": ("bad.zip", case.build(), "application/zip")},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == case.code
        assert _snapshot(skill_api, skill_owner, imported["id"]) == before
        rejected = [e for e in skill_audit if e["action"] == "skill.replace.rejected"]
        assert len(rejected) == 1
        assert rejected[0]["reason_code"] == case.code
        assert rejected[0]["resource_id"] == str(imported["id"])

    def test_replace_on_a_prompt_id_is_409(self, skill_api, skill_owner):
        prompt_id = skill_api.client.post(
            "/api/prompts", headers=skill_owner, data={"title": "p", "prompt": "b"}
        ).json()["prompt_id"]
        response = skill_api.client.put(
            f"/api/skills/{prompt_id}/archive",
            headers=skill_owner,
            files={"archive": ("x.zip", bf.valid_wrapped(), "application/zip")},
        )
        assert response.status_code == 409

    def test_replacement_is_searchable_by_new_text_only(
        self, skill_api, skill_owner, imported
    ):
        skill_api.client.put(
            f"/api/skills/{imported['id']}/archive",
            headers=skill_owner,
            files={"archive": ("v2.zip", NEW_ZIP_NAME_DIFFERS, "application/zip")},
        )
        hits = skill_api.client.get(
            "/api/prompts/search?search=pelican&item_type=skill", headers=skill_owner
        ).json()
        assert hits["total_count"] == 1
        old = skill_api.client.get(
            "/api/prompts/search?search=Run&item_type=skill&case_sensitive=true",
            headers=skill_owner,
        ).json()
        assert old["total_count"] == 0


class TestDelete:
    def test_delete_cascades_and_is_audited(
        self, skill_api, skill_owner, skill_audit, imported
    ):
        before = {t: skill_api.count_rows(t) for t in ("prompts", "skill_files")}
        response = skill_api.client.delete(
            f"/api/skills/{imported['id']}", headers=skill_owner
        )
        assert response.status_code == 204
        assert skill_api.count_rows("prompts") == before["prompts"] - 1
        assert skill_api.count_rows("skill_files") == 0
        assert skill_api.count_rows("skill_packages") == 0
        events = [e for e in skill_audit if e["action"] == "skill.delete"]
        assert len(events) == 1
        assert events[0]["skill_identifier"] == "pdf-tools"
        assert events[0]["file_count"] == 3
        assert (
            skill_api.client.get(
                f"/api/skills/{imported['id']}", headers=skill_owner
            ).status_code
            == 404
        )

    def test_delete_through_the_prompt_endpoint_is_also_audited_once(
        self, skill_api, skill_owner, skill_audit, imported
    ):
        response = skill_api.client.delete(
            f"/api/prompts/{imported['id']}", headers=skill_owner
        )
        assert response.status_code == 200
        events = [e for e in skill_audit if e["action"] == "skill.delete"]
        assert len(events) == 1
        assert skill_api.count_rows("skill_files") == 0

    def test_bulk_delete_writes_one_event_per_skill(
        self, skill_api, skill_admin, skill_audit
    ):
        first = skill_api.seed_skill("skill-owner-id", identifier="one")
        second = skill_api.seed_skill("skill-owner-id", identifier="two")
        prompt_id = skill_api.client.post(
            "/api/prompts", headers=skill_admin, data={"title": "p", "prompt": "b"}
        ).json()["prompt_id"]

        response = skill_api.client.request(
            "DELETE",
            "/api/prompts/bulk",
            headers=skill_admin,
            json={"prompt_ids": [first, second, prompt_id]},
        )
        assert response.status_code == 200, response.text
        assert response.json()["deleted_count"] == 3
        events = [e for e in skill_audit if e["action"] == "skill.delete"]
        assert sorted(e["skill_identifier"] for e in events) == ["one", "two"]
        assert skill_api.count_rows("skill_files") == 0

    def test_data_service_delete_paths_audit_skills(self, skill_api, skill_audit):
        from src.web import app as web_app

        first = skill_api.seed_skill("skill-owner-id", identifier="svc-one")
        second = skill_api.seed_skill("skill-owner-id", identifier="svc-two")
        assert web_app.data_service.delete_prompt(first) is True
        result = web_app.data_service.delete_prompts_bulk([second])
        assert result["deleted_count"] == 1
        events = [e for e in skill_audit if e["action"] == "skill.delete"]
        assert sorted(e["skill_identifier"] for e in events) == ["svc-one", "svc-two"]
        assert not [e for e in skill_audit if e["action"] == "prompt.delete"]
