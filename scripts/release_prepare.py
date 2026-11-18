# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prepare a PromptVault release: bump the version everywhere it appears.

Usage:
    python scripts/release_prepare.py --version X.Y.Z --dry-run   # show the diff, write nothing
    python scripts/release_prepare.py --version X.Y.Z             # apply and run the checks

The script only edits files. It never commits, pushes, tags or opens a PR.
Release-notes text and changelog entries still need a human (or an agent);
the script creates the structure around them.

Files updated:
    package.json, package-lock.json (two places), pyproject.toml, uv.lock,
    docs/CHANGELOG.md, and the release notes of the docs portal (en/fr/de/es).
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
RELEASE_NOTES_FILES = (
    "docs-portal/docs/release-notes/index.md",
    "docs-portal/i18n/fr/docusaurus-plugin-content-docs/current/release-notes/index.md",
    "docs-portal/i18n/de/docusaurus-plugin-content-docs/current/release-notes/index.md",
    "docs-portal/i18n/es/docusaurus-plugin-content-docs/current/release-notes/index.md",
)
RELEASE_NOTES_STUB = "- TODO: write the release notes for this version."


class ReleaseError(Exception):
    """A release precondition failed or a file no longer has the expected shape."""


def parse_semver(value: str) -> tuple[int, int, int]:
    match = SEMVER_RE.match(value)
    if not match:
        raise ReleaseError(f"'{value}' is not a valid X.Y.Z version")
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def current_version(root: Path) -> str:
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, flags=re.MULTILINE)
    if not match:
        raise ReleaseError("pyproject.toml: no top-level version found")
    return match.group(1)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def check_git_state(root: Path, version: str) -> None:
    """Require a clean tree on main or on release/vX.Y.Z."""
    if _git(root, "status", "--porcelain"):
        raise ReleaseError("working tree is not clean; commit or stash first")
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    allowed = {"main", f"release/v{version}"}
    if branch not in allowed:
        raise ReleaseError(f"on branch '{branch}'; expected main or release/v{version}")


def validate_version(new: str, current: str) -> None:
    if parse_semver(new) <= parse_semver(current):
        raise ReleaseError(f"version {new} must be greater than current {current}")


def _sub_once(pattern: str, repl: str, text: str, label: str, count: int = 1) -> str:
    new_text, n = re.subn(pattern, repl, text, count=count, flags=re.MULTILINE)
    if n != count:
        raise ReleaseError(f"{label}: expected {count} version match(es), found {n}")
    return new_text


def bump_package_json(text: str, version: str) -> str:
    return _sub_once(
        r'^(  "version": ")[^"]+(")', rf"\g<1>{version}\2", text, "package.json"
    )


def bump_package_lock(text: str, version: str) -> str:
    # Two places: the top-level entry and packages[""], both right after the name.
    return _sub_once(
        r'("name": "promptvault",\s*"version": ")[^"]+(")',
        rf"\g<1>{version}\2",
        text,
        "package-lock.json",
        count=2,
    )


def bump_pyproject(text: str, version: str) -> str:
    return _sub_once(
        r'^(version = ")[^"]+(")', rf"\g<1>{version}\2", text, "pyproject.toml"
    )


def bump_uv_lock(text: str, version: str) -> str:
    return _sub_once(
        r'(name = "promptvault"\nversion = ")[^"]+(")',
        rf"\g<1>{version}\2",
        text,
        "uv.lock",
    )


def bump_changelog(text: str, version: str, today: str) -> str:
    """Rename [Unreleased] to the new version and re-add an empty [Unreleased]."""
    if f"## [{version}]" in text:
        raise ReleaseError(f"docs/CHANGELOG.md already has a [{version}] section")
    return _sub_once(
        r"^## \[Unreleased\]\n",
        f"## [Unreleased]\n\n## [{version}] - {today}\n",
        text,
        "docs/CHANGELOG.md",
    )


def bump_release_notes(text: str, version: str, label: str) -> str:
    """Turn the 'Unreleased {#unreleased}' heading into the version heading.

    If the page has no unreleased section, insert a stub before the first
    version heading. Heading counts stay equal across locales (parity check).
    """
    if re.search(rf"^## {re.escape(version)}[ \t]*$", text, flags=re.MULTILINE):
        raise ReleaseError(f"{label}: already has a '## {version}' section")
    unreleased = re.compile(r"^## .*\{#unreleased\}[ \t]*$", flags=re.MULTILINE)
    if unreleased.search(text):
        return unreleased.sub(f"## {version}", text, count=1)
    first_version = re.search(r"^## \d+\.\d+\.\d+[ \t]*$", text, flags=re.MULTILINE)
    if not first_version:
        raise ReleaseError(f"{label}: no version heading to insert before")
    stub = f"## {version}\n\n{RELEASE_NOTES_STUB}\n\n"
    return text[: first_version.start()] + stub + text[first_version.start() :]


def plan_changes(root: Path, version: str, today: str) -> dict[Path, tuple[str, str]]:
    """Return {path: (old_text, new_text)} for every file that changes."""
    steps = [
        ("package.json", lambda t: bump_package_json(t, version)),
        ("package-lock.json", lambda t: bump_package_lock(t, version)),
        ("pyproject.toml", lambda t: bump_pyproject(t, version)),
        ("uv.lock", lambda t: bump_uv_lock(t, version)),
        ("docs/CHANGELOG.md", lambda t: bump_changelog(t, version, today)),
    ]
    steps += [
        (rel, lambda t, rel=rel: bump_release_notes(t, version, rel))
        for rel in RELEASE_NOTES_FILES
    ]
    changes: dict[Path, tuple[str, str]] = {}
    for rel, fn in steps:
        path = root / rel
        old = path.read_text(encoding="utf-8")
        changes[path] = (old, fn(old))
    return changes


def render_diff(root: Path, changes: dict[Path, tuple[str, str]]) -> str:
    chunks = []
    for path, (old, new) in changes.items():
        rel = path.relative_to(root).as_posix()
        chunks.append(
            "".join(
                difflib.unified_diff(
                    old.splitlines(keepends=True),
                    new.splitlines(keepends=True),
                    fromfile=f"a/{rel}",
                    tofile=f"b/{rel}",
                )
            )
        )
    return "\n".join(chunks)


def run_checks(root: Path) -> None:
    """Docs parity check and template snapshot tests; raise on failure."""
    commands = [
        ["npm", "--prefix", "docs-portal", "run", "docs:check-parity"],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_template_snapshots.py",
            "-q",
            "--no-cov",
        ],
    ]
    for cmd in commands:
        print(f"$ {' '.join(cmd)}")
        if subprocess.run(cmd, cwd=root, check=False).returncode != 0:
            raise ReleaseError(f"check failed: {' '.join(cmd)}")


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description="Prepare a PromptVault release.")
    parser.add_argument("--version", required=True, help="new version, X.Y.Z")
    parser.add_argument(
        "--dry-run", action="store_true", help="print the diff, write nothing"
    )
    parser.add_argument(
        "--skip-checks", action="store_true", help="do not run parity/snapshot checks"
    )
    parser.add_argument(
        "--today", default=date.today().isoformat(), help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)

    try:
        current = current_version(root)
        validate_version(args.version, current)
        check_git_state(root, args.version)
        changes = plan_changes(root, args.version, args.today)
        print(f"Release {current} -> {args.version}")
        print(
            f"{len(changes)} files would change:"
            if args.dry_run
            else f"Updating {len(changes)} files:"
        )
        for path in changes:
            print(f"  {path.relative_to(root).as_posix()}")
        if args.dry_run:
            print()
            print(render_diff(root, changes))
            return 0
        for path, (_, new) in changes.items():
            path.write_text(new, encoding="utf-8")
        if not args.skip_checks:
            run_checks(root)
        print(
            "\nDone. Next: write the changelog entries and release notes, "
            "review `git diff`, open the release PR, then tag the merge commit."
        )
        return 0
    except ReleaseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
