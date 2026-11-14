# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prompt model for PromptVault.

This is the core model representing a prompt with its current state.
Version history is stored separately in PromptVersion model.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.category import Category
    from src.db.models.prompt_branch import PromptBranch
    from src.db.models.prompt_share import PromptShare
    from src.db.models.prompt_version import PromptVersion
    from src.db.models.skill_file import SkillFile
    from src.db.models.skill_package import SkillPackage
    from src.db.models.tag import Tag
    from src.db.models.user import User


class Prompt(Base):
    """Main prompt model with current state.

    This model stores the current version of each prompt. Historical versions
    are stored in the PromptVersion model. Integer IDs are preserved from the
    JSON migration to maintain backward compatibility.

    Attributes:
        id: Integer primary key (preserved from JSON data, not auto-increment)
        title: Prompt title (1-200 chars, as per SPEC_APP.md REQ-006)
        prompt: Prompt content (1-50000 chars, as per SPEC_APP.md REQ-006)
        category_id: Foreign key to categories table
        note: Optional note/description (max 2000 chars, as per SPEC_APP.md REQ-006)
        favorite: Boolean flag for favorited prompts
        item_type: 'prompt' (default) or 'skill'; a skill stores its SKILL.md text
            in ``prompt`` and its files in ``skill_files``
        user_id: Foreign key to users table
        created_at: Timestamp when prompt was created
        updated_at: Timestamp when prompt was last updated
        category: Relationship to Category model
        tags: Many-to-many relationship to Tag model
        versions: One-to-many relationship to PromptVersion model
        branches: One-to-many relationship to PromptBranch model
        user: Relationship to User model
    """

    __tablename__ = "prompts"

    # Integer IDs with autoincrement (migration can override with explicit IDs)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    note: Mapped[str | None] = mapped_column(Text)
    favorite: Mapped[bool | None] = mapped_column(default=False, index=True)
    semantic_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    legacy_public: Mapped[bool] = mapped_column(nullable=False, default=False)
    item_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="prompt", server_default="prompt"
    )
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships
    category: Mapped["Category | None"] = relationship(
        "Category", back_populates="prompts"
    )
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary="prompt_tags", back_populates="prompts"
    )
    versions: Mapped[list["PromptVersion"]] = relationship(
        "PromptVersion",
        back_populates="parent_prompt",
        cascade="all, delete-orphan",
        order_by="PromptVersion.version_number",
    )
    branches: Mapped[list["PromptBranch"]] = relationship(
        "PromptBranch", back_populates="prompt", cascade="all, delete-orphan"
    )
    user: Mapped["User | None"] = relationship("User", back_populates="prompts")
    shares: Mapped[list["PromptShare"]] = relationship(
        "PromptShare", back_populates="prompt", cascade="all, delete-orphan"
    )
    # No passive_deletes: the ORM removes children itself so deletes cascade on
    # any SQLite engine (foreign_keys PRAGMA is only set on the app engine);
    # ON DELETE CASCADE in the schema remains as a backstop for raw SQL.
    skill_package: Mapped["SkillPackage | None"] = relationship(
        "SkillPackage",
        back_populates="prompt",
        uselist=False,
        cascade="all, delete-orphan",
    )
    skill_files: Mapped[list["SkillFile"]] = relationship(
        "SkillFile",
        back_populates="prompt",
        cascade="all, delete-orphan",
    )

    # Composite indices for common query patterns
    __table_args__ = (
        Index("idx_prompts_title", "title"),
        Index("idx_prompts_category", "category_id"),
        Index("idx_prompts_user", "user_id"),
        Index("idx_prompts_item_type", "item_type"),
        CheckConstraint("item_type IN ('prompt', 'skill')", name="item_type"),
    )

    def __repr__(self):
        return f"<Prompt(id={self.id}, title='{self.title[:30]}...')>"
