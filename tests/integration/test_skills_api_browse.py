# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Browsing a stored skill (User Story 2): detail, file content, raw download."""

import pytest
from fixtures.skills import build_fixtures as bf

from src.config.skill_config import get_skill_settings

HOSTILE_SKILL_MD = (
    "---\nname: hostile\ndescription: d\n---\n"
    "# Title\n<script>alert(1)</script>\n<img src=x onerror=alert(1)>\n"
    "[bad](javascript:alert(1))\nRun ${CLAUDE_SKILL_DIR}/run.sh\n"
)


@pytest.fixture
def imported(skill_api, skill_owner, skill_zip_valid_wrapped) -> dict:
    return skill_api.import_zip(skill_zip_valid_wrapped, skill_owner).json()["skill"]


class TestDetail:
    def test_detail_has_the_contract_shape(self, skill_api, skill_owner, imported):
        body = skill_api.client.get(
            f"/api/skills/{imported['id']}", headers=skill_owner
        ).json()
        for key in (
            "id",
            "item_type",
            "title",
            "skill_identifier",
            "description",
            "category",
            "tags",
            "favorite",
            "file_count",
            "total_bytes",
            "format_warnings",
            "created_at",
            "updated_at",
            "note",
            "instructions_html",
            "files",
        ):
            assert key in body, key
        assert body["item_type"] == "skill"
        assert "prompt" not in body

    def test_files_are_listed_with_size_flag_and_hash(
        self, skill_api, skill_owner, imported
    ):
        body = skill_api.client.get(
            f"/api/skills/{imported['id']}", headers=skill_owner
        ).json()
        by_path = {f["path"]: f for f in body["files"]}
        assert by_path["scripts/fill.py"]["is_text"] is True
        assert by_path["references/sample.bin"]["is_text"] is False
        assert by_path["references/sample.bin"]["size"] == len(bf.BINARY_SAMPLE)

    def test_placeholders_stay_literal_and_html_is_inert(
        self, skill_api, skill_owner, make_skill_zip
    ):
        data = make_skill_zip([("SKILL.md", HOSTILE_SKILL_MD)])
        skill_id = skill_api.import_zip(data, skill_owner).json()["skill"]["id"]
        html = skill_api.client.get(
            f"/api/skills/{skill_id}", headers=skill_owner
        ).json()["instructions_html"]
        assert "${CLAUDE_SKILL_DIR}/run.sh" in html
        assert "<script" not in html and "<img" not in html
        assert "&lt;script&gt;" in html
        assert "javascript:" not in html.split("href=")[-1] if "href=" in html else True
        assert "name: hostile" not in html  # frontmatter removed

    def test_not_found_and_prompt_ids(self, skill_api, skill_owner):
        assert (
            skill_api.client.get("/api/skills/424242", headers=skill_owner).status_code
            == 404
        )
        prompt_id = skill_api.client.post(
            "/api/prompts", headers=skill_owner, data={"title": "p", "prompt": "b"}
        ).json()["prompt_id"]
        response = skill_api.client.get(f"/api/skills/{prompt_id}", headers=skill_owner)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "ITEM_IS_PROMPT"


class TestFileContent:
    def _get(self, skill_api, headers, skill_id, path):
        return skill_api.client.get(
            f"/api/skills/{skill_id}/files/content",
            headers=headers,
            params={"path": path},
        )

    def test_text_file_returns_its_text(self, skill_api, skill_owner, imported):
        response = self._get(skill_api, skill_owner, imported["id"], "scripts/fill.py")
        assert response.status_code == 200
        assert response.json() == {
            "path": "scripts/fill.py",
            "size": len(b'print("hi")\n'),
            "is_text": True,
            "truncated": False,
            "text": 'print("hi")\n',
        }

    def test_binary_file_has_no_text(self, skill_api, skill_owner, imported):
        body = self._get(
            skill_api, skill_owner, imported["id"], "references/sample.bin"
        ).json()
        assert body["is_text"] is False
        assert body["text"] is None
        assert body["truncated"] is False

    def test_unknown_path_is_a_structured_404(self, skill_api, skill_owner, imported):
        response = self._get(skill_api, skill_owner, imported["id"], "nope.md")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "FILE_NOT_FOUND"

    def test_path_is_matched_exactly_and_traversal_finds_nothing(
        self, skill_api, skill_owner, imported
    ):
        for path in ("../SKILL.md", "/SKILL.md", "skill.md", "scripts"):
            assert (
                self._get(skill_api, skill_owner, imported["id"], path).status_code
                == 404
            )

    def test_text_is_cut_at_a_character_boundary(
        self, skill_api, skill_owner, monkeypatch
    ):
        monkeypatch.setenv("SKILL_TEXT_PREVIEW_BYTES", "10")
        get_skill_settings.cache_clear()
        try:
            text = "é" * 20  # 2 bytes per character
            skill_id = skill_api.seed_skill(
                "skill-owner-id",
                files={"SKILL.md": bf.SKILL_MD_VALID.encode(), "a.txt": text.encode()},
            )
            body = self._get(skill_api, skill_owner, skill_id, "a.txt").json()
        finally:
            monkeypatch.delenv("SKILL_TEXT_PREVIEW_BYTES")
            get_skill_settings.cache_clear()
        assert body["truncated"] is True
        assert body["size"] == 40
        assert body["text"] == "é" * 5
        assert len(body["text"].encode()) <= 10

    def test_odd_limit_never_splits_a_character(
        self, skill_api, skill_owner, monkeypatch
    ):
        monkeypatch.setenv("SKILL_TEXT_PREVIEW_BYTES", "9")
        get_skill_settings.cache_clear()
        try:
            skill_id = skill_api.seed_skill(
                "skill-owner-id",
                files={
                    "SKILL.md": bf.SKILL_MD_VALID.encode(),
                    "a.txt": ("é" * 20).encode(),
                },
            )
            body = self._get(skill_api, skill_owner, skill_id, "a.txt").json()
        finally:
            monkeypatch.delenv("SKILL_TEXT_PREVIEW_BYTES")
            get_skill_settings.cache_clear()
        assert body["text"] == "é" * 4
        assert "\ufffd" not in body["text"]

    def test_xss_shaped_text_is_returned_verbatim_as_data(self, skill_api, skill_owner):
        payload = "<script>alert(1)</script>"
        skill_id = skill_api.seed_skill(
            "skill-owner-id",
            files={"SKILL.md": bf.SKILL_MD_VALID.encode(), "x.html": payload.encode()},
        )
        body = self._get(skill_api, skill_owner, skill_id, "x.html").json()
        assert body["text"] == payload


class TestRawDownload:
    def _raw(self, skill_api, headers, skill_id, path):
        return skill_api.client.get(
            f"/api/skills/{skill_id}/files/raw", headers=headers, params={"path": path}
        )

    def test_exact_bytes_and_safe_headers(self, skill_api, skill_owner, imported):
        response = self._raw(
            skill_api, skill_owner, imported["id"], "references/sample.bin"
        )
        assert response.status_code == 200
        assert response.content == bf.BINARY_SAMPLE
        assert response.headers["content-type"] == "application/octet-stream"
        assert response.headers["content-disposition"].startswith("attachment;")
        assert "filename*=UTF-8''sample.bin" in response.headers["content-disposition"]
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["content-security-policy"] == "sandbox"

    def test_non_ascii_names_use_rfc5987_encoding(self, skill_api, skill_owner):
        skill_id = skill_api.seed_skill(
            "skill-owner-id",
            files={
                "SKILL.md": bf.SKILL_MD_VALID.encode(),
                "docs/résumé final.txt": b"cv",
            },
        )
        response = self._raw(skill_api, skill_owner, skill_id, "docs/résumé final.txt")
        assert response.content == b"cv"
        assert (
            "filename*=UTF-8''r%C3%A9sum%C3%A9%20final.txt"
            in response.headers["content-disposition"]
        )

    def test_html_is_never_served_as_html(self, skill_api, skill_owner):
        skill_id = skill_api.seed_skill(
            "skill-owner-id",
            files={
                "SKILL.md": bf.SKILL_MD_VALID.encode(),
                "evil.html": b"<script>alert(1)</script>",
            },
        )
        response = self._raw(skill_api, skill_owner, skill_id, "evil.html")
        assert response.headers["content-type"] == "application/octet-stream"
        assert "attachment" in response.headers["content-disposition"]

    def test_unknown_file_is_404(self, skill_api, skill_owner, imported):
        assert (
            self._raw(skill_api, skill_owner, imported["id"], "missing").status_code
            == 404
        )

    def test_other_users_skill_is_404(self, skill_api, skill_other, imported):
        assert (
            self._raw(skill_api, skill_other, imported["id"], "SKILL.md").status_code
            == 404
        )
