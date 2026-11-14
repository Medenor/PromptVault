# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Lenient ``SKILL.md`` frontmatter parsing (research.md Decisions 4 and 5).

Format problems never reject an upload; they are returned as warning codes.
``SKILL.md`` is stored byte for byte elsewhere, so nothing here rewrites it.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

import yaml

MAX_FRONTMATTER_BYTES = 64 * 1024
MAX_FRONTMATTER_DEPTH = 20
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_TITLE_LENGTH = 200
DEFAULT_IDENTIFIER = "skill"

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\Z")

# Warning codes (stored in skill_packages.format_warnings, translated client-side).
FRONTMATTER_MISSING = "frontmatter_missing"
FRONTMATTER_MALFORMED = "frontmatter_malformed"
NAME_MISSING = "name_missing"
NAME_INVALID = "name_invalid"
NAME_FOLDER_MISMATCH = "name_folder_mismatch"
DESCRIPTION_MISSING = "description_missing"
DESCRIPTION_TOO_LONG = "description_too_long"
NO_WRAPPING_FOLDER = "no_wrapping_folder"
SKILL_MD_NOT_UTF8 = "skill_md_not_utf8"

WARNING_CODES = (
    FRONTMATTER_MISSING,
    FRONTMATTER_MALFORMED,
    NAME_MISSING,
    NAME_INVALID,
    NAME_FOLDER_MISMATCH,
    DESCRIPTION_MISSING,
    DESCRIPTION_TOO_LONG,
    NO_WRAPPING_FOLDER,
    SKILL_MD_NOT_UTF8,
)

_BOM = "\ufeff"


@dataclass
class SkillMetadata:
    """Metadata derived from a ``SKILL.md``.

    Attributes:
        name: Frontmatter ``name`` as a string, or None when absent.
        description: Frontmatter ``description`` as written, or None.
        text: Full decoded ``SKILL.md`` (BOM removed), frontmatter included.
        warnings: Format warning codes, in a stable order.
        identifier: Format-compliant skill identifier (slug).
        title: Initial title (``name`` or the archive file name, max 200 chars).
    """

    name: str | None
    description: str | None
    text: str
    warnings: list[str] = field(default_factory=list)
    identifier: str = DEFAULT_IDENTIFIER
    title: str = DEFAULT_IDENTIFIER


def decode_skill_md(raw: bytes) -> tuple[str, bool]:
    """Decode ``SKILL.md`` bytes as UTF-8, removing a leading byte-order mark.

    Returns:
        Tuple of (text, was_valid_utf8). Invalid bytes become U+FFFD.
    """
    try:
        text, valid = raw.decode("utf-8"), True
    except UnicodeDecodeError:
        text, valid = raw.decode("utf-8", errors="replace"), False
    if text.startswith(_BOM):
        text = text[len(_BOM) :]
    return text, valid


def split_frontmatter(text: str) -> tuple[str | None, str, bool]:
    """Split a ``---`` delimited frontmatter block from the body.

    Returns:
        Tuple of (frontmatter_text, body, is_closed). ``frontmatter_text`` is
        None when the document has no frontmatter. ``is_closed`` is False when
        an opening ``---`` has no closing line.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n").rstrip() != "---":
        return None, text, True
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r\n").rstrip() == "---":
            return "".join(lines[1:index]), "".join(lines[index + 1 :]), True
    return "".join(lines[1:]), "", False


def strip_frontmatter(text: str) -> str:
    """Return ``text`` without its frontmatter block, if it has a closed one."""
    front, body, closed = split_frontmatter(text)
    return body if front is not None and closed else text


def _nesting_depth(value: Any) -> int:
    """Return the nesting depth of a parsed YAML value.

    Memoised by object identity so documents that reuse anchors cannot cause
    exponential work.
    """
    memo: dict[int, int] = {}

    def depth(node: Any, stack: frozenset[int]) -> int:
        if not isinstance(node, dict | list):
            return 0
        key = id(node)
        if key in stack:
            return MAX_FRONTMATTER_DEPTH + 1  # recursive structure
        if key in memo:
            return memo[key]
        children = node.values() if isinstance(node, dict) else node
        result = 1 + max((depth(child, stack | {key}) for child in children), default=0)
        memo[key] = result
        return result

    return depth(value, frozenset())


def _parse_mapping(front: str) -> dict[str, Any] | None:
    """Parse frontmatter YAML; None means malformed."""
    if len(front.encode("utf-8")) > MAX_FRONTMATTER_BYTES:
        return None
    try:
        parsed = yaml.safe_load(front)
    except yaml.YAMLError, RecursionError, ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    if _nesting_depth(parsed) > MAX_FRONTMATTER_DEPTH:
        return None
    return parsed


def slugify(value: str | None) -> str:
    """Turn arbitrary text into a format-compliant identifier (Decision 5)."""
    ascii_text = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", errors="ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    slug = slug[:MAX_NAME_LENGTH].strip("-")
    return slug or DEFAULT_IDENTIFIER


def archive_stem(archive_name: str) -> str:
    """Return the archive file name without directories or a ``.zip`` suffix."""
    base = archive_name.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if base.lower().endswith(".zip"):
        base = base[:-4]
    return base


def _scalar_to_text(value: Any) -> str | None:
    """Return a scalar frontmatter value as text; None for containers/None."""
    if value is None or isinstance(value, dict | list):
        return None
    return str(value)


def parse_skill_md(
    raw: bytes, wrapped_folder_name: str | None, archive_name: str
) -> SkillMetadata:
    """Parse ``SKILL.md`` bytes into metadata and format warnings.

    Args:
        raw: The exact bytes of ``SKILL.md``.
        wrapped_folder_name: Name of the wrapping top-level folder, if any.
        archive_name: Uploaded file name, used as the title fallback.

    Returns:
        SkillMetadata: Never raises for format problems.
    """
    text, valid_utf8 = decode_skill_md(raw)
    warnings: list[str] = []

    front, _body, closed = split_frontmatter(text)
    meta: dict[str, Any] = {}
    if front is None:
        warnings.append(FRONTMATTER_MISSING)
    else:
        parsed = _parse_mapping(front) if closed else None
        if parsed is None:
            warnings.append(FRONTMATTER_MALFORMED)
        else:
            meta = parsed

    name: str | None = None
    description: str | None = None
    if not warnings:  # frontmatter present and well-formed
        name = _scalar_to_text(meta.get("name"))
        if name is not None and not name.strip():
            name = None
        if name is None:
            warnings.append(NAME_MISSING)
        else:
            if len(name) > MAX_NAME_LENGTH or not NAME_PATTERN.match(name):
                warnings.append(NAME_INVALID)
            if wrapped_folder_name is not None and name != wrapped_folder_name:
                warnings.append(NAME_FOLDER_MISMATCH)
        description = _scalar_to_text(meta.get("description"))
        if description is not None and not description.strip():
            description = None
        if description is None:
            warnings.append(DESCRIPTION_MISSING)
        elif len(description) > MAX_DESCRIPTION_LENGTH:
            warnings.append(DESCRIPTION_TOO_LONG)

    if wrapped_folder_name is None:
        warnings.append(NO_WRAPPING_FOLDER)
    if not valid_utf8:
        warnings.append(SKILL_MD_NOT_UTF8)

    stem = archive_stem(archive_name)
    if name is not None and len(name) <= MAX_NAME_LENGTH and NAME_PATTERN.match(name):
        identifier = name
    else:
        identifier = slugify(name if name is not None else stem)
    title = (name if name is not None else stem) or DEFAULT_IDENTIFIER

    return SkillMetadata(
        name=name,
        description=description,
        text=text,
        warnings=warnings,
        identifier=identifier,
        title=title[:MAX_TITLE_LENGTH],
    )
