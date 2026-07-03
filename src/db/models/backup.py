# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Backup model for PromptVault.

This model tracks backup metadata for both PostgreSQL (pg_dump) and
SQLite (file copy) backup operations.
"""

from sqlalchemy import Column, String, Text, BigInteger, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.sql import func

from src.db.base import Base


class Backup(Base):
    """Backup metadata model.

    Stores metadata about database backups. Actual backup files are stored
    in the filesystem (data/backups/), while this table tracks metadata.

    Supports both PostgreSQL (pg_dump) and SQLite (file copy) backups, as
    well as JSON export backups for compatibility.

    Attributes:
        id: UUID primary key (stored as String for SQLite compatibility)
        backup_type: Type of backup ('pg_dump', 'sqlite_copy', 'json_export')
        filename: Backup file name
        storage_path: Full path to backup file
        size_bytes: Backup file size in bytes
        prompt_count: Number of prompts in backup
        created_by: Username who created the backup
        created_at: Timestamp when backup was created
        succeeded: Whether backup completed successfully
        backup_metadata: Additional backup metadata as JSON
    """

    __tablename__ = "backups"

    id = Column(String(36), primary_key=True)
    backup_type = Column(
        String(50), nullable=False
    )  # 'pg_dump', 'sqlite_copy', 'json_export'
    filename = Column(String(255), nullable=False)
    storage_path = Column(Text, nullable=False)
    size_bytes = Column(BigInteger)
    prompt_count = Column(Integer)
    created_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    succeeded = Column(Boolean, default=True)
    backup_metadata = Column(
        JSON
    )  # Additional backup metadata (versions included, etc.)

    def __repr__(self):
        return f"<Backup(id='{self.id[:8]}...', type='{self.backup_type}', filename='{self.filename}')>"
