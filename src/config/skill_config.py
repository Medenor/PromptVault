# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Limits and tunables for skill package uploads.

Every value can be overridden through an environment variable with the
``SKILL_`` prefix (research.md Decision 9), for example
``SKILL_MAX_FILES=200``.

Environment Variables:
    SKILL_MAX_UPLOAD_BYTES: Largest accepted ``.zip`` upload.
    SKILL_MAX_TOTAL_BYTES: Largest total unpacked size of one skill.
    SKILL_MAX_FILES: Largest number of files in one skill.
    SKILL_MAX_DEPTH: Deepest folder nesting allowed.
    SKILL_MAX_FILE_BYTES: Largest single unpacked file.
    SKILL_MAX_COMPRESSION_RATIO: Highest allowed compression ratio for a
        large entry (zip-bomb defence).
    SKILL_TEXT_PREVIEW_BYTES: Largest text excerpt returned by the viewer.
    SKILL_MAX_SKILL_MD_BYTES: Largest accepted ``SKILL.md``.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

MEGABYTE = 1024 * 1024

# Extra room on top of the archive limit for multipart boundaries and form fields.
MULTIPART_OVERHEAD_BYTES = 64 * 1024


class SkillSettings(BaseSettings):
    """Upload and unpacking limits for skill packages."""

    model_config = SettingsConfigDict(
        env_prefix="SKILL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    max_upload_bytes: int = Field(default=10 * MEGABYTE, gt=0)
    max_total_bytes: int = Field(default=50 * MEGABYTE, gt=0)
    max_files: int = Field(default=500, gt=0)
    max_depth: int = Field(default=10, gt=0)
    max_file_bytes: int = Field(default=10 * MEGABYTE, gt=0)
    max_compression_ratio: int = Field(default=100, gt=0)
    text_preview_bytes: int = Field(default=MEGABYTE, gt=0)
    max_skill_md_bytes: int = Field(default=MEGABYTE, gt=0)


@lru_cache
def get_skill_settings() -> SkillSettings:
    """Return the cached skill settings.

    Tests that change the environment call ``get_skill_settings.cache_clear()``.

    Returns:
        SkillSettings: The process-wide settings instance.
    """
    return SkillSettings()
