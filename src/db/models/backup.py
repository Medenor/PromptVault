# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Backup model for PromptVault.

This model tracks backup metadata for both PostgreSQL (pg_dump) and
SQLite (file copy) backup operations, with support for encryption,
cloud storage, incremental backups, and integrity verification.
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

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
        backup_kind: 'full' or 'incremental'
        parent_backup_id: FK to parent full backup for incremental backups
        checksum: SHA-256 hex digest of backup file
        integrity_verified_at: Last successful integrity check timestamp
        is_encrypted: Whether backup file is AES-256-GCM encrypted
        encryption_salt: 16-byte hex-encoded salt for Argon2id key derivation
        encryption_nonce: 12-byte hex-encoded GCM nonce
        cloud_provider_id: FK to cloud storage provider
        cloud_path: Remote path/key in cloud bucket
        cloud_uploaded_at: When cloud upload completed
        tags: Admin-assigned labels as JSON array
        delta_payload: For incremental backups, the diff payload as JSON
    """

    __tablename__ = "backups"

    id = Column(String(36), primary_key=True)
    backup_type = Column(String(50), nullable=False)
    filename = Column(String(255), nullable=False)
    storage_path = Column(Text, nullable=False)
    size_bytes = Column(BigInteger)
    prompt_count = Column(Integer)
    created_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    succeeded = Column(Boolean, default=True)
    backup_metadata = Column(JSON)

    backup_kind = Column(String(20), nullable=False, default="full")
    parent_backup_id = Column(String(36), ForeignKey("backups.id"), nullable=True)
    checksum = Column(String(64), nullable=True)
    integrity_verified_at = Column(DateTime(timezone=True), nullable=True)
    is_encrypted = Column(Boolean, nullable=False, default=False)
    encryption_salt = Column(String(32), nullable=True)
    encryption_nonce = Column(String(24), nullable=True)
    cloud_provider_id = Column(
        String(36), ForeignKey("backup_storage_providers.id"), nullable=True
    )
    cloud_path = Column(Text, nullable=True)
    cloud_uploaded_at = Column(DateTime(timezone=True), nullable=True)
    tags = Column(JSON, nullable=True, default=list)
    delta_payload = Column(JSON, nullable=True)

    parent_backup = relationship("Backup", remote_side=[id], backref="child_backups")
    storage_provider = relationship(
        "BackupStorageProvider",
        back_populates="backups",
        foreign_keys=[cloud_provider_id],
    )

    def __repr__(self):
        return f"<Backup(id='{self.id[:8]}...', type='{self.backup_type}', filename='{self.filename}')>"
