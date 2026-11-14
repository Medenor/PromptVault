# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Authorization of skill endpoints in both auth modes (Constitution III, FR-025)."""

import pytest
from fixtures.skills import build_fixtures as bf

from src.config.auth_config import auth_settings

anonymous_only = pytest.mark.skipif(
    auth_settings.auth_enabled,
    reason="Requires AUTH_ENABLED=false (run: AUTH_ENABLED=false pytest --no-cov ...)",
)
authenticated_only = pytest.mark.skipif(
    not auth_settings.auth_enabled, reason="Requires AUTH_ENABLED=true"
)


@pytest.fixture
def owned_skill(skill_api, skill_owner) -> int:
    return skill_api.seed_skill("skill-owner-id", title="Owner skill")


def _every_endpoint(skill_api, skill_id, headers, zip_bytes):
    """Call every skill endpoint once; return {name: status}."""
    client = skill_api.client
    path = "path=SKILL.md"
    files = {"archive": ("x.zip", zip_bytes, "application/zip")}
    return {
        "detail": client.get(f"/api/skills/{skill_id}", headers=headers).status_code,
        "content": client.get(
            f"/api/skills/{skill_id}/files/content?{path}", headers=headers
        ).status_code,
        "raw": client.get(
            f"/api/skills/{skill_id}/files/raw?{path}", headers=headers
        ).status_code,
        "download": client.get(
            f"/api/skills/{skill_id}/download", headers=headers
        ).status_code,
        "patch": client.patch(
            f"/api/skills/{skill_id}", headers=headers, json={"title": "Hacked"}
        ).status_code,
        "replace": client.put(
            f"/api/skills/{skill_id}/archive", headers=headers, files=files
        ).status_code,
        "delete": client.delete(f"/api/skills/{skill_id}", headers=headers).status_code,
    }


@authenticated_only
class TestAuthEnabled:
    def test_non_owner_gets_404_on_every_endpoint(
        self, skill_api, skill_other, owned_skill, skill_zip_valid_wrapped
    ):
        statuses = _every_endpoint(
            skill_api, owned_skill, skill_other, skill_zip_valid_wrapped
        )
        assert set(statuses.values()) == {404}, statuses
        assert skill_api.count_rows("skill_packages") == 1  # nothing was deleted

    def test_unauthenticated_reads_are_404_and_writes_are_401(
        self, skill_api, owned_skill, skill_zip_valid_wrapped
    ):
        statuses = _every_endpoint(skill_api, owned_skill, {}, skill_zip_valid_wrapped)
        assert statuses["detail"] == statuses["content"] == 404
        assert statuses["raw"] == statuses["download"] == 404
        assert statuses["patch"] == statuses["replace"] == statuses["delete"] == 401

    def test_admin_reads_everything_but_cannot_edit_or_replace_others(
        self, skill_api, skill_admin, owned_skill, skill_zip_valid_wrapped
    ):
        statuses = _every_endpoint(
            skill_api, owned_skill, skill_admin, skill_zip_valid_wrapped
        )
        assert statuses["detail"] == 200
        assert statuses["content"] == 200
        assert statuses["raw"] == 200
        assert statuses["download"] == 200
        assert statuses["patch"] == 404
        assert statuses["replace"] == 404
        assert statuses["delete"] == 204  # administrators may delete any skill
        assert skill_api.count_rows("skill_packages") == 0

    def test_admin_listing_includes_other_users_skills(
        self, skill_api, skill_admin, skill_other, owned_skill
    ):
        for headers, expected in ((skill_admin, 1), (skill_other, 0)):
            listing = skill_api.client.get(
                "/api/prompts?item_type=skill", headers=headers
            ).json()
            assert listing["total_count"] == expected

    def test_owner_has_full_access(
        self, skill_api, skill_owner, owned_skill, skill_zip_valid_wrapped
    ):
        statuses = _every_endpoint(
            skill_api, owned_skill, skill_owner, skill_zip_valid_wrapped
        )
        assert statuses == {
            "detail": 200,
            "content": 200,
            "raw": 200,
            "download": 200,
            "patch": 200,
            "replace": 200,
            "delete": 204,
        }

    def test_prompt_id_on_skill_endpoints_is_409_for_the_owner_and_404_otherwise(
        self, skill_api, skill_owner, skill_other
    ):
        created = skill_api.client.post(
            "/api/prompts",
            headers=skill_owner,
            data={"title": "A prompt", "prompt": "body"},
        ).json()["prompt_id"]
        mine = skill_api.client.get(f"/api/skills/{created}", headers=skill_owner)
        assert mine.status_code == 409
        assert mine.json()["detail"]["code"] == "ITEM_IS_PROMPT"
        theirs = skill_api.client.get(f"/api/skills/{created}", headers=skill_other)
        assert theirs.status_code == 404
        assert (
            skill_api.client.delete(
                f"/api/skills/{created}", headers=skill_owner
            ).status_code
            == 409
        )

    def test_unknown_id_is_a_structured_404(self, skill_api, skill_owner):
        response = skill_api.client.get("/api/skills/987654", headers=skill_owner)
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "SKILL_NOT_FOUND"


@anonymous_only
class TestAnonymousMode:
    """With auth off, skills follow the same guard as their prompt counterparts."""

    def test_import_matches_post_prompts(self, skill_api, skill_zip_valid_wrapped):
        prompt = skill_api.client.post(
            "/api/prompts", data={"title": "t", "prompt": "p"}
        )
        skill = skill_api.import_zip(skill_zip_valid_wrapped, {})
        assert (skill.status_code == 201) == (prompt.status_code == 201)

    def test_replace_and_delete_match_their_prompt_counterparts(
        self, skill_api, skill_zip_valid_wrapped
    ):
        client = skill_api.client
        prompt_id = client.post(
            "/api/prompts", data={"title": "t", "prompt": "p"}
        ).json()["prompt_id"]
        skill_id = skill_api.import_zip(skill_zip_valid_wrapped, {}).json()["skill"][
            "id"
        ]

        prompt_put = client.put(
            f"/api/prompts/{prompt_id}", data={"title": "t2", "prompt": "p2"}
        )
        skill_put = client.put(
            f"/api/skills/{skill_id}/archive",
            files={"archive": ("x.zip", bf.valid_wrapped(), "application/zip")},
        )
        assert prompt_put.is_success == skill_put.is_success

        prompt_del = client.delete(f"/api/prompts/{prompt_id}")
        skill_del = client.delete(f"/api/skills/{skill_id}")
        assert prompt_del.is_success == skill_del.is_success

    def test_reads_are_public(self, skill_api, skill_zip_valid_wrapped):
        skill_id = skill_api.import_zip(skill_zip_valid_wrapped, {}).json()["skill"][
            "id"
        ]
        assert skill_api.client.get(f"/api/skills/{skill_id}").status_code == 200
