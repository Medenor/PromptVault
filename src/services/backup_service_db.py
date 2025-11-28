"""Database-aware BackupService for PromptVault.

This service handles backup and restoration of database data, supporting both
PostgreSQL (using pg_dump) and SQLite (using file copy).

Key features:
- PostgreSQL backups using pg_dump
- SQLite backups using file copy
- Pre-restore automatic backups
- Backup metadata tracking in database
- Gzip compression support
"""

import os
import shutil
import gzip
import subprocess
import re
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path
import getpass

from src.db.config import db_settings
from src.db.session import get_db_session
from src.db.models import Backup
from src.services.exceptions import BackupError
from src.services.logging_service import logging_service


logger = logging_service.get_logger(__name__)


class BackupService:
    """Database-aware backup service for PromptVault.

    Supports both PostgreSQL and SQLite databases with appropriate
    backup strategies for each.
    """

    def __init__(self, data_dir: str = None):
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

        # Ensure backups directory exists
        os.makedirs(self.backups_dir, exist_ok=True)

    def create_backup(self, custom_name: Optional[str] = None) -> Optional[str]:
        """Create a backup of the database.

        Args:
            custom_name (str): Optional custom name for the backup

        Returns:
            Optional[str]: Backup ID if successful, None otherwise
        """
        try:
            # Generate backup ID
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            if custom_name:
                safe_suffix = self._sanitize_backup_name(custom_name)
                backup_id = f"backup_{safe_suffix}" if safe_suffix else f"backup_{timestamp}"
            else:
                backup_id = f"backup_{timestamp}"

            # Create backup based on database type
            if db_settings.is_sqlite:
                return self._create_sqlite_backup(backup_id)
            elif db_settings.is_postgresql:
                return self._create_pg_backup(backup_id)
            else:
                raise BackupError(
                    "Unsupported database type",
                    context={"database_url": db_settings.DATABASE_URL}
                )

        except BackupError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to create backup",
                extra={"event": "backup.create.failure"},
                exc_info=exc
            )
            raise BackupError(
                "Failed to create backup.",
                context={}
            ) from exc

    def _create_sqlite_backup(self, backup_id: str) -> str:
        """Create SQLite backup using file copy.

        Args:
            backup_id: Backup identifier

        Returns:
            str: Backup ID
        """
        try:
            # Extract database path from DATABASE_URL
            db_url = db_settings.DATABASE_URL
            if db_url.startswith("sqlite:///"):
                db_path = db_url.replace("sqlite:///", "")
            else:
                raise BackupError(
                    "Invalid SQLite DATABASE_URL format",
                    context={"database_url": db_url}
                )

            # Resolve relative paths
            if not os.path.isabs(db_path):
                script_dir = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                db_path = os.path.join(script_dir, db_path)

            # Check if database exists
            if not os.path.exists(db_path):
                raise BackupError(
                    "Database file does not exist",
                    context={"db_path": db_path},
                    http_status=404
                )

            # Create backup file path
            backup_filename = f"{backup_id}.db"
            backup_path = os.path.join(self.backups_dir, backup_filename)

            # Copy database file
            shutil.copy2(db_path, backup_path)

            # Get backup metadata
            backup_size = os.path.getsize(backup_path)

            # Save metadata to database
            timestamp = datetime.now(timezone.utc).isoformat()
            metadata = {
                "backup_id": backup_id,
                "backup_type": "sqlite_copy",
                "filename": backup_filename,
                "storage_path": backup_path,
                "size_bytes": backup_size,
                "database_type": "sqlite",
                "created_by": self._get_current_user(),
                "compressed": False,
                "timestamp": timestamp,
            }

            self._save_metadata_to_db(backup_id, metadata)
            self._write_metadata_file(metadata)

            logger.info(
                "SQLite backup created successfully",
                extra={
                    "event": "backup.create.success",
                    "resource_id": backup_id,
                    "backup_type": "sqlite_copy"
                }
            )

            logging_service.log_audit_event(
                action="backup.create",
                resource_type="backup",
                resource_id=backup_id,
                backup_type="sqlite_copy",
                size_bytes=backup_size,
            )

            return backup_id

        except Exception as exc:
            logger.error(
                "Failed to create SQLite backup",
                extra={"event": "backup.create.failure", "backup_id": backup_id},
                exc_info=exc
            )
            raise BackupError(
                "Failed to create SQLite backup.",
                context={"backup_id": backup_id}
            ) from exc

    def _create_pg_backup(self, backup_id: str) -> str:
        """Create PostgreSQL backup using pg_dump.

        Args:
            backup_id: Backup identifier

        Returns:
            str: Backup ID
        """
        try:
            # Create backup file path
            backup_filename = f"{backup_id}.sql"
            backup_path = os.path.join(self.backups_dir, backup_filename)

            # Build pg_dump command
            # Use DATABASE_URL directly as connection string
            db_url = db_settings.DATABASE_URL

            cmd = [
                "pg_dump",
                "--file", backup_path,
                "--format=plain",
                "--clean",
                "--if-exists",
                db_url
            ]

            # Execute pg_dump
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            # Get backup metadata
            backup_size = os.path.getsize(backup_path)

            # Save metadata to database
            timestamp = datetime.now(timezone.utc).isoformat()
            metadata = {
                "backup_id": backup_id,
                "backup_type": "pg_dump",
                "filename": backup_filename,
                "storage_path": backup_path,
                "size_bytes": backup_size,
                "database_type": "postgresql",
                "created_by": self._get_current_user(),
                "compressed": False,
                "timestamp": timestamp,
            }

            self._save_metadata_to_db(backup_id, metadata)
            self._write_metadata_file(metadata)

            logger.info(
                "PostgreSQL backup created successfully",
                extra={
                    "event": "backup.create.success",
                    "resource_id": backup_id,
                    "backup_type": "pg_dump"
                }
            )

            logging_service.log_audit_event(
                action="backup.create",
                resource_type="backup",
                resource_id=backup_id,
                backup_type="pg_dump",
                size_bytes=backup_size,
            )

            return backup_id

        except subprocess.CalledProcessError as exc:
            error_msg = exc.stderr if exc.stderr else str(exc)
            logger.error(
                "pg_dump failed",
                extra={
                    "event": "backup.create.failure",
                    "backup_id": backup_id,
                    "error": error_msg
                },
                exc_info=exc
            )
            raise BackupError(
                f"pg_dump failed: {error_msg}",
                context={"backup_id": backup_id}
            ) from exc
        except Exception as exc:
            logger.error(
                "Failed to create PostgreSQL backup",
                extra={"event": "backup.create.failure", "backup_id": backup_id},
                exc_info=exc
            )
            raise BackupError(
                "Failed to create PostgreSQL backup.",
                context={"backup_id": backup_id}
            ) from exc

    def restore_backup(self, backup_id: str) -> bool:
        """Restore database from a backup.

        Creates a pre-restore backup automatically before restoring.

        Args:
            backup_id (str): ID of the backup to restore

        Returns:
            bool: True if successful

        Raises:
            BackupError: If backup not found or restore fails
        """
        try:
            # Get backup metadata
            metadata = self.get_backup_info(backup_id)
            if not metadata:
                raise BackupError(
                    "Backup not found",
                    context={"backup_id": backup_id},
                    http_status=404
                )

            backup_type = metadata.get("backup_type")

            # Verify backup file exists
            backup_path = metadata.get("storage_path")
            if not os.path.exists(backup_path):
                raise BackupError(
                    "Backup file does not exist",
                    context={"backup_id": backup_id, "path": backup_path},
                    http_status=404
                )

            # Create pre-restore backup with unique timestamp
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            logger.info(
                "Creating pre-restore backup",
                extra={"event": "backup.restore.pre_backup"}
            )
            pre_restore_backup = self.create_backup(f"pre_restore_{timestamp}")
            if not pre_restore_backup:
                logger.warning(
                    "Could not create pre-restore backup",
                    extra={"event": "backup.restore.warning"}
                )

            # Restore based on backup type
            if backup_type == "pg_dump":
                success = self._restore_pg_backup(backup_id, backup_path)
            elif backup_type == "sqlite_copy":
                success = self._restore_sqlite_backup(backup_id, backup_path)
            else:
                raise BackupError(
                    f"Unsupported backup type: {backup_type}",
                    context={"backup_id": backup_id, "backup_type": backup_type}
                )

            if success:
                logger.info(
                    "Backup restored successfully",
                    extra={
                        "event": "backup.restore.success",
                        "resource_id": backup_id
                    }
                )
                logging_service.log_audit_event(
                    action="backup.restore",
                    resource_type="backup",
                    resource_id=backup_id,
                )

            return success

        except BackupError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to restore backup",
                extra={
                    "event": "backup.restore.failure",
                    "resource_id": backup_id
                },
                exc_info=exc
            )
            raise BackupError(
                "Failed to restore backup.",
                context={"backup_id": backup_id}
            ) from exc

    def _restore_sqlite_backup(self, backup_id: str, backup_path: str) -> bool:
        """Restore SQLite database from backup file.

        Args:
            backup_id: Backup identifier
            backup_path: Path to backup file

        Returns:
            bool: True if successful
        """
        try:
            # Extract database path from DATABASE_URL
            db_url = db_settings.DATABASE_URL
            if db_url.startswith("sqlite:///"):
                db_path = db_url.replace("sqlite:///", "")
            else:
                raise BackupError(
                    "Invalid SQLite DATABASE_URL format",
                    context={"database_url": db_url}
                )

            # Resolve relative paths
            if not os.path.isabs(db_path):
                script_dir = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                db_path = os.path.join(script_dir, db_path)

            # Copy backup to database location
            shutil.copy2(backup_path, db_path)

            logger.info(
                "SQLite database restored from backup",
                extra={
                    "event": "backup.restore.success",
                    "backup_id": backup_id
                }
            )

            return True

        except Exception as exc:
            logger.error(
                "Failed to restore SQLite backup",
                extra={
                    "event": "backup.restore.failure",
                    "backup_id": backup_id
                },
                exc_info=exc
            )
            raise BackupError(
                "Failed to restore SQLite backup.",
                context={"backup_id": backup_id}
            ) from exc

    def _restore_pg_backup(self, backup_id: str, backup_path: str) -> bool:
        """Restore PostgreSQL database from pg_dump file.

        Args:
            backup_id: Backup identifier
            backup_path: Path to SQL dump file

        Returns:
            bool: True if successful
        """
        try:
            # Build psql command to restore
            db_url = db_settings.DATABASE_URL

            cmd = [
                "psql",
                "--file", backup_path,
                db_url
            ]

            # Execute psql
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            logger.info(
                "PostgreSQL database restored from backup",
                extra={
                    "event": "backup.restore.success",
                    "backup_id": backup_id
                }
            )

            return True

        except subprocess.CalledProcessError as exc:
            error_msg = exc.stderr if exc.stderr else str(exc)
            logger.error(
                "psql restore failed",
                extra={
                    "event": "backup.restore.failure",
                    "backup_id": backup_id,
                    "error": error_msg
                },
                exc_info=exc
            )
            raise BackupError(
                f"psql restore failed: {error_msg}",
                context={"backup_id": backup_id}
            ) from exc
        except Exception as exc:
            logger.error(
                "Failed to restore PostgreSQL backup",
                extra={
                    "event": "backup.restore.failure",
                    "backup_id": backup_id
                },
                exc_info=exc
            )
            raise BackupError(
                "Failed to restore PostgreSQL backup.",
                context={"backup_id": backup_id}
            ) from exc

    def list_backups(self) -> List[Dict[str, Any]]:
        """Get list of available backups from database.

        Returns:
            List[Dict[str, Any]]: List of backup metadata, sorted by timestamp (newest first)
        """
        try:
            result: List[Dict[str, Any]] = []
            seen_ids = set()

            with get_db_session() as session:
                backups = (
                    session.query(Backup)
                    .order_by(Backup.created_at.desc())
                    .all()
                )

                for backup in backups:
                    metadata = backup.backup_metadata or {}
                    timestamp = metadata.get("timestamp")
                    if not timestamp and backup.created_at:
                        timestamp = backup.created_at.isoformat() + "Z"

                    serialized = {
                        "backup_id": backup.id,
                        "backup_type": backup.backup_type,
                        "filename": backup.filename,
                        "storage_path": backup.storage_path,
                        "timestamp": timestamp,
                        "size_bytes": metadata.get("size_bytes", backup.size_bytes or 0),
                        "database_type": metadata.get("database_type", "unknown"),
                        "created_by": metadata.get("created_by", "unknown"),
                        "compressed": metadata.get("compressed", False),
                    }
                    result.append(serialized)
                    seen_ids.add(backup.id)
                    self._ensure_metadata_file(serialized)

            file_metadata = self._load_all_metadata_files()
            for backup_id, metadata in file_metadata.items():
                if backup_id not in seen_ids:
                    result.append(metadata)

            result.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
            return result

        except Exception as exc:
            logger.error(
                "Failed to list backups",
                extra={"event": "backup.list.failure"},
                exc_info=exc
            )
            raise BackupError(
                "Unable to list backups.",
                context={"backups_dir": self.backups_dir}
            ) from exc

    def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific backup.

        Args:
            backup_id (str): ID of the backup

        Returns:
            Optional[Dict[str, Any]]: Backup metadata if found, None otherwise
        """
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
                        "filename": backup.filename,
                        "storage_path": backup.storage_path,
                        "timestamp": timestamp,
                        "size_bytes": metadata.get("size_bytes", backup.size_bytes or 0),
                        "database_type": metadata.get("database_type", "unknown"),
                        "created_by": metadata.get("created_by", "unknown"),
                        "compressed": metadata.get("compressed", False),
                    }
                    self._ensure_metadata_file(info)
                    return info

        except Exception as exc:
            logger.error(
                "Failed to get backup info",
                extra={"event": "backup.info.failure", "resource_id": backup_id},
                exc_info=exc
            )

        # Fallback to metadata file
        return self._load_metadata_from_file(backup_id)

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup and its files.

        Args:
            backup_id (str): Backup ID to delete

        Returns:
            bool: True if successful
        """
        try:
            with get_db_session() as session:
                backup = session.query(Backup).filter_by(id=backup_id).first()
                metadata = None

                if backup:
                    metadata = backup.backup_metadata or {}
                    storage_path = backup.storage_path
                else:
                    metadata = self._load_metadata_from_file(backup_id)
                    storage_path = metadata.get("storage_path") if metadata else None

                if not backup and not metadata:
                    return False

                if storage_path and os.path.exists(storage_path):
                    os.remove(storage_path)

                if backup:
                    session.delete(backup)
                    session.flush()

                self._remove_metadata_file(backup_id)

                logging_service.log_audit_event(
                    action="backup.delete",
                    resource_type="backup",
                    resource_id=backup_id,
                )

                return True

        except Exception as exc:
            logger.error(
                "Failed to delete backup",
                extra={"event": "backup.delete.failure", "resource_id": backup_id},
                exc_info=exc
            )
            raise BackupError(
                "Failed to delete backup.",
                context={"backup_id": backup_id}
            ) from exc

    def get_backup_stats(self) -> Dict[str, Any]:
        """Get statistics about backups.

        Returns:
            Dict[str, Any]: Backup statistics
        """
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
                exc_info=exc
            )
            return {
                "total_backups": 0,
                "total_size": 0,
                "oldest_backup": None,
                "newest_backup": None,
                "compressed_count": 0,
            }

    def cleanup_old_backups(self, retention_days: int = 30) -> int:
        """Remove old backups based on retention policy.

        Args:
            retention_days (int): Number of days to keep backups

        Returns:
            int: Number of backups removed
        """
        removed_count = 0

        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            backups = self.list_backups()

            for backup in backups:
                # Parse backup timestamp
                backup_date = self._parse_backup_timestamp(backup["timestamp"])

                if backup_date < cutoff_date:
                    # Delete the backup
                    success = self.delete_backup(backup["backup_id"])
                    if success:
                        removed_count += 1
                        logger.info(
                            "Removed old backup during cleanup",
                            extra={
                                "event": "backup.cleanup.removal",
                                "resource_id": backup["backup_id"]
                            }
                        )

            if removed_count > 0:
                logger.info(
                    "Cleanup completed",
                    extra={
                        "event": "backup.cleanup.success",
                        "removed_count": removed_count
                    }
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
                exc_info=exc
            )
            raise BackupError(
                "Failed to cleanup old backups.",
                context={"retention_days": retention_days}
            ) from exc

        return removed_count

    def compress_old_backups(self, days_threshold: int = 7) -> int:
        """Compress backups older than the provided threshold."""
        compressed_count = 0

        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
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

                self._update_backup_record(backup["backup_id"], backup)
                self._write_metadata_file(backup)

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
                context={"days_threshold": days_threshold}
            ) from exc

        return compressed_count

    def _save_metadata_to_db(self, backup_id: str, metadata: Dict[str, Any]) -> None:
        """Save backup metadata to database.

        Args:
            backup_id: Backup identifier
            metadata: Backup metadata dictionary
        """
        try:
            with get_db_session() as session:
                backup = Backup(
                    id=backup_id,
                    backup_type=metadata["backup_type"],
                    filename=metadata["filename"],
                    storage_path=metadata["storage_path"],
                    backup_metadata=metadata,
                )
                session.add(backup)
                session.flush()

        except Exception as exc:
            logger.error(
                "Failed to save backup metadata",
                extra={"event": "backup.metadata.failure", "backup_id": backup_id},
                exc_info=exc
            )
            raise

    def _update_backup_record(self, backup_id: str, metadata: Dict[str, Any]) -> None:
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
                extra={"event": "backup.metadata.update_failure", "backup_id": backup_id},
                exc_info=exc,
            )

    def _metadata_file_path(self, backup_id: str) -> str:
        """Return on-disk path for backup metadata file."""
        filename = f"{backup_id}_metadata.json"
        return os.path.join(self.backups_dir, filename)

    def _write_metadata_file(self, metadata: Dict[str, Any]) -> None:
        """Persist metadata alongside backup for DB-restore resilience."""
        try:
            path = self._metadata_file_path(metadata["backup_id"])
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(metadata, handle, indent=2)
        except Exception as exc:
            logger.warning(
                "Failed to persist backup metadata file",
                extra={"event": "backup.metadata_file.warning", "resource_id": metadata.get("backup_id")},
                exc_info=exc,
            )

    def _load_metadata_from_file(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Load metadata from disk if the database record is unavailable."""
        path = self._metadata_file_path(backup_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                return data
        except Exception as exc:
            logger.warning(
                "Failed to read backup metadata file",
                extra={"event": "backup.metadata_file.read_failure", "resource_id": backup_id},
                exc_info=exc,
            )
            return None

    def _load_all_metadata_files(self) -> Dict[str, Dict[str, Any]]:
        """Return metadata for all backups stored on disk."""
        found: Dict[str, Dict[str, Any]] = {}
        try:
            for filename in os.listdir(self.backups_dir):
                if not filename.endswith("_metadata.json"):
                    continue
                path = os.path.join(self.backups_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as handle:
                        data = json.load(handle)
                        backup_id = data.get("backup_id")
                        if backup_id:
                            found[backup_id] = data
                except Exception as exc:
                    logger.warning(
                        "Failed to parse backup metadata file",
                        extra={"event": "backup.metadata_file.parse_failure", "resource_id": filename},
                        exc_info=exc,
                    )
        except FileNotFoundError:
            return found
        return found

    def _ensure_metadata_file(self, metadata: Dict[str, Any]) -> None:
        """Ensure a metadata JSON file exists for the given backup."""
        path = self._metadata_file_path(metadata["backup_id"])
        if not os.path.exists(path):
            self._write_metadata_file(metadata)

    def _remove_metadata_file(self, backup_id: str) -> None:
        """Delete metadata JSON file if present."""
        path = self._metadata_file_path(backup_id)
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as exc:
            logger.warning(
                "Failed to remove backup metadata file",
                extra={"event": "backup.metadata_file.remove_failure", "resource_id": backup_id},
                exc_info=exc,
            )

    def _get_current_user(self) -> str:
        """Get the current user.

        Returns:
            str: Current user name
        """
        try:
            return getpass.getuser()
        except Exception:
            return "unknown"

    def _sanitize_backup_name(self, name: str) -> str:
        """Sanitize custom backup names for safe filenames."""
        if not name:
            return ""
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip())
        return cleaned[:64]

    @staticmethod
    def _parse_backup_timestamp(raw: str) -> datetime:
        """Return timezone-aware datetime for backup metadata."""
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
