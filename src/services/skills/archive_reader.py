# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Hardened, in-memory reader for skill ``.zip`` archives.

Archive entries are never extracted to the filesystem and ``extractall()`` is
never used (research.md Decision 3). Reading happens in two passes:

1. A central-directory pass validates counts, declared sizes, compression
   ratios, paths, links and encryption before any content is read.
2. A content pass reads each file in chunks with live byte counting, so a
   header that lies about its size cannot get round the limits.
"""

import hashlib
import io
import re
import stat
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass, field

from src.config.skill_config import SkillSettings, get_skill_settings
from src.services.skills import errors as err
from src.services.skills.errors import SkillArchiveError

SKILL_MD = "SKILL.md"

_CHUNK_BYTES = 64 * 1024
_RATIO_MIN_BYTES = 1024 * 1024
_CLUTTER_DIRS = frozenset({"__MACOSX"})
_CLUTTER_NAMES = frozenset({".DS_Store", "Thumbs.db"})
_INVALID_NAME_CHARS = frozenset('<>:"|?*')
_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True)
class ArchiveFile:
    """One validated file read from an archive."""

    path: str
    content: bytes
    size: int
    sha256: str
    is_text: bool


@dataclass
class ReadArchive:
    """Result of reading a skill archive."""

    files: list[ArchiveFile] = field(default_factory=list)
    wrapped_folder_name: str | None = None
    has_wrapping_folder: bool = False


@dataclass
class _Entry:
    info: zipfile.ZipInfo
    parts: list[str]


def _is_clutter(raw_name: str) -> bool:
    """Return True for OS clutter entries that are ignored entirely."""
    segments = [s for s in raw_name.replace("\\", "/").split("/") if s]
    if not segments:
        return False
    if any(s in _CLUTTER_DIRS for s in segments):
        return True
    last = segments[-1]
    return last in _CLUTTER_NAMES or last.startswith("._")


def _validate_segment(segment: str, raw_name: str) -> None:
    """Reject path segments that are invalid on common operating systems."""
    if any(ch in _INVALID_NAME_CHARS or ord(ch) < 32 for ch in segment):
        raise SkillArchiveError(
            err.ENTRY_NAME_INVALID, "Entry name contains invalid characters", raw_name
        )
    if segment.endswith((".", " ")):
        raise SkillArchiveError(
            err.ENTRY_NAME_INVALID,
            "Entry name ends with a dot or a space",
            raw_name,
        )
    if segment.split(".", 1)[0].upper() in _RESERVED_NAMES:
        raise SkillArchiveError(
            err.ENTRY_NAME_INVALID, "Entry name is reserved by the OS", raw_name
        )


def _normalise_path(raw_name: str) -> list[str]:
    """Normalise an entry name into validated path segments.

    Raises:
        SkillArchiveError: If the path is absolute, escapes the root or has an
            invalid segment name.
    """
    name = raw_name.replace("\\", "/")
    if name.startswith("/") or _DRIVE_PATTERN.match(name):
        raise SkillArchiveError(
            err.ENTRY_PATH_UNSAFE, "Absolute paths are not allowed", raw_name
        )
    parts: list[str] = []
    for segment in name.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            raise SkillArchiveError(
                err.ENTRY_PATH_UNSAFE,
                "Entry escapes the skill root with '..'",
                raw_name,
            )
        segment = unicodedata.normalize("NFC", segment)
        _validate_segment(segment, raw_name)
        parts.append(segment)
    return parts


def _check_declared(
    info: zipfile.ZipInfo, raw_name: str, settings: SkillSettings
) -> None:
    """Check one entry's declared sizes and compression ratio."""
    if info.file_size > _RATIO_MIN_BYTES:
        ratio = info.file_size / max(info.compress_size, 1)
        if ratio > settings.max_compression_ratio:
            raise SkillArchiveError(
                err.ARCHIVE_SUSPICIOUS_RATIO,
                "Entry has a suspicious compression ratio",
                raw_name,
            )
    if info.file_size > settings.max_file_bytes:
        raise SkillArchiveError(
            err.LIMIT_FILE_SIZE, "File exceeds the per-file size limit", raw_name
        )


def _detect_root(entries: list[_Entry]) -> tuple[int, str | None]:
    """Find the skill root.

    Returns:
        Tuple of (number of leading segments to strip, wrapping folder name).

    Raises:
        SkillArchiveError: If no root with a ``SKILL.md`` can be found.
    """
    file_parts = [e.parts for e in entries]
    if any(parts == [SKILL_MD] for parts in file_parts):
        return 0, None
    top_level = {parts[0] for parts in file_parts}
    has_top_level_file = any(len(parts) == 1 for parts in file_parts)
    if len(top_level) == 1 and not has_top_level_file:
        folder = next(iter(top_level))
        if any(parts == [folder, SKILL_MD] for parts in file_parts):
            return 1, folder
    raise SkillArchiveError(
        err.SKILL_MD_MISSING,
        "SKILL.md not found at the archive root or in a single top-level folder",
    )


def _is_text(content: bytes) -> bool:
    """A file is text when it has no NUL byte and is valid UTF-8."""
    if b"\x00" in content:
        return False
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _read_member(
    zf: zipfile.ZipFile,
    entry: _Entry,
    path: str,
    total_so_far: int,
    settings: SkillSettings,
) -> bytes:
    """Read one member in chunks with live size and ratio limits."""
    buffer = bytearray()
    offending = entry.info.filename
    try:
        with zf.open(entry.info) as handle:
            while chunk := handle.read(_CHUNK_BYTES):
                buffer.extend(chunk)
                size = len(buffer)
                if path == SKILL_MD and size > settings.max_skill_md_bytes:
                    raise SkillArchiveError(
                        err.LIMIT_SKILL_MD_SIZE,
                        "SKILL.md exceeds the size limit",
                        offending,
                    )
                if size > settings.max_file_bytes:
                    raise SkillArchiveError(
                        err.LIMIT_FILE_SIZE, "File exceeds the size limit", offending
                    )
                if total_so_far + size > settings.max_total_bytes:
                    raise SkillArchiveError(
                        err.LIMIT_TOTAL_SIZE,
                        "Archive exceeds the total unpacked size limit",
                        offending,
                    )
                if (
                    size > _RATIO_MIN_BYTES
                    and size / max(entry.info.compress_size, 1)
                    > settings.max_compression_ratio
                ):
                    raise SkillArchiveError(
                        err.ARCHIVE_SUSPICIOUS_RATIO,
                        "Entry has a suspicious compression ratio",
                        offending,
                    )
    except SkillArchiveError:
        raise
    except (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError) as exc:
        raise SkillArchiveError(
            err.ARCHIVE_INVALID, "Archive entry is corrupt or unsupported", offending
        ) from exc
    except RuntimeError as exc:  # encrypted member without a password
        raise SkillArchiveError(
            err.ARCHIVE_ENCRYPTED,
            "Password-protected entries are not supported",
            offending,
        ) from exc
    return bytes(buffer)


class SkillArchiveReader:
    """Reads and validates a skill archive entirely in memory."""

    def __init__(self, settings: SkillSettings | None = None) -> None:
        self._settings = settings or get_skill_settings()

    def read(self, data: bytes, archive_name: str = "skill.zip") -> ReadArchive:
        """Read a skill archive.

        Args:
            data: The raw bytes of the uploaded ``.zip``.
            archive_name: Original file name, used only in error context.

        Returns:
            ReadArchive: Validated files with paths relative to the skill root.

        Raises:
            SkillArchiveError: If the archive is invalid, unsafe or over a limit.
        """
        settings = self._settings
        if not data:
            raise SkillArchiveError(err.ARCHIVE_INVALID, "Archive is empty")
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except (zipfile.BadZipFile, zlib.error, EOFError, ValueError) as exc:
            raise SkillArchiveError(
                err.ARCHIVE_INVALID, "File is not a valid zip archive"
            ) from exc

        with zf:
            entries = self._scan_directory(zf, settings)
            if not entries:
                raise SkillArchiveError(err.ARCHIVE_INVALID, "Archive has no files")
            strip, folder = _detect_root(entries)
            return self._read_contents(zf, entries, strip, folder, settings)

    def _scan_directory(
        self, zf: zipfile.ZipFile, settings: SkillSettings
    ) -> list[_Entry]:
        """Central-directory pass: validate every non-clutter entry."""
        entries: list[_Entry] = []
        file_count = 0
        declared_total = 0
        for info in zf.infolist():
            raw_name = info.filename
            if _is_clutter(raw_name):
                continue
            mode = info.external_attr >> 16
            if mode and stat.S_ISLNK(mode):
                raise SkillArchiveError(
                    err.ENTRY_LINK, "Symbolic links are not allowed", raw_name
                )
            if info.flag_bits & 0x1:
                raise SkillArchiveError(
                    err.ARCHIVE_ENCRYPTED,
                    "Password-protected entries are not supported",
                    raw_name,
                )
            parts = _normalise_path(raw_name)
            if info.is_dir() or not parts:
                continue  # empty folders are dropped (FR-009)
            file_count += 1
            if file_count > settings.max_files:
                raise SkillArchiveError(
                    err.LIMIT_FILE_COUNT, "Archive has too many files"
                )
            _check_declared(info, raw_name, settings)
            declared_total += info.file_size
            if declared_total > settings.max_total_bytes:
                raise SkillArchiveError(
                    err.LIMIT_TOTAL_SIZE,
                    "Archive exceeds the total unpacked size limit",
                    raw_name,
                )
            entries.append(_Entry(info=info, parts=parts))
        return entries

    def _read_contents(
        self,
        zf: zipfile.ZipFile,
        entries: list[_Entry],
        strip: int,
        folder: str | None,
        settings: SkillSettings,
    ) -> ReadArchive:
        """Content pass: strip the wrapping folder, then read every file."""
        seen: dict[str, str] = {}
        planned: list[tuple[_Entry, str]] = []
        for entry in entries:
            rel_parts = entry.parts[strip:]
            if len(rel_parts) - 1 > settings.max_depth:
                raise SkillArchiveError(
                    err.LIMIT_DEPTH,
                    "Folder nesting is deeper than allowed",
                    entry.info.filename,
                )
            path = "/".join(rel_parts)
            folded = path.casefold()
            if folded in seen:
                raise SkillArchiveError(
                    err.ENTRY_DUPLICATE, "Duplicate entry path", entry.info.filename
                )
            seen[folded] = path
            if path == SKILL_MD and entry.info.file_size > settings.max_skill_md_bytes:
                raise SkillArchiveError(
                    err.LIMIT_SKILL_MD_SIZE,
                    "SKILL.md exceeds the size limit",
                    entry.info.filename,
                )
            planned.append((entry, path))

        files: list[ArchiveFile] = []
        total = 0
        for entry, path in planned:
            content = _read_member(zf, entry, path, total, settings)
            total += len(content)
            files.append(
                ArchiveFile(
                    path=path,
                    content=content,
                    size=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                    is_text=_is_text(content),
                )
            )
        return ReadArchive(
            files=files,
            wrapped_folder_name=folder,
            has_wrapping_folder=folder is not None,
        )
