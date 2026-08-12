# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""PromptVault repository layer.

This package provides the repository pattern for data access, separating
business logic from database operations.

Repositories available:
    - BaseRepository: Generic base repository with common CRUD operations
    - UserRepository: User authentication and account management
    - SessionRepository: JWT refresh token session management
    - PasswordResetTokenRepository: Password reset token management
    - PromptRepository: Advanced prompt search and filtering
    - SharingRepository: Per-prompt sharing grants (upsert/revoke/list)
    - VersionRepository: Version control operations
    - CategoryRepository: Category management with statistics
    - TagRepository: Tag management with usage tracking

Usage:
    from src.db.repositories import PromptRepository, TagRepository, UserRepository
    from src.db import get_db_session

    with get_db_session() as session:
        prompt_repo = PromptRepository(session)
        prompts = prompt_repo.search(query="email", favorite=True)
"""

from src.db.repositories.backup_audit_log_repository import BackupAuditLogRepository
from src.db.repositories.backup_repository import BackupRepository
from src.db.repositories.backup_schedule_repository import BackupScheduleRepository
from src.db.repositories.backup_storage_provider_repository import (
    BackupStorageProviderRepository,
)
from src.db.repositories.base import BaseRepository
from src.db.repositories.category_repository import CategoryRepository
from src.db.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from src.db.repositories.prompt_repository import PromptRepository
from src.db.repositories.session_repository import SessionRepository
from src.db.repositories.sharing_repository import SharingRepository
from src.db.repositories.tag_repository import TagRepository
from src.db.repositories.user_repository import UserRepository
from src.db.repositories.version_repository import VersionRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "SessionRepository",
    "PasswordResetTokenRepository",
    "PromptRepository",
    "SharingRepository",
    "VersionRepository",
    "CategoryRepository",
    "TagRepository",
    "BackupRepository",
    "BackupScheduleRepository",
    "BackupStorageProviderRepository",
    "BackupAuditLogRepository",
]
