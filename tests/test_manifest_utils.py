# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for Vite manifest utilities."""

import json

from src.web.utils import manifest as manifest_utils


def test_manifest_loads_and_resolves_asset(tmp_path, monkeypatch):
    manifest_file = tmp_path / "manifest.json"
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()

    manifest_file.write_text(
        json.dumps({"entry.ts": {"file": "assets/entry.123.js"}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(manifest_utils, "MANIFEST_PATH", manifest_file)
    monkeypatch.setattr(manifest_utils, "DIST_PATH", dist_dir)
    manifest_utils.clear_manifest_cache()

    manifest = manifest_utils.load_manifest()
    assert manifest["entry.ts"]["file"] == "assets/entry.123.js"
    assert manifest_utils.get_asset_path("entry.ts") == "assets/entry.123.js"
    assert manifest_utils.get_asset_path("missing.js") == "missing.js"
    assert manifest_utils.is_production() is True


def test_manifest_loads_empty_on_missing_file(tmp_path, monkeypatch):
    manifest_file = tmp_path / "missing.json"
    dist_dir = tmp_path / "dist"

    monkeypatch.setattr(manifest_utils, "MANIFEST_PATH", manifest_file)
    monkeypatch.setattr(manifest_utils, "DIST_PATH", dist_dir)
    manifest_utils.clear_manifest_cache()

    assert manifest_utils.load_manifest() == {}
    assert manifest_utils.is_production() is False


def test_manifest_loads_empty_on_invalid_json(tmp_path, monkeypatch):
    manifest_file = tmp_path / "manifest.json"
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()

    manifest_file.write_text("{not-json", encoding="utf-8")

    monkeypatch.setattr(manifest_utils, "MANIFEST_PATH", manifest_file)
    monkeypatch.setattr(manifest_utils, "DIST_PATH", dist_dir)
    manifest_utils.clear_manifest_cache()

    assert manifest_utils.load_manifest() == {}
