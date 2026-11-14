# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Builds skill archives (valid, lenient and malicious) in memory at test time.

No binary fixtures are committed (quickstart.md). Every builder returns the raw
bytes of a ``.zip`` archive.
"""

import io
import struct
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass

SKILL_MD_VALID = (
    "---\n"
    "name: pdf-tools\n"
    "description: Fill PDF forms and extract tables.\n"
    "license: MIT\n"
    "---\n"
    "# PDF tools\n"
    "Run `python3 ${CLAUDE_SKILL_DIR}/scripts/fill.py` to fill a form.\n"
)

BINARY_SAMPLE = bytes(range(256)) * 8  # 2048 bytes, contains NUL
SYMLINK_MODE = 0o120777 << 16

Content = bytes | str


def _to_bytes(content: Content) -> bytes:
    return content.encode("utf-8") if isinstance(content, str) else content


def build_zip(
    entries: Iterable[tuple[str, Content]],
    *,
    compression: int = zipfile.ZIP_DEFLATED,
    symlinks: Iterable[str] = (),
) -> bytes:
    """Build a zip from ``(name, content)`` pairs.

    Names ending in ``/`` become directory entries. Names listed in
    ``symlinks`` get a Unix symbolic-link mode.
    """
    link_names = set(symlinks)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as zf:
        for name, content in entries:
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 2, 3, 4, 6))
            info.compress_type = compression
            info.create_system = 3
            if name in link_names:
                info.external_attr = SYMLINK_MODE
            elif name.endswith("/"):
                info.external_attr = (0o40755 << 16) | 0x10
            else:
                info.external_attr = 0o100644 << 16
            zf.writestr(info, _to_bytes(content))
    return buffer.getvalue()


def set_central_flag_bits(data: bytes, bits: int) -> bytes:
    """OR ``bits`` into the general-purpose flag of every central-directory entry."""
    out = bytearray(data)
    signature = b"PK\x01\x02"
    index = out.find(signature)
    while index != -1:
        (flags,) = struct.unpack_from("<H", out, index + 8)
        struct.pack_into("<H", out, index + 8, flags | bits)
        index = out.find(signature, index + 4)
    return bytes(out)


def valid_wrapped() -> bytes:
    """Standard layout: ``pdf-tools/`` folder with text and binary files."""
    return build_zip(
        [
            ("pdf-tools/", ""),
            ("pdf-tools/SKILL.md", SKILL_MD_VALID),
            ("pdf-tools/scripts/", ""),
            ("pdf-tools/scripts/fill.py", 'print("hi")\n'),
            ("pdf-tools/references/sample.bin", BINARY_SAMPLE),
            ("pdf-tools/empty-folder/", ""),
        ]
    )


def valid_root_level() -> bytes:
    """``SKILL.md`` directly at the archive root (no wrapping folder)."""
    return build_zip(
        [
            ("SKILL.md", SKILL_MD_VALID),
            ("scripts/fill.py", 'print("hi")\n'),
        ]
    )


def no_frontmatter() -> bytes:
    return build_zip([("SKILL.md", "# Just instructions\nNo frontmatter here.\n")])


def bad_name() -> bytes:
    text = "---\nname: Bad Name!\ndescription: ok\n---\nbody\n"
    return build_zip([("bad-skill/SKILL.md", text)])


def with_clutter() -> bytes:
    return build_zip(
        [
            ("pdf-tools/SKILL.md", SKILL_MD_VALID),
            ("pdf-tools/.DS_Store", b"\x00\x00"),
            ("pdf-tools/Thumbs.db", b"junk"),
            ("pdf-tools/._SKILL.md", b"appledouble"),
            ("__MACOSX/pdf-tools/._SKILL.md", b"appledouble"),
            ("__MACOSX/", ""),
        ]
    )


def path_traversal() -> bytes:
    return build_zip([("SKILL.md", SKILL_MD_VALID), ("../evil.txt", "owned")])


def nested_traversal() -> bytes:
    return build_zip([("SKILL.md", SKILL_MD_VALID), ("a/../../evil.txt", "owned")])


def absolute_path() -> bytes:
    return build_zip([("SKILL.md", SKILL_MD_VALID), ("/etc/passwd", "owned")])


def windows_drive_path() -> bytes:
    return build_zip([("SKILL.md", SKILL_MD_VALID), ("C:/Windows/x.txt", "owned")])


def symbolic_link() -> bytes:
    return build_zip(
        [("SKILL.md", SKILL_MD_VALID), ("link", "/etc/passwd")], symlinks=["link"]
    )


def case_duplicate() -> bytes:
    return build_zip(
        [
            ("SKILL.md", SKILL_MD_VALID),
            ("docs/README.md", "one"),
            ("docs/readme.md", "two"),
        ]
    )


def exact_duplicate() -> bytes:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # zipfile warns on duplicates
        return build_zip(
            [("SKILL.md", SKILL_MD_VALID), ("a.txt", "one"), ("a.txt", "two")]
        )


def too_deep(levels: int = 11) -> bytes:
    path = "/".join(f"d{i}" for i in range(levels)) + "/leaf.txt"
    return build_zip([("SKILL.md", SKILL_MD_VALID), (path, "deep")])


def too_many_files(count: int = 501) -> bytes:
    entries: list[tuple[str, Content]] = [("SKILL.md", SKILL_MD_VALID)]
    entries += [(f"files/f{i}.txt", "x") for i in range(count - 1)]
    return build_zip(entries)


def oversized_file(size: int = 10 * 1024 * 1024 + 1) -> bytes:
    return build_zip(
        [("SKILL.md", SKILL_MD_VALID), ("big.bin", b"\x01" * size)],
        compression=zipfile.ZIP_STORED,
    )


def oversized_skill_md(size: int = 1024 * 1024 + 1) -> bytes:
    body = "---\nname: big\ndescription: big\n---\n" + "a" * size
    return build_zip([("SKILL.md", body)], compression=zipfile.ZIP_STORED)


def total_too_large(files: int = 6, each: int = 9 * 1024 * 1024) -> bytes:
    entries: list[tuple[str, Content]] = [("SKILL.md", SKILL_MD_VALID)]
    entries += [(f"part{i}.bin", bytes([i + 1]) * each) for i in range(files)]
    return build_zip(entries, compression=zipfile.ZIP_STORED)


def compression_bomb(size: int = 5 * 1024 * 1024) -> bytes:
    return build_zip([("SKILL.md", SKILL_MD_VALID), ("bomb.txt", b"0" * size)])


def encrypted_entry() -> bytes:
    return set_central_flag_bits(valid_root_level(), 0x1)


def corrupt_bytes() -> bytes:
    return b"this is definitely not a zip archive"


def truncated_zip() -> bytes:
    data = valid_wrapped()
    return data[: len(data) // 2]


def empty_zip() -> bytes:
    return build_zip([])


def only_clutter() -> bytes:
    return build_zip([(".DS_Store", b"x"), ("__MACOSX/x", b"y")])


def no_skill_md() -> bytes:
    return build_zip([("pdf-tools/README.md", "hello")])


def two_top_level_folders() -> bytes:
    return build_zip([("a/SKILL.md", SKILL_MD_VALID), ("b/other.txt", "x")])


def stray_top_level_file() -> bytes:
    return build_zip([("pdf-tools/SKILL.md", SKILL_MD_VALID), ("README.md", "x")])


def invalid_windows_name() -> bytes:
    return build_zip([("SKILL.md", SKILL_MD_VALID), ("docs/what?.md", "x")])


def reserved_windows_name() -> bytes:
    return build_zip([("SKILL.md", SKILL_MD_VALID), ("CON.txt", "x")])


def trailing_dot_name() -> bytes:
    return build_zip([("SKILL.md", SKILL_MD_VALID), ("notes.", "x")])


def non_utf8_skill_md() -> bytes:
    return build_zip(
        [("pdf-tools/SKILL.md", b"---\nname: pdf-tools\n---\n\xff\xfe bad")]
    )


@dataclass(frozen=True)
class RejectedCase:
    """A malicious or invalid archive and the rejection it must produce."""

    id: str
    build: Callable[[], bytes]
    code: str
    offending_entry: str | None = None


REJECTED_CASES: list[RejectedCase] = [
    RejectedCase("path-traversal", path_traversal, "ENTRY_PATH_UNSAFE", "../evil.txt"),
    RejectedCase(
        "nested-traversal", nested_traversal, "ENTRY_PATH_UNSAFE", "a/../../evil.txt"
    ),
    RejectedCase("absolute-path", absolute_path, "ENTRY_PATH_UNSAFE", "/etc/passwd"),
    RejectedCase(
        "windows-drive", windows_drive_path, "ENTRY_PATH_UNSAFE", "C:/Windows/x.txt"
    ),
    RejectedCase("symlink", symbolic_link, "ENTRY_LINK", "link"),
    RejectedCase("case-duplicate", case_duplicate, "ENTRY_DUPLICATE", "docs/readme.md"),
    RejectedCase("exact-duplicate", exact_duplicate, "ENTRY_DUPLICATE", "a.txt"),
    RejectedCase(
        "invalid-char", invalid_windows_name, "ENTRY_NAME_INVALID", "docs/what?.md"
    ),
    RejectedCase(
        "reserved-name", reserved_windows_name, "ENTRY_NAME_INVALID", "CON.txt"
    ),
    RejectedCase("trailing-dot", trailing_dot_name, "ENTRY_NAME_INVALID", "notes."),
    RejectedCase("too-deep", too_deep, "LIMIT_DEPTH"),
    RejectedCase("too-many-files", too_many_files, "LIMIT_FILE_COUNT"),
    RejectedCase("oversized-file", oversized_file, "LIMIT_FILE_SIZE", "big.bin"),
    RejectedCase(
        "oversized-skill-md", oversized_skill_md, "LIMIT_SKILL_MD_SIZE", "SKILL.md"
    ),
    RejectedCase("total-too-large", total_too_large, "LIMIT_TOTAL_SIZE"),
    RejectedCase(
        "compression-bomb", compression_bomb, "ARCHIVE_SUSPICIOUS_RATIO", "bomb.txt"
    ),
    RejectedCase("encrypted", encrypted_entry, "ARCHIVE_ENCRYPTED"),
    RejectedCase("corrupt", corrupt_bytes, "ARCHIVE_INVALID"),
    RejectedCase("truncated", truncated_zip, "ARCHIVE_INVALID"),
    RejectedCase("empty-zip", empty_zip, "ARCHIVE_INVALID"),
    RejectedCase("only-clutter", only_clutter, "ARCHIVE_INVALID"),
    RejectedCase("no-skill-md", no_skill_md, "SKILL_MD_MISSING"),
    RejectedCase("two-top-level-folders", two_top_level_folders, "SKILL_MD_MISSING"),
    RejectedCase("stray-top-level-file", stray_top_level_file, "SKILL_MD_MISSING"),
]
