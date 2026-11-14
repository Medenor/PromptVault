# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic response models for the skills API (contracts/skills-api.md)."""

from typing import Literal

from pydantic import BaseModel, Field


class SkillSummary(BaseModel):
    """A skill in list and search results.

    Deliberately has no ``prompt`` field: clients fetch ``SkillDetail`` from
    ``/api/skills/{id}`` before showing instructions, so a large ``SKILL.md``
    is never sent with a list page.
    """

    id: int = Field(..., description="Item ID (shared with prompts)")
    item_type: Literal["skill"] = Field(..., description="Always 'skill'")
    title: str = Field(..., description="Editable title")
    skill_identifier: str = Field(..., description="Format-compliant identifier")
    description: str | None = Field(None, description="Frontmatter description")
    category: str = Field("", description="Category name")
    category_color: str | None = Field(None, description="Category color")
    tags: list[str] = Field(default_factory=list, description="Tag names")
    tag_colors: dict[str, str | None] = Field(default_factory=dict)
    favorite: bool | None = Field(False, description="Favorite status")
    file_count: int = Field(..., description="Number of stored files")
    total_bytes: int = Field(..., description="Total size of stored files")
    format_warnings: list[str] = Field(
        default_factory=list, description="Format warning codes recorded at import"
    )
    user_id: str | None = Field(None, description="Owner's user ID")
    created_at: str | None = Field(None, description="Creation timestamp (ISO)")
    updated_at: str | None = Field(None, description="Update timestamp (ISO)")


class SkillFileEntry(BaseModel):
    """One stored file of a skill (no content)."""

    path: str = Field(..., description="Path relative to the skill root")
    size: int = Field(..., description="Size in bytes")
    is_text: bool = Field(..., description="True for UTF-8 text without NUL bytes")
    sha256: str = Field(..., description="Lowercase hex SHA-256 of the content")


class SkillDetailResponse(SkillSummary):
    """A skill with its sanitised instructions and file list."""

    note: str = Field("", description="Optional note")
    instructions_html: str = Field(
        ..., description="Server-sanitised HTML of the SKILL.md body"
    )
    files: list[SkillFileEntry] = Field(default_factory=list)


class SkillImportResponse(BaseModel):
    """Result of importing or replacing a skill archive."""

    skill: SkillDetailResponse
    warnings: list[str] = Field(
        default_factory=list, description="Same list as skill.format_warnings"
    )


class SkillFileContentResponse(BaseModel):
    """Text preview of one stored file."""

    path: str
    size: int
    is_text: bool
    truncated: bool = Field(
        ..., description="True when text was cut to the preview limit"
    )
    text: str | None = Field(None, description="Text, or null for binary files")
