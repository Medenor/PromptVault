# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Error type and codes for rejected skill archives.

The codes are part of the public API contract (contracts/skills-api.md) and
are translated in the client, so they must not be renamed.
"""

ARCHIVE_INVALID = "ARCHIVE_INVALID"
ARCHIVE_ENCRYPTED = "ARCHIVE_ENCRYPTED"
SKILL_MD_MISSING = "SKILL_MD_MISSING"
ENTRY_PATH_UNSAFE = "ENTRY_PATH_UNSAFE"
ENTRY_LINK = "ENTRY_LINK"
ENTRY_NAME_INVALID = "ENTRY_NAME_INVALID"
ENTRY_DUPLICATE = "ENTRY_DUPLICATE"
LIMIT_DEPTH = "LIMIT_DEPTH"
LIMIT_FILE_COUNT = "LIMIT_FILE_COUNT"
LIMIT_FILE_SIZE = "LIMIT_FILE_SIZE"
LIMIT_TOTAL_SIZE = "LIMIT_TOTAL_SIZE"
ARCHIVE_SUSPICIOUS_RATIO = "ARCHIVE_SUSPICIOUS_RATIO"
LIMIT_SKILL_MD_SIZE = "LIMIT_SKILL_MD_SIZE"
LIMIT_UPLOAD_SIZE = "LIMIT_UPLOAD_SIZE"

SKILL_NOT_FOUND = "SKILL_NOT_FOUND"
FILE_NOT_FOUND = "FILE_NOT_FOUND"

ARCHIVE_ERROR_CODES = frozenset(
    {
        ARCHIVE_INVALID,
        ARCHIVE_ENCRYPTED,
        SKILL_MD_MISSING,
        ENTRY_PATH_UNSAFE,
        ENTRY_LINK,
        ENTRY_NAME_INVALID,
        ENTRY_DUPLICATE,
        LIMIT_DEPTH,
        LIMIT_FILE_COUNT,
        LIMIT_FILE_SIZE,
        LIMIT_TOTAL_SIZE,
        ARCHIVE_SUSPICIOUS_RATIO,
        LIMIT_SKILL_MD_SIZE,
        LIMIT_UPLOAD_SIZE,
    }
)


class SkillArchiveError(Exception):
    """A skill archive was rejected.

    Attributes:
        code: Stable machine-readable error code (see module constants).
        message: Developer-facing English description.
        offending_entry: Archive entry that caused the rejection, if any.
    """

    def __init__(
        self, code: str, message: str, offending_entry: str | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.offending_entry = offending_entry

    @property
    def http_status(self) -> int:
        """HTTP status for this rejection: 413 for upload size, 400 otherwise."""
        return 413 if self.code == LIMIT_UPLOAD_SIZE else 400

    def to_detail(self) -> dict[str, str | None]:
        """Return the ``detail`` body defined in the API contract."""
        return {
            "code": self.code,
            "message": self.message,
            "offending_entry": self.offending_entry,
        }
