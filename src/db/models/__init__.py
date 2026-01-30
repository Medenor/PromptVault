# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""PromptVault database models.

This module exports all SQLAlchemy ORM models for the PromptVault application.
Import models from this module for use throughout the application.

Usage:
    from src.db.models import Prompt, PromptVersion, User, UserSession, Category, Tag

Models exported:
    - User: User accounts
    - UserSession: JWT refresh token sessions
    - PasswordResetToken: Password reset tokens
    - Category: Prompt categories
    - Tag: Flexible tags for prompts
    - Prompt: Main prompt entity with current state
    - PromptVersion: Version history (Git-like immutable snapshots)
    - PromptBranch: Branch pointers for version control
    - Backup: Backup metadata
    - UndoOperation: Undo operation history for tags and categories
    - prompt_tags: Association table for many-to-many prompt-tag relationship
"""

from src.db.models.user import User
from src.db.models.user_session import UserSession
from src.db.models.password_reset_token import PasswordResetToken
from src.db.models.category import Category
from src.db.models.tag import Tag
from src.db.models.prompt import Prompt
from src.db.models.prompt_version import PromptVersion
from src.db.models.prompt_branch import PromptBranch
from src.db.models.backup import Backup
from src.db.models.undo_operation import UndoOperation
from src.db.models.associations import prompt_tags

__all__ = [
    "User",
    "UserSession",
    "PasswordResetToken",
    "Category",
    "Tag",
    "Prompt",
    "PromptVersion",
    "PromptBranch",
    "Backup",
    "UndoOperation",
    "prompt_tags",
]
