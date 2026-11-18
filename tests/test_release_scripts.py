# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for scripts/release_prepare.py and scripts/release_publish.py."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses look the module up by name
    spec.loader.exec_module(module)
    return module


prepare = _load("release_prepare")
publish = _load("release_publish")

PACKAGE_JSON = (
    '{\n  "name": "promptvault",\n  "version": "1.14.1",\n  "private": true\n}\n'
)
PACKAGE_LOCK = (
    '{\n  "name": "promptvault",\n  "version": "1.14.1",\n  "packages": {\n'
    '    "": {\n      "name": "promptvault",\n      "version": "1.14.1"\n    },\n'
    '    "node_modules/foo": {\n      "version": "1.14.1"\n    }\n  }\n}\n'
)
PYPROJECT = (
    '[project]\nname = "promptvault"\nversion = "1.14.1"\n\n'
    '[project.urls]\nRepository = "https://github.com/Medenor/PromptVault"\n'
)
UV_LOCK = (
    '[[package]]\nname = "other"\nversion = "1.14.1"\n\n'
    '[[package]]\nname = "promptvault"\nversion = "1.14.1"\n'
)
CHANGELOG = (
    "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- A new thing.\n\n"
    "## [1.14.1] - 2026-11-14\n\n- Fixed a bug.\n"
)
NOTES_EN = (
    "# Release Notes\n\n## Unreleased {#unreleased}\n\nSome text.\n\n"
    "## 1.14.1\n\n- Fix.\n"
)
NOTES_NO_UNRELEASED = "# Release Notes\n\n## 1.14.1\n\n- Fix.\n"


def _write_tree(root: Path, notes: str = NOTES_EN) -> None:
    files = {
        "package.json": PACKAGE_JSON,
        "package-lock.json": PACKAGE_LOCK,
        "pyproject.toml": PYPROJECT,
        "uv.lock": UV_LOCK,
        "docs/CHANGELOG.md": CHANGELOG,
    }
    for rel in prepare.RELEASE_NOTES_FILES:
        files[rel] = notes
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    _write_tree(tmp_path)
    return tmp_path


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def git_tree(tree: Path) -> Path:
    _git(tree, "init", "-q", "-b", "main")
    _git(tree, "config", "user.email", "test@example.com")
    _git(tree, "config", "user.name", "Test")
    _git(tree, "add", "-A")
    _git(tree, "commit", "-q", "-m", "init")
    return tree


# ---------------------------------------------------------------------------
# release_prepare


class TestPrepareVersionChecks:
    def test_current_version_reads_pyproject(self, tree: Path) -> None:
        assert prepare.current_version(tree) == "1.14.1"

    @pytest.mark.parametrize("bad", ["1.14", "v1.15.0", "1.15.0-rc1", "abc", ""])
    def test_rejects_non_semver(self, bad: str) -> None:
        with pytest.raises(prepare.ReleaseError):
            prepare.parse_semver(bad)

    @pytest.mark.parametrize("new", ["1.14.1", "1.14.0", "1.0.0"])
    def test_rejects_version_not_greater(self, new: str) -> None:
        with pytest.raises(prepare.ReleaseError, match="greater"):
            prepare.validate_version(new, "1.14.1")

    def test_accepts_greater_version(self) -> None:
        prepare.validate_version("1.14.2", "1.14.1")
        prepare.validate_version("1.15.0", "1.14.1")
        prepare.validate_version("2.0.0", "1.14.1")


class TestPreparePlan:
    def test_every_file_is_updated(self, tree: Path) -> None:
        changes = prepare.plan_changes(tree, "1.15.0", "2026-12-01")
        assert len(changes) == 9
        for path, (old, new) in changes.items():
            assert old != new, path

    def test_version_strings(self, tree: Path) -> None:
        changes = prepare.plan_changes(tree, "1.15.0", "2026-12-01")
        assert '"version": "1.15.0"' in changes[tree / "package.json"][1]
        lock = changes[tree / "package-lock.json"][1]
        assert lock.count('"version": "1.15.0"') == 2
        # An unrelated dependency that happens to share the old version is untouched.
        assert '"node_modules/foo": {\n      "version": "1.14.1"' in lock
        assert 'version = "1.15.0"' in changes[tree / "pyproject.toml"][1]
        uv = changes[tree / "uv.lock"][1]
        assert 'name = "other"\nversion = "1.14.1"' in uv
        assert 'name = "promptvault"\nversion = "1.15.0"' in uv

    def test_changelog_gets_dated_section_and_empty_unreleased(
        self, tree: Path
    ) -> None:
        new = prepare.plan_changes(tree, "1.15.0", "2026-12-01")[
            tree / "docs/CHANGELOG.md"
        ][1]
        assert "## [Unreleased]\n\n## [1.15.0] - 2026-12-01\n\n### Added" in new
        assert new.count("## [Unreleased]") == 1

    def test_release_notes_unreleased_heading_becomes_version(self, tree: Path) -> None:
        for rel in prepare.RELEASE_NOTES_FILES:
            new = prepare.plan_changes(tree, "1.15.0", "2026-12-01")[tree / rel][1]
            assert "## 1.15.0\n\nSome text." in new
            assert "{#unreleased}" not in new

    def test_release_notes_stub_when_no_unreleased_section(
        self, tmp_path: Path
    ) -> None:
        _write_tree(tmp_path, NOTES_NO_UNRELEASED)
        rel = prepare.RELEASE_NOTES_FILES[0]
        new = prepare.plan_changes(tmp_path, "1.15.0", "2026-12-01")[tmp_path / rel][1]
        assert new.index("## 1.15.0") < new.index("## 1.14.1")
        assert prepare.RELEASE_NOTES_STUB in new

    def test_missing_version_in_a_file_is_reported(self, tree: Path) -> None:
        (tree / "uv.lock").write_text('[[package]]\nname = "x"\n', encoding="utf-8")
        with pytest.raises(prepare.ReleaseError, match="uv.lock"):
            prepare.plan_changes(tree, "1.15.0", "2026-12-01")

    def test_existing_changelog_version_is_rejected(self, tree: Path) -> None:
        with pytest.raises(prepare.ReleaseError, match="already"):
            prepare.bump_changelog(CHANGELOG, "1.14.1", "2026-12-01")


class TestPrepareCli:
    def test_dry_run_writes_nothing(
        self, git_tree: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        before = {
            p: p.read_text()
            for p in git_tree.rglob("*")
            if p.is_file() and ".git" not in p.parts
        }
        code = prepare.main(["--version", "1.15.0", "--dry-run"], root=git_tree)
        out = capsys.readouterr().out
        assert code == 0
        assert "9 files would change" in out
        assert '+version = "1.15.0"' in out
        after = {
            p: p.read_text()
            for p in git_tree.rglob("*")
            if p.is_file() and ".git" not in p.parts
        }
        assert after == before

    def test_apply_updates_files(self, git_tree: Path) -> None:
        code = prepare.main(
            ["--version", "1.15.0", "--skip-checks", "--today", "2026-12-01"],
            root=git_tree,
        )
        assert code == 0
        assert prepare.current_version(git_tree) == "1.15.0"
        assert (
            "## [1.15.0] - 2026-12-01" in (git_tree / "docs/CHANGELOG.md").read_text()
        )

    def test_dirty_tree_is_refused(
        self, git_tree: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (git_tree / "package.json").write_text(PACKAGE_JSON + "\n")
        assert prepare.main(["--version", "1.15.0", "--dry-run"], root=git_tree) == 1
        assert "not clean" in capsys.readouterr().err

    def test_wrong_branch_is_refused(
        self, git_tree: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _git(git_tree, "switch", "-q", "-c", "feature/x")
        assert prepare.main(["--version", "1.15.0", "--dry-run"], root=git_tree) == 1
        assert "expected main or release/v1.15.0" in capsys.readouterr().err

    def test_release_branch_is_accepted(self, git_tree: Path) -> None:
        _git(git_tree, "switch", "-q", "-c", "release/v1.15.0")
        assert prepare.main(["--version", "1.15.0", "--dry-run"], root=git_tree) == 0

    def test_lower_version_is_refused(
        self, git_tree: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert prepare.main(["--version", "1.14.0", "--dry-run"], root=git_tree) == 1
        assert "greater" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# release_publish


class TestPublishHelpers:
    @pytest.mark.parametrize(
        ("version", "ok"),
        [("1.15.0", True), ("1.15.0-rc.1", True), ("1.15", False), ("v1.15.0", False)],
    )
    def test_is_semver(self, version: str, ok: bool) -> None:
        assert publish.is_semver(version) is ok

    def test_parse_repository(self) -> None:
        repo = publish.parse_repository("https://github.com/Medenor/PromptVault.git")
        assert (repo.host, repo.owner, repo.name) == (
            "github.com",
            "Medenor",
            "PromptVault",
        )
        assert repo.slug == "Medenor/PromptVault"

    def test_parse_repository_rejects_garbage(self) -> None:
        with pytest.raises(publish.ReleaseError):
            publish.parse_repository("not a url")

    @pytest.mark.parametrize(
        ("url", "ok"),
        [
            ("https://github.com/Medenor/PromptVault.git", True),
            ("https://github.com/medenor/promptvault", True),
            ("git@github.com:Medenor/PromptVault.git", True),
            ("ssh://git@github.com/Medenor/PromptVault.git", True),
            ("https://github.com/Medenor/other.git", False),
            ("https://codeberg.org/Medenor/PromptVault.git", False),
        ],
    )
    def test_remote_matches(self, url: str, ok: bool) -> None:
        repo = publish.parse_repository("https://github.com/Medenor/PromptVault")
        assert publish.remote_matches(url, repo) is ok

    def test_changelog_section_returns_only_that_version(self) -> None:
        text = (
            "## [Unreleased]\n\n## [1.15.0] - 2026-12-01\n\n### Added\n\n- New.\n\n"
            "## [1.14.1] - 2026-11-14\n\n- Old.\n"
        )
        assert publish.changelog_section(text, "1.15.0") == "### Added\n\n- New."
        assert publish.changelog_section(text, "1.14.1") == "- Old."

    def test_changelog_section_stops_at_link_references(self) -> None:
        text = "## [1.15.0] - 2026-12-01\n\n- New.\n\n[1.15.0]: https://example.com\n"
        assert publish.changelog_section(text, "1.15.0") == "- New."

    def test_changelog_section_missing_or_empty(self) -> None:
        assert publish.changelog_section("## [1.14.1] - x\n\n- a\n", "1.15.0") is None
        assert (
            publish.changelog_section("## [1.15.0] - x\n\n## [1.14.1] - y\n", "1.15.0")
            is None
        )

    def test_redact_credentials(self) -> None:
        assert (
            publish.redact_credentials("https://user:secret@github.com/a/b")
            == "https://***@github.com/a/b"
        )
        assert publish.redact_credentials("no url here") == "no url here"


class TestPublishPreflight:
    def test_wrong_branch_is_refused(
        self, git_tree: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _git(git_tree, "switch", "-q", "-c", "feature/x")
        with pytest.raises(publish.ReleaseError, match="from main"):
            publish.publish(git_tree, dry_run=True, skip_checks=True)

    def test_dirty_tree_is_refused(self, git_tree: Path) -> None:
        (git_tree / "package.json").write_text(PACKAGE_JSON + "\n")
        with pytest.raises(publish.ReleaseError, match="uncommitted"):
            publish.publish(git_tree, dry_run=True, skip_checks=True)

    def test_missing_remote_is_refused(self, git_tree: Path) -> None:
        with pytest.raises(publish.ReleaseError, match="no git remote"):
            publish.publish(git_tree, dry_run=True, skip_checks=True)

    def test_remote_pointing_elsewhere_is_refused(self, git_tree: Path) -> None:
        _git(git_tree, "remote", "add", "origin", "https://github.com/someone/else.git")
        with pytest.raises(publish.ReleaseError, match="not Medenor/PromptVault"):
            publish.publish(git_tree, dry_run=True, skip_checks=True)
