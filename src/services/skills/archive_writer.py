# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Build a standard-layout skill archive for download (FR-019, FR-020).

The archive is created per request, never stored, and deterministic: the same
files and timestamp always produce the same bytes.
"""

import tempfile
import zipfile
from collections.abc import Iterable
from datetime import datetime
from typing import IO

SPOOL_MAX_BYTES = 8 * 1024 * 1024

# ZIP timestamps cannot represent years before 1980.
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
_REGULAR_FILE_MODE = 0o100644 << 16


def _zip_timestamp(timestamp: datetime) -> tuple[int, int, int, int, int, int]:
    """Convert a datetime to a ZIP-safe date tuple (even seconds, >= 1980)."""
    if timestamp.year < 1980:
        return _ZIP_EPOCH
    return (
        timestamp.year,
        timestamp.month,
        timestamp.day,
        timestamp.hour,
        timestamp.minute,
        timestamp.second - timestamp.second % 2,
    )


def write_skill_archive(
    identifier: str,
    files: Iterable[tuple[str, bytes]],
    timestamp: datetime,
) -> IO[bytes]:
    """Write ``<identifier>/<path>`` entries into a spooled temporary file.

    Args:
        identifier: Skill identifier, used as the top-level folder name.
        files: ``(relative path, content)`` pairs, in the order to write.
        timestamp: Fixed modification time for every entry.

    Returns:
        A ``SpooledTemporaryFile`` positioned at the start. In memory up to
        8 MB, then on disk; the caller must close it.
    """
    spool = tempfile.SpooledTemporaryFile(max_size=SPOOL_MAX_BYTES)
    date_time = _zip_timestamp(timestamp)
    try:
        with zipfile.ZipFile(spool, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path, content in files:
                info = zipfile.ZipInfo(f"{identifier}/{path}", date_time=date_time)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = _REGULAR_FILE_MODE
                info.create_system = 3
                zf.writestr(info, content)
    except BaseException:
        spool.close()
        raise
    spool.seek(0)
    return spool
