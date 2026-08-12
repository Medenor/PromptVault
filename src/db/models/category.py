# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Category model for PromptVault.

Categories provide organizational grouping for prompts.
Each category has a unique name and optional description.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.prompt import Prompt


class Category(Base):
    """Category model for organizing prompts.

    Attributes:
        id: Auto-incrementing integer primary key
        name: Unique category name (max 100 chars, as per SPEC_APP.md REQ-006)
        description: Optional category description
        created_at: Timestamp when category was created
        updated_at: Timestamp when category was last updated
        color: Optional display color token or hex value
        sort_order: Optional custom order for category display
        prompts: Relationship to prompts in this category
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    color: Mapped[str | None] = mapped_column(String(20))
    sort_order: Mapped[int | None] = mapped_column()

    # Relationships
    prompts: Mapped[list["Prompt"]] = relationship("Prompt", back_populates="category")

    __table_args__ = (Index("ix_categories_name_lower", func.lower(name), unique=True),)

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"
