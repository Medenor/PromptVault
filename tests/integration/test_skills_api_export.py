# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Exporting a skill as a zip (User Story 3)."""

import hashlib
import io
import zipfile

import pytest
from fixtures.skills import build_fixtures as bf


@pytest.fixture
def imported(skill_api, skill_owner, skill_zip_valid_wrapped) -> dict:
    return skill_api.import_zip(skill_zip_valid_wrapped, skill_owner).json()["skill"]


def _download(skill_api, headers, skill_id):
    return skill_api.client.get(f"/api/skills/{skill_id}/download", headers=headers)


def _entries(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return {
            info.filename: zf.read(info) for info in zf.infolist() if not info.is_dir()
        }


class TestDownload:
    def test_headers(self, skill_api, skill_owner, imported):
        response = _download(skill_api, skill_owner, imported["id"])
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert (
            response.headers["content-disposition"]
            == 'attachment; filename="pdf-tools.zip"'
        )
        assert int(response.headers["content-length"]) == len(response.content)

    def test_standard_layout_and_byte_identical_files(
        self, skill_api, skill_owner, imported
    ):
        entries = _entries(_download(skill_api, skill_owner, imported["id"]).content)
        assert set(entries) == {
            "pdf-tools/SKILL.md",
            "pdf-tools/scripts/fill.py",
            "pdf-tools/references/sample.bin",
        }
        assert entries["pdf-tools/SKILL.md"] == bf.SKILL_MD_VALID.encode()
        assert entries["pdf-tools/scripts/fill.py"] == b'print("hi")\n'
        assert entries["pdf-tools/references/sample.bin"] == bf.BINARY_SAMPLE

    def test_hashes_match_the_detail_view(self, skill_api, skill_owner, imported):
        entries = _entries(_download(skill_api, skill_owner, imported["id"]).content)
        for file in imported["files"]:
            digest = hashlib.sha256(entries[f"pdf-tools/{file['path']}"]).hexdigest()
            assert digest == file["sha256"]

    def test_archive_keeps_the_identifier_name_after_a_title_change(
        self, skill_api, skill_owner, imported
    ):
        skill_api.client.patch(
            f"/api/skills/{imported['id']}",
            headers=skill_owner,
            json={"title": "My renamed skill"},
        )
        response = _download(skill_api, skill_owner, imported["id"])
        assert 'filename="pdf-tools.zip"' in response.headers["content-disposition"]
        assert all(n.startswith("pdf-tools/") for n in _entries(response.content))

    def test_same_skill_always_exports_the_same_bytes(
        self, skill_api, skill_owner, imported
    ):
        first = _download(skill_api, skill_owner, imported["id"]).content
        second = _download(skill_api, skill_owner, imported["id"]).content
        assert first == second

    def test_round_trip_imports_again_without_warnings(
        self, skill_api, skill_owner, imported
    ):
        exported = _download(skill_api, skill_owner, imported["id"]).content
        again = skill_api.import_zip(exported, skill_owner, filename="pdf-tools.zip")
        assert again.status_code == 201
        body = again.json()
        assert body["warnings"] == []
        assert {f["sha256"] for f in body["skill"]["files"]} == {
            f["sha256"] for f in imported["files"]
        }

    def test_root_level_import_exports_with_the_standard_wrapping_folder(
        self, skill_api, skill_owner, skill_zip_valid_root
    ):
        skill = skill_api.import_zip(skill_zip_valid_root, skill_owner).json()["skill"]
        entries = _entries(_download(skill_api, skill_owner, skill["id"]).content)
        assert "pdf-tools/SKILL.md" in entries

    def test_other_users_skill_is_404(self, skill_api, skill_other, imported):
        assert _download(skill_api, skill_other, imported["id"]).status_code == 404

    def test_download_stores_nothing(self, skill_api, skill_owner, imported):
        before = {t: skill_api.count_rows(t) for t in ("prompts", "skill_files")}
        _download(skill_api, skill_owner, imported["id"])
        after = {t: skill_api.count_rows(t) for t in ("prompts", "skill_files")}
        assert before == after

    def test_unknown_skill_is_404(self, skill_api, skill_owner):
        assert _download(skill_api, skill_owner, 31337).status_code == 404
