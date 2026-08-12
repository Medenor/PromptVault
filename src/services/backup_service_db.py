# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Database-aware BackupService for PromptVault.

This is a thin facade over the backup subsystem, preserving the original
public API while delegating to focused collaborators:
- backup_creation_service.BackupCreationService: create_backup
- backup_restore_service.BackupRestoreService: restore_backup, selective_restore
- backup_diff_service.BackupDiffService: compute_restore_diff
- backup_dump_strategy: engine-specific dump/restore (SQLite VACUUM INTO /
  online backup API, PostgreSQL pg_dump/psql)
- backup_metadata_store.BackupMetadataStore: DB record + JSON sidecar
  metadata, list/get/delete

Key features:
- PostgreSQL backups using pg_dump
- SQLite backups using file copy
- Pre-restore automatic backups
- Backup metadata tracking in database
- Gzip compression support
"""

import getpass
import gzip
import os
import shutil
from datetime import UTC, datetime, timedelta
from typing import Any

from src.db.session import get_db_session
from src.services.backup_creation_service import BackupCreationService
from src.services.backup_diff_service import (
    BackupDiffService,
    extract_prompts_from_backup,
)
from src.services.backup_metadata_store import BackupMetadataStore
from src.services.backup_restore_service import BackupRestoreService
from src.services.exceptions import BackupError
from src.services.logging_service import logging_service

logger = logging_service.get_logger(__name__)


class BackupService:
    """Database-aware backup service for PromptVault.

    Supports both PostgreSQL and SQLite databases with appropriate
    backup strategies for each.
    """

    def __init__(self, data_dir: str | None = None):
        """Initialize the BackupService.

        Args:
            data_dir (str): Path to the data directory. If None, uses default location.
        """
        if data_dir is None:
            script_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            self.data_dir = os.path.join(script_dir, "data")
        else:
            self.data_dir = data_dir

        self.backups_dir = os.path.join(self.data_dir, "backups")
        os.makedirs(self.backups_dir, exist_ok=True)

        self._metadata_store = BackupMetadataStore(self.backups_dir)
        self._creation_service = BackupCreationService(
            self.backups_dir, self._metadata_store
        )
        self._restore_service = BackupRestoreService(
            self._metadata_store,
            self._ensure_local_backup_file,
            lambda *args, **kwargs: self.create_backup(*args, **kwargs),
        )
        self._diff_service = BackupDiffService(
            self._metadata_store, self._ensure_local_backup_file
        )

    # -- Creation ----------------------------------------------------------

    def create_backup(
        self,
        custom_name: str | None = None,
        created_by: str | None = None,
        encrypt: bool = False,
        passphrase: str | None = None,
        backup_kind: str = "full",
    ) -> str | None:
        """Create a backup of the database."""
        return self._creation_service.create_backup(
            custom_name,
            created_by,
            self._get_current_user,
            encrypt=encrypt,
            passphrase=passphrase,
            backup_kind=backup_kind,
        )

    # -- Restore -------------------------------------------------------------

    def restore_backup(
        self,
        backup_id: str,
        created_by: str | None = None,
        passphrase: str | None = None,
    ) -> bool:
        """Restore database from a backup.

        Creates a pre-restore backup automatically before restoring.
        """
        return self._restore_service.restore_backup(
            backup_id, created_by, self._get_current_user, passphrase=passphrase
        )

    def selective_restore(
        self,
        backup_id: str,
        prompt_ids: list,
        created_by: str | None = None,
        passphrase: str | None = None,
    ) -> dict[str, Any]:
        """Restore only specific prompts from a backup."""
        return self._restore_service.selective_restore(
            backup_id,
            prompt_ids,
            created_by,
            self._get_current_user,
            extract_prompts_from_backup,
            passphrase=passphrase,
        )

    # -- Diff / preview ------------------------------------------------------

    def compute_restore_diff(
        self, backup_id: str, passphrase: str | None = None
    ) -> dict[str, Any]:
        """Compute a diff of what would change if this backup were restored."""
        return self._diff_service.compute_restore_diff(backup_id, passphrase=passphrase)

    def _extract_prompts_from_backup(self, backup_path: str, backup_type: str) -> list:
        return extract_prompts_from_backup(backup_path, backup_type)

    # -- Listing / metadata ----------------------------------------------------

    def list_backups(self) -> list[dict[str, Any]]:
        """Get list of available backups from database."""
        return self._metadata_store.list_backups()

    def get_backup_info(self, backup_id: str) -> dict[str, Any] | None:
        """Get detailed information about a specific backup."""
        return self._metadata_store.get_backup_info(backup_id)

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup and its files."""
        return self._metadata_store.delete_backup(backup_id, self._get_current_user)

    def get_backup_stats(self) -> dict[str, Any]:
        """Get statistics about backups."""
        try:
            backups = self.list_backups()

            if not backups:
                return {
                    "total_backups": 0,
                    "total_size": 0,
                    "oldest_backup": None,
                    "newest_backup": None,
                    "compressed_count": 0,
                }

            total_size = sum(backup.get("size_bytes", 0) for backup in backups)
            compressed_count = sum(
                1 for backup in backups if backup.get("compressed", False)
            )

            return {
                "total_backups": len(backups),
                "total_size": total_size,
                "oldest_backup": backups[-1]["timestamp"] if backups else None,
                "newest_backup": backups[0]["timestamp"] if backups else None,
                "compressed_count": compressed_count,
            }

        except Exception as exc:
            logger.error(
                "Failed to get backup stats",
                extra={"event": "backup.stats.failure"},
                exc_info=exc,
            )
            return {
                "total_backups": 0,
                "total_size": 0,
                "oldest_backup": None,
                "newest_backup": None,
                "compressed_count": 0,
            }

    # -- Retention / compression -----------------------------------------------

    def cleanup_old_backups(self, retention_days: int = 30) -> int:
        """Remove old backups based on retention policy."""
        removed_count = 0

        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
            backups = self.list_backups()

            for backup in backups:
                backup_date = self._parse_backup_timestamp(backup["timestamp"])

                if backup_date < cutoff_date:
                    success = self.delete_backup(backup["backup_id"])
                    if success:
                        removed_count += 1
                        logger.info(
                            "Removed old backup during cleanup",
                            extra={
                                "event": "backup.cleanup.removal",
                                "resource_id": backup["backup_id"],
                            },
                        )

            if removed_count > 0:
                logger.info(
                    "Cleanup completed",
                    extra={
                        "event": "backup.cleanup.success",
                        "removed_count": removed_count,
                    },
                )
                logging_service.log_audit_event(
                    action="backup.cleanup",
                    resource_type="backup",
                    resource_id="multiple",
                    removed_count=removed_count,
                )

        except Exception as exc:
            logger.error(
                "Failed to cleanup old backups",
                extra={"event": "backup.cleanup.failure"},
                exc_info=exc,
            )
            raise BackupError(
                "Failed to cleanup old backups.",
                context={"retention_days": retention_days},
            ) from exc

        return removed_count

    def compress_old_backups(self, days_threshold: int = 7) -> int:
        """Compress backups older than the provided threshold."""
        compressed_count = 0

        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_threshold)
            backups = self.list_backups()

            for backup in backups:
                timestamp = backup.get("timestamp")
                if not timestamp:
                    continue

                backup_date = self._parse_backup_timestamp(timestamp)
                if days_threshold > 0 and backup_date >= cutoff_date:
                    continue

                filename = backup.get("filename")
                storage_path = backup.get("storage_path")
                if not storage_path or not os.path.exists(storage_path):
                    continue
                if filename and filename.endswith(".gz"):
                    continue

                compressed_path = f"{storage_path}.gz"
                try:
                    with open(storage_path, "rb") as src:
                        with gzip.open(compressed_path, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                    os.remove(storage_path)
                except Exception as exc:
                    logger.warning(
                        "Failed to compress backup file",
                        extra={
                            "event": "backup.compress.failure",
                            "resource_id": backup.get("backup_id"),
                        },
                        exc_info=exc,
                    )
                    continue

                backup["filename"] = os.path.basename(compressed_path)
                backup["storage_path"] = compressed_path
                backup["compressed"] = True
                backup["original_size"] = backup.get("size_bytes", 0)
                backup["compressed_size"] = os.path.getsize(compressed_path)
                backup["size_bytes"] = backup["compressed_size"]

                self._metadata_store.update_backup_record(backup["backup_id"], backup)
                self._metadata_store.write_metadata_file(backup)

                compressed_count += 1
                logger.info(
                    "Compressed backup file",
                    extra={
                        "event": "backup.compress.success",
                        "resource_id": backup["backup_id"],
                    },
                )
                logging_service.log_audit_event(
                    action="backup.compress",
                    resource_type="backup",
                    resource_id=backup["backup_id"],
                    compressed_size=backup["compressed_size"],
                )

        except Exception as exc:
            logger.error(
                "Failed to compress backups",
                extra={"event": "backup.compress.failure"},
                exc_info=exc,
            )
            raise BackupError(
                "Failed to compress backups.",
                context={"days_threshold": days_threshold},
            ) from exc

        return compressed_count

    # -- Cloud fallback --------------------------------------------------------

    def _ensure_local_backup_file(
        self, backup_id: str, metadata: dict[str, Any]
    ) -> str:
        """Ensure the backup file exists locally, downloading from cloud if needed.

        If the local storage_path is missing (e.g. removed by cleanup, or this
        backup was only ever uploaded from another machine), fall back to the
        cloud copy referenced by cloud_provider_id/cloud_path.
        """
        backup_path = metadata.get("storage_path")
        if backup_path and os.path.exists(backup_path):
            return backup_path

        cloud_provider_id = metadata.get("cloud_provider_id")
        cloud_path = metadata.get("cloud_path")
        if not cloud_provider_id or not cloud_path:
            raise BackupError(
                "Backup file not found",
                context={"backup_id": backup_id, "path": backup_path},
                http_status=404,
            )

        from src.db.models.backup_storage_provider import BackupStorageProvider
        from src.services.backup_cloud_service import BackupCloudService

        with get_db_session() as session:
            provider = (
                session.query(BackupStorageProvider)
                .filter_by(id=cloud_provider_id)
                .first()
            )
            if not provider or not provider.enabled:
                raise BackupError(
                    "Cloud storage provider not found or disabled",
                    context={"backup_id": backup_id, "provider_id": cloud_provider_id},
                    http_status=404,
                )

            dest_path = backup_path or os.path.join(
                self.backups_dir, metadata.get("filename", f"{backup_id}.db")
            )
            try:
                BackupCloudService().download(provider, cloud_path, dest_path)
            except Exception as exc:
                logger.error(
                    "Failed to download backup from cloud storage",
                    extra={
                        "event": "backup.restore.cloud_download_failure",
                        "backup_id": backup_id,
                        "provider_id": cloud_provider_id,
                    },
                    exc_info=exc,
                )
                raise BackupError(
                    "Failed to download backup from cloud storage.",
                    context={"backup_id": backup_id, "provider_id": cloud_provider_id},
                ) from exc

        logger.info(
            "Backup downloaded from cloud storage for restore",
            extra={
                "event": "backup.restore.cloud_download_success",
                "backup_id": backup_id,
            },
        )

        if not metadata.get("storage_path"):
            self._metadata_store.update_backup_record(
                backup_id, {**metadata, "storage_path": dest_path}
            )

        return dest_path

    # -- Helpers -----------------------------------------------------------

    def _get_current_user(self) -> str:
        """Get the current user."""
        try:
            return getpass.getuser()
        except Exception:
            return "unknown"

    @staticmethod
    def _parse_backup_timestamp(raw: str) -> datetime:
        """Return timezone-aware datetime for backup metadata."""
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    def _validate_backup_id(self, backup_id: str) -> None:
        """Reject backup_id values that could cause path traversal."""
        self._metadata_store.validate_backup_id(backup_id)

    def _sanitize_backup_name(self, name: str) -> str:
        """Sanitize custom backup names for safe filenames."""
        return self._creation_service._sanitize_backup_name(name)

    def _metadata_file_path(self, backup_id: str) -> str:
        """Return on-disk path for backup metadata file."""
        return self._metadata_store.metadata_file_path(backup_id)

    def _write_metadata_file(self, metadata: dict[str, Any]) -> None:
        """Persist metadata alongside backup for DB-restore resilience."""
        self._metadata_store.write_metadata_file(metadata)

    def _load_metadata_from_file(self, backup_id: str) -> dict[str, Any] | None:
        """Load metadata from disk if the database record is unavailable."""
        return self._metadata_store.load_metadata_from_file(backup_id)

    def _load_all_metadata_files(self) -> dict[str, dict[str, Any]]:
        """Return metadata for all backups stored on disk."""
        return self._metadata_store.load_all_metadata_files()

    def _ensure_metadata_file(self, metadata: dict[str, Any]) -> None:
        """Ensure a metadata JSON file exists for the given backup."""
        self._metadata_store.ensure_metadata_file(metadata)

    def _remove_metadata_file(self, backup_id: str) -> None:
        """Delete metadata JSON file if present."""
        self._metadata_store.remove_metadata_file(backup_id)

    def _update_backup_record(self, backup_id: str, metadata: dict[str, Any]) -> None:
        """Update an existing backup record with refreshed metadata."""
        self._metadata_store.update_backup_record(backup_id, metadata)

    def _get_prompt_count(self) -> int:
        """Return the current count of prompts for backup metadata."""
        return self._creation_service._get_prompt_count()
