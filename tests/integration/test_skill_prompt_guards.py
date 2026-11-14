# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prompt-only features are blocked on skills (FR-003, FR-024a, FR-001).

Skills are inserted straight through the repository (no import service), so
these tests prove the guards on their own. A skill is a ``prompts`` row with
``item_type='skill'``; every prompt-only code path must refuse it or skip it.
"""

import io
import json

import pytest

SKILL_BODY_FIELDS = {"title": "Edited", "prompt": "new text"}


@pytest.fixture
def skill_id(skill_api, skill_owner) -> int:
    return skill_api.seed_skill("skill-owner-id", title="Guarded skill")


def _assert_item_is_skill(response):
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "ITEM_IS_SKILL"
    assert detail["message"]


class TestWriteGuards:
    def test_put_prompt_is_refused_and_creates_no_version(
        self, skill_api, skill_owner, skill_id
    ):
        before = skill_api.count_rows("prompt_versions")
        response = skill_api.client.put(
            f"/api/prompts/{skill_id}", headers=skill_owner, data=SKILL_BODY_FIELDS
        )
        _assert_item_is_skill(response)
        assert skill_api.count_rows("prompt_versions") == before

    def test_put_leaves_the_skill_text_unchanged(
        self, skill_api, skill_owner, skill_id
    ):
        skill_api.client.put(
            f"/api/prompts/{skill_id}", headers=skill_owner, data=SKILL_BODY_FIELDS
        )
        listing = skill_api.client.get(
            "/api/prompts?item_type=skill", headers=skill_owner
        ).json()
        assert listing["prompts"][str(skill_id)]["title"] == "Guarded skill"

    def test_patch_prompt_visibility_is_refused(self, skill_api, skill_owner, skill_id):
        response = skill_api.client.patch(
            f"/api/prompts/{skill_id}",
            headers=skill_owner,
            json={"legacy_public": False},
        )
        _assert_item_is_skill(response)

    def test_copy_with_version_is_refused(
        self, skill_api, skill_owner_session, skill_id
    ):
        response = skill_api.client.post(
            f"/api/prompts/{skill_id}/copy-with-version",
            headers=skill_owner_session,
        )
        _assert_item_is_skill(response)

    def test_copy_with_version_hides_the_skill_from_anonymous_callers(
        self, skill_api, skill_id
    ):
        response = skill_api.client.post(f"/api/prompts/{skill_id}/copy-with-version")
        assert response.status_code == 404

    def test_service_update_raises_for_a_skill(self, skill_api, skill_id):
        from src.services.exceptions import ItemIsSkillError
        from src.web import app as web_app

        with pytest.raises(ItemIsSkillError):
            web_app.data_service.update_prompt(skill_id, SKILL_BODY_FIELDS)

    def test_service_revert_raises_for_a_skill(self, skill_api, skill_id):
        from src.services.exceptions import ItemIsSkillError
        from src.web import app as web_app

        with pytest.raises(ItemIsSkillError):
            web_app.data_service.revert_prompt_to_version(
                skill_id, SKILL_BODY_FIELDS, "revert"
            )


class TestVersionGuards:
    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("get", "/versions"),
            ("get", "/versions/compare?v1=a&v2=b"),
            ("get", "/versions/some-version"),
            ("post", "/versions/some-version/revert"),
        ],
    )
    def test_version_endpoints_refuse_skills(
        self, skill_api, skill_owner, skill_id, method, path
    ):
        before = skill_api.count_rows("prompt_versions")
        response = getattr(skill_api.client, method)(
            f"/api/prompts/{skill_id}{path}", headers=skill_owner
        )
        _assert_item_is_skill(response)
        assert skill_api.count_rows("prompt_versions") == before


class TestSharingGuards:
    def test_grant_is_refused(self, skill_api, skill_owner, skill_other, skill_id):
        response = skill_api.client.post(
            f"/api/prompts/{skill_id}/shares",
            headers=skill_owner,
            json={"identifier": "skill_other", "permission": "read"},
        )
        _assert_item_is_skill(response)
        assert skill_api.count_rows("prompt_shares") == 0

    def test_list_is_refused(self, skill_api, skill_owner, skill_id):
        _assert_item_is_skill(
            skill_api.client.get(f"/api/prompts/{skill_id}/shares", headers=skill_owner)
        )

    def test_revoke_is_refused(self, skill_api, skill_owner, skill_other, skill_id):
        _assert_item_is_skill(
            skill_api.client.delete(
                f"/api/prompts/{skill_id}/shares/skill-other-id", headers=skill_owner
            )
        )


class TestInvisibleSkillsStayHidden:
    """A non-owner must not learn that the id is a skill (404, not 409)."""

    def test_other_user_gets_404_everywhere(self, skill_api, skill_other, skill_id):
        client = skill_api.client
        responses = [
            client.put(
                f"/api/prompts/{skill_id}", headers=skill_other, data=SKILL_BODY_FIELDS
            ),
            client.get(f"/api/prompts/{skill_id}/versions", headers=skill_other),
            client.post(
                f"/api/prompts/{skill_id}/shares",
                headers=skill_other,
                json={"identifier": "x", "permission": "read"},
            ),
        ]
        assert [r.status_code for r in responses] == [404, 404, 404]

    def test_other_user_cannot_see_the_skill_in_lists(
        self, skill_api, skill_other, skill_id
    ):
        listing = skill_api.client.get("/api/prompts", headers=skill_other).json()
        assert listing["total_count"] == 0

    def test_admin_sees_every_skill(self, skill_api, skill_admin, skill_id):
        listing = skill_api.client.get(
            "/api/prompts?item_type=skill", headers=skill_admin
        ).json()
        assert listing["total_count"] == 1


class TestPromptCreationIgnoresItemType:
    def test_post_prompts_always_creates_a_prompt(self, skill_api, skill_owner):
        response = skill_api.client.post(
            "/api/prompts",
            headers=skill_owner,
            data={
                "title": "Sneaky",
                "prompt": "body",
                "item_type": "skill",
            },
        )
        assert response.status_code == 201
        new_id = response.json()["prompt_id"]
        detail = skill_api.client.get(f"/api/prompts/{new_id}", headers=skill_owner)
        assert detail.json()["item_type"] == "prompt"
        assert detail.json()["prompt"] == "body"


class TestListAndGetShapes:
    def test_list_items_carry_item_type_and_skills_omit_the_body(
        self, skill_api, skill_owner, skill_id
    ):
        skill_api.client.post(
            "/api/prompts",
            headers=skill_owner,
            data={"title": "Plain", "prompt": "plain body"},
        )
        listing = skill_api.client.get("/api/prompts", headers=skill_owner).json()
        items = list(listing["prompts"].values())
        by_type = {item["item_type"]: item for item in items}
        assert set(by_type) == {"prompt", "skill"}
        assert by_type["prompt"]["prompt"] == "plain body"
        skill = by_type["skill"]
        assert "prompt" not in skill
        assert skill["skill_identifier"] == "seeded-skill"
        assert skill["description"] == "A seeded skill"
        assert skill["file_count"] == 3
        assert skill["total_bytes"] > 0
        assert skill["format_warnings"] == []

    @pytest.mark.parametrize(
        ("item_type", "expected"),
        [("all", {"prompt", "skill"}), ("prompt", {"prompt"}), ("skill", {"skill"})],
    )
    def test_item_type_filter(
        self, skill_api, skill_owner, skill_id, item_type, expected
    ):
        skill_api.client.post(
            "/api/prompts",
            headers=skill_owner,
            data={"title": "Plain", "prompt": "plain body"},
        )
        for url in (
            f"/api/prompts?item_type={item_type}",
            f"/api/prompts/search?item_type={item_type}",
        ):
            body = skill_api.client.get(url, headers=skill_owner).json()
            assert {i["item_type"] for i in body["prompts"].values()} == expected
            assert body["total_count"] == len(body["prompts"])

    def test_unknown_item_type_is_rejected(self, skill_api, skill_owner):
        response = skill_api.client.get(
            "/api/prompts?item_type=banana", headers=skill_owner
        )
        assert response.status_code == 422

    def test_get_skill_returns_a_summary_without_the_body(
        self, skill_api, skill_owner, skill_id
    ):
        body = skill_api.client.get(
            f"/api/prompts/{skill_id}", headers=skill_owner
        ).json()
        assert body["item_type"] == "skill"
        assert "prompt" not in body

    def test_favorite_toggle_works_for_skills(self, skill_api, skill_owner, skill_id):
        response = skill_api.client.put(
            f"/api/prompts/{skill_id}/favorite", headers=skill_owner
        )
        assert response.status_code == 200
        assert response.json()["favorite"] is True

    def test_delete_removes_the_skill_and_its_files(
        self, skill_api, skill_owner, skill_id
    ):
        assert skill_api.count_rows("skill_files") == 3
        response = skill_api.client.delete(
            f"/api/prompts/{skill_id}", headers=skill_owner
        )
        assert response.status_code == 200
        assert skill_api.count_rows("skill_files") == 0
        assert skill_api.count_rows("skill_packages") == 0


class TestBulkImportExport:
    def _import(self, skill_api, csv: str, mode: str):
        files = {"file": ("data.csv", io.BytesIO(csv.encode()), "text/csv")}
        response = skill_api.client.post(
            "/api/import", data={"mode": mode, "validate_data": True}, files=files
        )
        assert response.status_code == 200, response.text
        return response.json()

    def test_replace_mode_keeps_skills(
        self, skill_api, skill_owner, skill_admin, skill_id
    ):
        skill_api.client.post(
            "/api/prompts",
            headers=skill_owner,
            data={"title": "Old prompt", "prompt": "old"},
        )
        csv = "title,prompt,note,category,tags,favorite\nNew prompt,Body,,Docs,,No\n"
        result = self._import(skill_api, csv, "replace")
        assert result["added_count"] == 1

        listing = skill_api.client.get("/api/prompts", headers=skill_admin).json()
        titles = {i["title"] for i in listing["prompts"].values()}
        assert titles == {"Guarded skill", "New prompt"}
        assert skill_api.count_rows("skill_files") == 3

    def test_export_leaves_skills_out_and_reports_the_count(
        self, skill_api, skill_owner, skill_id
    ):
        skill_api.client.post(
            "/api/prompts",
            headers=skill_owner,
            data={"title": "Exported prompt", "prompt": "body"},
        )
        response = skill_api.client.post("/api/export", data={"format": "json"})
        assert response.status_code == 200
        assert response.headers["X-Skills-Excluded"] == "1"
        payload = json.loads(response.content)
        assert payload["skills_excluded"] == 1
        titles = {p["data"]["title"] for p in payload["prompts"].values()}
        assert "Exported prompt" in titles
        assert "Guarded skill" not in titles

    def test_stats_count_skills_apart_from_prompts(
        self, skill_api, skill_admin, skill_id
    ):
        listing = skill_api.client.get(
            "/api/prompts?item_type=prompt", headers=skill_admin
        ).json()
        stats = skill_api.client.get("/api/import-export/stats").json()
        assert stats["skill_count"] == 1
        assert stats["total_prompts"] == listing["total_count"]
