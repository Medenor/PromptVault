"""Category model for PromptVault.

Categories provide organizational grouping for prompts.
Each category has a unique name and optional description.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.base import Base


class Category(Base):
    """Category model for organizing prompts.

    Attributes:
        id: Auto-incrementing integer primary key
        name: Unique category name (max 100 chars, as per SPEC_APP.md REQ-006)
        description: Optional category description
        created_at: Timestamp when category was created
        prompts: Relationship to prompts in this category
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    prompts = relationship("Prompt", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"
