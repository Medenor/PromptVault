"""PromptVault database models.

This module exports all SQLAlchemy ORM models for the PromptVault application.
Import models from this module for use throughout the application.

Usage:
    from src.db.models import Prompt, PromptVersion, User, Category, Tag

Models exported:
    - User: User accounts
    - Category: Prompt categories
    - Tag: Flexible tags for prompts
    - Prompt: Main prompt entity with current state
    - PromptVersion: Version history (Git-like immutable snapshots)
    - PromptBranch: Branch pointers for version control
    - Backup: Backup metadata
    - prompt_tags: Association table for many-to-many prompt-tag relationship
"""

from src.db.models.user import User
from src.db.models.category import Category
from src.db.models.tag import Tag
from src.db.models.prompt import Prompt
from src.db.models.prompt_version import PromptVersion
from src.db.models.prompt_branch import PromptBranch
from src.db.models.backup import Backup
from src.db.models.associations import prompt_tags

__all__ = [
    "User",
    "Category",
    "Tag",
    "Prompt",
    "PromptVersion",
    "PromptBranch",
    "Backup",
    "prompt_tags",
]
