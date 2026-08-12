# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Persistence for backup metadata: the `Backup` DB row and its on-disk
JSON sidecar file (used as a fallback when the DB record is unavailable).
"""

import json
import os
import re
from typing import Any

from src.db.models import Backup
from src.db.session import get_db_session
from src.services.exceptions import BackupError
from src.services.logging_service import logging_service

logger = logging_service.get_logger(__name__)

_BACKUP_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class BackupMetadataStore:
    """Reads and writes backup metadata to the DB and to JSON sidecar files."""

    def __init__(self, backups_dir: str):
        self.backups_dir = backups_dir

    def validate_backup_id(self, backup_id: str) -> None:
        """Reject backup_id values that could cause path traversal."""
        if not _BACKUP_ID_RE.match(backup_id):
            raise BackupError(
                "Invalid backup ID",
                context={"backup_id": backup_id},
                http_status=400,
            )

    def metadata_file_path(self, backup_id: str) -> str:
        """Return on-disk path for backup metadata file."""
        filename = f"{backup_id}_metadata.json"
        resolved = os.path.realpath(os.path.join(self.backups_dir, filename))
        backups_dir_real = os.path.realpath(self.backups_dir)
        if not resolved.startswith(backups_dir_real + os.sep):
            raise BackupError(
                "Invalid backup ID",
                context={"backup_id": backup_id},
                http_status=400,
            )
        return resolved

    def write_metadata_file(self, metadata: dict[str, Any]) -> None:
        """Persist metadata alongside backup for DB-restore resilience."""
        try:
            path = self.metadata_file_path(metadata["backup_id"])
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(metadata, handle, indent=2)
        except Exception as exc:
            logger.warning(
                "Failed to persist backup metadata file",
                extra={
                    "event": "backup.metadata_file.warning",
                    "resource_id": metadata.get("backup_id"),
                },
                exc_info=exc,
            )

    def load_metadata_from_file(self, backup_id: str) -> dict[str, Any] | None:
        """Load metadata from disk if the database record is unavailable."""
        path = self.metadata_file_path(backup_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            logger.warning(
                "Failed to read backup metadata file",
                extra={
                    "event": "backup.metadata_file.read_failure",
                    "resource_id": backup_id,
                },
                exc_info=exc,
            )
            return None

    def load_all_metadata_files(self) -> dict[str, dict[str, Any]]:
        """Return metadata for all backups stored on disk."""
        found: dict[str, dict[str, Any]] = {}
        try:
            for filename in os.listdir(self.backups_dir):
                if not filename.endswith("_metadata.json"):
                    continue
                path = os.path.join(self.backups_dir, filename)
                try:
                    with open(path, encoding="utf-8") as handle:
                        data = json.load(handle)
                        backup_id = data.get("backup_id")
                        if backup_id:
                            found[backup_id] = data
                except Exception as exc:
                    logger.warning(
                        "Failed to parse backup metadata file",
                        extra={
                            "event": "backup.metadata_file.parse_failure",
                            "resource_id": filename,
                        },
                        exc_info=exc,
                    )
        except FileNotFoundError:
            return found
        return found

    def ensure_metadata_file(self, metadata: dict[str, Any]) -> None:
        """Ensure a metadata JSON file exists for the given backup."""
        path = self.metadata_file_path(metadata["backup_id"])
        if not os.path.exists(path):
            self.write_metadata_file(metadata)

    def remove_metadata_file(self, backup_id: str) -> None:
        """Delete metadata JSON file if present."""
        path = self.metadata_file_path(backup_id)
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as exc:
            logger.warning(
                "Failed to remove backup metadata file",
                extra={
                    "event": "backup.metadata_file.remove_failure",
                    "resource_id": backup_id,
                },
                exc_info=exc,
            )

    def save_metadata_to_db(
        self,
        backup_id: str,
        metadata: dict[str, Any],
        is_encrypted: bool = False,
        encryption_salt: str | None = None,
        encryption_nonce: str | None = None,
        backup_kind: str = "full",
    ) -> None:
        """Save backup metadata to database."""
        try:
            with get_db_session() as session:
                backup = Backup(
                    id=backup_id,
                    backup_type=metadata["backup_type"],
                    backup_kind=backup_kind,
                    filename=metadata["filename"],
                    storage_path=metadata["storage_path"],
                    size_bytes=metadata.get("size_bytes"),
                    prompt_count=metadata.get("prompt_count"),
                    created_by=metadata.get("created_by"),
                    backup_metadata=metadata,
                    is_encrypted=is_encrypted,
                    encryption_salt=encryption_salt,
                    encryption_nonce=encryption_nonce,
                )
                session.add(backup)
                session.flush()

        except Exception as exc:
            logger.error(
                "Failed to save backup metadata",
                extra={"event": "backup.metadata.failure", "backup_id": backup_id},
                exc_info=exc,
            )
            raise

    def update_backup_record(self, backup_id: str, metadata: dict[str, Any]) -> None:
        """Update an existing backup record with refreshed metadata."""
        try:
            with get_db_session() as session:
                backup = session.query(Backup).filter_by(id=backup_id).first()
                if not backup:
                    return

                backup.filename = metadata.get("filename", backup.filename)
                backup.storage_path = metadata.get("storage_path", backup.storage_path)
                if "size_bytes" in metadata:
                    backup.size_bytes = metadata["size_bytes"]
                if "backup_type" in metadata:
                    backup.backup_type = metadata["backup_type"]
                backup.backup_metadata = metadata
                session.flush()

        except Exception as exc:
            logger.warning(
                "Failed to update backup record",
                extra={
                    "event": "backup.metadata.update_failure",
                    "backup_id": backup_id,
                },
                exc_info=exc,
            )

    def update_backup_encryption(
        self, backup_id: str, encryption_salt: str, encryption_nonce: str
    ) -> None:
        """Persist encryption salt/nonce to an existing backup record.

        Raises so the caller can handle DB inconsistency (file already encrypted
        but DB record would be left with is_encrypted=False if this is swallowed).
        """
        with get_db_session() as session:
            backup = session.query(Backup).filter_by(id=backup_id).first()
            if not backup:
                raise BackupError(
                    "Backup record not found while persisting encryption state; "
                    "file on disk is encrypted but DB metadata was not updated.",
                    context={"backup_id": backup_id},
                )
            backup.is_encrypted = True
            backup.encryption_salt = encryption_salt
            backup.encryption_nonce = encryption_nonce

    def get_backup_info(self, backup_id: str) -> dict[str, Any] | None:
        """Get detailed information about a specific backup."""
        self.validate_backup_id(backup_id)
        try:
            with get_db_session() as session:
                backup = session.query(Backup).filter_by(id=backup_id).first()

                if backup:
                    metadata = backup.backup_metadata or {}
                    timestamp = metadata.get("timestamp")
                    if not timestamp and backup.created_at:
                        timestamp = backup.created_at.isoformat() + "Z"
                    info = {
                        "backup_id": backup.id,
                        "backup_type": backup.backup_type,
                        "backup_kind": backup.backup_kind or "full",
                        "filename": backup.filename,
                        "storage_path": backup.storage_path,
                        "timestamp": timestamp,
                        "size_bytes": metadata.get(
                            "size_bytes", backup.size_bytes or 0
                        ),
                        "prompt_count": metadata.get("prompt_count", 0),
                        "database_type": metadata.get("database_type", "unknown"),
                        "created_by": metadata.get("created_by", "unknown"),
                        "compressed": metadata.get("compressed", False),
                        "is_encrypted": backup.is_encrypted or False,
                        "encryption_salt": backup.encryption_salt,
                        "encryption_nonce": backup.encryption_nonce,
                        "cloud_provider_id": backup.cloud_provider_id,
                        "cloud_path": backup.cloud_path,
                        "cloud_uploaded_at": (
                            backup.cloud_uploaded_at.isoformat()
                            if backup.cloud_uploaded_at
                            else None
                        ),
                    }
                    self.ensure_metadata_file(info)
                    return info

        except Exception as exc:
            logger.error(
                "Failed to get backup info",
                extra={"event": "backup.info.failure", "resource_id": backup_id},
                exc_info=exc,
            )

        # Fallback to metadata file
        return self.load_metadata_from_file(backup_id)

    def list_backups(self) -> list:
        """Get list of available backups from database, merged with any
        on-disk-only metadata files."""
        try:
            result: list = []
            seen_ids = set()

            with get_db_session() as session:
                backups = session.query(Backup).order_by(Backup.created_at.desc()).all()

                for backup in backups:
                    metadata = backup.backup_metadata or {}
                    timestamp = metadata.get("timestamp")
                    if not timestamp and backup.created_at:
                        timestamp = backup.created_at.isoformat() + "Z"

                    serialized = {
                        "backup_id": backup.id,
                        "backup_type": backup.backup_type,
                        "backup_kind": backup.backup_kind or "full",
                        "filename": backup.filename,
                        "storage_path": backup.storage_path,
                        "timestamp": timestamp,
                        "size_bytes": metadata.get(
                            "size_bytes", backup.size_bytes or 0
                        ),
                        "prompt_count": metadata.get("prompt_count", 0),
                        "database_type": metadata.get("database_type", "unknown"),
                        "created_by": metadata.get("created_by", "unknown"),
                        "compressed": metadata.get("compressed", False),
                        "tags": backup.tags or [],
                        "cloud_provider_id": backup.cloud_provider_id,
                        "cloud_path": backup.cloud_path,
                        "cloud_uploaded_at": (
                            backup.cloud_uploaded_at.isoformat()
                            if backup.cloud_uploaded_at
                            else None
                        ),
                        "is_encrypted": backup.is_encrypted or False,
                    }
                    result.append(serialized)
                    seen_ids.add(backup.id)
                    self.ensure_metadata_file(serialized)

            file_metadata = self.load_all_metadata_files()
            for backup_id, metadata in file_metadata.items():
                if backup_id not in seen_ids:
                    result.append(metadata)

            result.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
            return result

        except Exception as exc:
            logger.error(
                "Failed to list backups",
                extra={"event": "backup.list.failure"},
                exc_info=exc,
            )
            raise BackupError(
                "Unable to list backups.", context={"backups_dir": self.backups_dir}
            ) from exc

    def delete_backup(self, backup_id: str, get_current_user) -> bool:
        """Delete a backup and its files."""
        self.validate_backup_id(backup_id)
        try:
            with get_db_session() as session:
                backup = session.query(Backup).filter_by(id=backup_id).first()
                metadata = None

                if backup:
                    metadata = backup.backup_metadata or {}
                    storage_path = backup.storage_path
                else:
                    metadata = self.load_metadata_from_file(backup_id)
                    storage_path = metadata.get("storage_path") if metadata else None

                if not backup and not metadata:
                    return False

                if storage_path and os.path.exists(storage_path):
                    os.remove(storage_path)

                if backup:
                    from src.db.models.backup_audit_log import AuditLogEntry

                    session.query(AuditLogEntry).filter_by(backup_id=backup_id).update(
                        {"backup_id": None}
                    )
                    session.delete(backup)
                    session.flush()

                self.remove_metadata_file(backup_id)

                logging_service.log_audit_event(
                    action="backup.delete",
                    resource_type="backup",
                    resource_id=backup_id,
                )

                from src.services.backup_audit_service import BackupAuditService

                BackupAuditService().log(
                    operation="backup.delete",
                    outcome="success",
                    performed_by=get_current_user(),
                    detail={"backup_id": backup_id},
                )

                return True

        except Exception as exc:
            logger.error(
                "Failed to delete backup",
                extra={"event": "backup.delete.failure", "resource_id": backup_id},
                exc_info=exc,
            )
            from src.services.backup_audit_service import BackupAuditService

            BackupAuditService().log(
                operation="backup.delete",
                outcome="failure",
                performed_by=get_current_user(),
                detail={"backup_id": backup_id, "error": str(exc)},
            )
            raise BackupError(
                "Failed to delete backup.", context={"backup_id": backup_id}
            ) from exc
