# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Publish a PromptVault release to GitHub from the maintainer's machine.

    make release            full release (tag, push the tag, GitHub release)
    make release-dry-run    every check, nothing published

Run it on main, after the release PR (made with `make release-prepare`) is
merged. The version comes from pyproject.toml and the release notes from the
matching `## [X.Y.Z]` section of docs/CHANGELOG.md. There are no assets: the
application is deployed from source with Docker Compose.

Re-running after a failure resumes: a tag already on HEAD and an existing
release are reused. A published tag is never moved or deleted.

GitHub access goes through the GitHub CLI (`gh auth login`); no token is read
or printed by this script.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?$"
)
CHANGELOG = "docs/CHANGELOG.md"
CHECKS = (["make", "lint"], ["make", "test"])


class ReleaseError(Exception):
    """A release precondition failed."""


@dataclass(frozen=True)
class Repository:
    host: str
    owner: str
    name: str

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested in tests/test_release_scripts.py)


def is_semver(version: str) -> bool:
    return bool(SEMVER_RE.match(version))


def parse_repository(url: str) -> Repository:
    """'https://github.com/Owner/repo(.git)' -> Repository."""
    match = re.match(r"^https?://([^/]+)/([^/]+)/([^/]+?)(?:\.git)?/?$", url or "")
    if not match:
        raise ReleaseError(
            "pyproject.toml [project.urls] Repository must look like "
            f"https://github.com/<owner>/<repo>, got: {url!r}"
        )
    return Repository(*match.groups())


def remote_matches(remote_url: str, repo: Repository) -> bool:
    """Does a git remote URL point at owner/name on the repository's host?"""
    normalized = remote_url.lower().strip()
    normalized = re.sub(r"^([^/@:]+@[^/:]+):(?!/)", r"ssh://\1/", normalized)
    normalized = re.sub(r"\.git/?$", "", normalized).rstrip("/")
    return repo.host.lower() in normalized and normalized.endswith(
        f"/{repo.slug}".lower()
    )


def changelog_section(changelog: str, version: str) -> str | None:
    """Body of the '## [version]' section of a Keep a Changelog file, or None."""
    lines = changelog.replace("\r\n", "\n").split("\n")
    start = next(
        (i for i, line in enumerate(lines) if line.startswith(f"## [{version}]")),
        None,
    )
    if start is None:
        return None
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if lines[i].startswith("## ") or re.match(r"^\[[^\]]+\]:\s", lines[i])
        ),
        len(lines),
    )
    body = "\n".join(lines[start + 1 : end]).strip()
    return body or None


def redact_credentials(text: str) -> str:
    """Hide credentials embedded in URLs: https://user:secret@host -> https://***@host."""
    return re.sub(r"(\b[a-z][a-z0-9+.-]*://)[^/@\s]+@", r"\1***@", text, flags=re.I)


# ---------------------------------------------------------------------------
# Procedure


def _run(root: Path, *cmd: str, check: bool = True) -> str:
    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        detail = redact_credentials((result.stderr or result.stdout).strip())
        raise ReleaseError(f"{' '.join(cmd[:2])} failed: {detail}")
    return result.stdout.strip() if result.returncode == 0 else ""


def _stream(root: Path, cmd: list[str]) -> None:
    print(f"  $ {' '.join(cmd)}")
    if subprocess.run(cmd, cwd=root, check=False).returncode != 0:
        raise ReleaseError(f"`{' '.join(cmd)}` failed")


def read_project(root: Path) -> tuple[str, Repository]:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    return project["version"], parse_repository(project["urls"]["Repository"])


def publish(
    root: Path = ROOT,
    *,
    dry_run: bool,
    skip_checks: bool = False,
    remote: str = "origin",
) -> None:
    version, repo = read_project(root)
    tag = f"v{version}"
    mode = " (dry run: nothing will be published)" if dry_run else ""
    print(f"\nPromptVault {version} -> {repo.host}/{repo.slug}{mode}\n")

    # 1. Pre-flight ---------------------------------------------------------
    print("1/5 Pre-flight checks")
    if not is_semver(version):
        raise ReleaseError(f"version '{version}' is not semantic versioning (X.Y.Z)")
    branch = _run(root, "git", "rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main":
        raise ReleaseError(f'releases are made from main; you are on "{branch}"')
    if _run(root, "git", "status", "--porcelain"):
        raise ReleaseError("the working tree has uncommitted changes")

    remote_url = _run(root, "git", "remote", "get-url", remote, check=False)
    if not remote_url:
        raise ReleaseError(f'no git remote "{remote}"')
    if not remote_matches(remote_url, repo):
        raise ReleaseError(
            f'remote "{remote}" points to {redact_credentials(remote_url)}, '
            f"not {repo.slug} on {repo.host}"
        )
    _run(root, "git", "fetch", "--quiet", remote, "main")
    head = _run(root, "git", "rev-parse", "HEAD")
    remote_head = _run(root, "git", "rev-parse", f"{remote}/main")
    if head != remote_head:
        raise ReleaseError(
            f"local main ({head[:7]}) differs from {remote}/main "
            f"({remote_head[:7]}); pull or push first"
        )

    notes = changelog_section((root / CHANGELOG).read_text(encoding="utf-8"), version)
    if not notes:
        raise ReleaseError(
            f'{CHANGELOG} has no "## [{version}]" section with content; '
            "write the entries in the release PR (see `make release-prepare`)"
        )

    local_tag = (
        _run(
            root,
            "git",
            "rev-parse",
            "--verify",
            "--quiet",
            f"refs/tags/{tag}^{{commit}}",
            check=False,
        )
        or None
    )
    refs = [
        line.split()
        for line in _run(
            root,
            "git",
            "ls-remote",
            "--tags",
            remote,
            f"refs/tags/{tag}",
            f"refs/tags/{tag}^{{}}",
        ).splitlines()
        if line
    ]
    by_ref = {ref: sha for sha, ref in refs}
    remote_tag = by_ref.get(f"refs/tags/{tag}^{{}}") or by_ref.get(f"refs/tags/{tag}")
    for where, commit in (("locally", local_tag), (f"on {remote}", remote_tag)):
        if commit and commit != head:
            raise ReleaseError(
                f"tag {tag} already exists {where} on another commit ({commit[:7]}); "
                "released versions are never moved, bump the version instead"
            )
    resuming = bool(local_tag or remote_tag)
    if resuming:
        print(f"  Tag {tag} already exists on this commit: resuming.")
    if not resuming and not (
        _run(root, "git", "config", "user.name", check=False)
        and _run(root, "git", "config", "user.email", check=False)
    ):
        raise ReleaseError("git user.name and user.email must be set to create the tag")

    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        raise ReleaseError("not logged in to GitHub; run `gh auth login`")
    perms = _run(
        root,
        "gh",
        "api",
        f"repos/{repo.slug}",
        "--jq",
        ".permissions.push",
    )
    if perms != "true":
        raise ReleaseError(f"your GitHub account cannot push to {repo.slug}")
    print("  OK: main is clean and up to date, changelog section found, gh can push.")

    # 2. Checks -------------------------------------------------------------
    print("\n2/5 Full checks")
    if skip_checks:
        print("  skipped (--skip-checks)")
    else:
        for cmd in CHECKS:
            _stream(root, list(cmd))
        if _run(root, "git", "status", "--porcelain"):
            raise ReleaseError("the checks left the working tree modified")

    prerelease = "-" in version
    if dry_run:
        print("\nDry run complete. A real run would:")
        print(
            f"  - {'reuse' if resuming else 'create and push'} tag {tag} on {head[:7]}"
        )
        kind = "pre-release" if prerelease else "release"
        print(f'  - publish GitHub {kind} "PromptVault {version}" with these notes:\n')
        print(re.sub(r"(?m)^", "    ", notes) + "\n")
        return

    # 3. Tag ----------------------------------------------------------------
    print("\n3/5 Tag")
    if not local_tag and not remote_tag:
        # Signed automatically when git has tag.gpgSign=true; the terminal is
        # passed through so gpg can ask for a passphrase.
        created = subprocess.run(
            ["git", "tag", "-a", tag, "-m", f"PromptVault {version}"],
            cwd=root,
            check=False,
        )
        if created.returncode != 0:
            raise ReleaseError(f"creating tag {tag} failed; nothing was published")
        print(f"  Created {tag}")
    elif not local_tag:
        _run(
            root, "git", "fetch", "--quiet", remote, f"refs/tags/{tag}:refs/tags/{tag}"
        )
        print(f"  Fetched {tag} from {remote}")
    if not remote_tag:
        _run(root, "git", "push", "--quiet", remote, f"refs/tags/{tag}")
        print(f"  Pushed {tag} to {remote}")
    else:
        print(f"  {tag} already on {remote}")

    # 4. Release ------------------------------------------------------------
    print("\n4/5 Release")
    exists = (
        subprocess.run(
            ["gh", "release", "view", tag, "--repo", repo.slug],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    if exists:
        print("  Release already exists: nothing to create.")
    else:
        cmd = [
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            repo.slug,
            "--verify-tag",
            "--title",
            f"PromptVault {version}",
            "--notes-file",
            "-",
        ]
        if prerelease:
            cmd.append("--prerelease")
        created = subprocess.run(cmd, input=notes, text=True, cwd=root, check=False)
        if created.returncode != 0:
            raise ReleaseError(f"creating the GitHub release for {tag} failed")

    # 5. Report -------------------------------------------------------------
    print(f"\n5/5 Done\n  https://{repo.host}/{repo.slug}/releases/tag/{tag}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish a PromptVault release.")
    parser.add_argument("--dry-run", action="store_true", help="check, publish nothing")
    parser.add_argument(
        "--skip-checks", action="store_true", help="skip lint and tests"
    )
    args = parser.parse_args(argv)
    try:
        publish(dry_run=args.dry_run, skip_checks=args.skip_checks)
    except ReleaseError as error:
        print(f"\nerror: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
