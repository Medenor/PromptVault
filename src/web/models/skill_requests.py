# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic request models for the skills API (contracts/skills-api.md)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.web.validators import (
    MAX_CATEGORY_LENGTH,
    MAX_NOTE_LENGTH,
    MAX_TAG_COUNT,
    MAX_TAG_LENGTH,
    MAX_TITLE_LENGTH,
)


class SkillUpdateRequest(BaseModel):
    """Editable skill metadata (``PATCH /api/skills/{id}``).

    Files, ``prompt``, description and identifier cannot be changed here:
    ``extra='forbid'`` makes any such field a 422. Only fields present in the
    request are applied; ``category: null`` clears the category.
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, min_length=1, max_length=MAX_TITLE_LENGTH)
    category: str | None = Field(None, max_length=MAX_CATEGORY_LENGTH)
    tags: list[str] | None = Field(None, max_length=MAX_TAG_COUNT)
    note: str | None = Field(None, max_length=MAX_NOTE_LENGTH)
    favorite: bool | None = None

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("title must not be blank")
        return value

    @field_validator("tags")
    @classmethod
    def _tag_length(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and any(len(tag) > MAX_TAG_LENGTH for tag in value):
            raise ValueError(f"each tag must be at most {MAX_TAG_LENGTH} characters")
        return value
