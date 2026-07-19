# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import os
import re
import shutil
import gzip
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
import getpass

from src.services.exceptions import BackupError
from src.services.logging_service import logging_service

logger = logging_service.get_logger(__name__)


class BackupService:
    """Service for handling prompt data backup and restoration operations."""

    def __init__(self, data_dir: str = None):
        """
        Initialize the BackupService.

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
        self.data_file = os.path.join(self.data_dir, "prompts_data.json")

        # Ensure backups directory exists
        os.makedirs(self.backups_dir, exist_ok=True)

    def create_backup(
        self, custom_name: str = None, created_by: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a timestamped backup of the current data.

        Args:
            custom_name (str): Optional custom name for the backup
            created_by (str): Optional username for audit metadata

        Returns:
            Optional[str]: Backup ID if successful, None otherwise
        """
        try:
            # Check if data file exists
            if not os.path.exists(self.data_file):
                context = {"data_file": self.data_file}
                logger.error(
                    "Backup creation failed because data file is missing",
                    extra={
                        "event": "backup.create.failure",
                        "resource_id": self.data_file,
                    },
                )
                raise BackupError(
                    "Data file does not exist.",
                    user_message="Cannot create backup because the data file is missing.",
                    context=context,
                    http_status=404,
                )

            # Generate backup filename
            if custom_name:
                safe_suffix = self._sanitize_backup_name(custom_name)
                if safe_suffix:
                    backup_filename = f"backup_{safe_suffix}.json"
                else:
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    backup_filename = f"backup_{timestamp}.json"
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                backup_filename = f"backup_{timestamp}.json"

            backup_path = os.path.join(self.backups_dir, backup_filename)

            # Copy the data file to backup location
            shutil.copy2(self.data_file, backup_path)

            # Get backup metadata
            backup_size = os.path.getsize(backup_path)

            # Load data to count prompts
            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                prompt_count = len(data.get("prompts", {}))

            # Create backup metadata
            backup_id = backup_filename.replace(".json", "")
            metadata = {
                "backup_id": backup_id,
                "filename": backup_filename,
                "timestamp": datetime.now().isoformat(),
                "size_bytes": backup_size,
                "prompt_count": prompt_count,
                "created_by": created_by or self._get_current_user(),
                "data_file_modified": datetime.fromtimestamp(
                    os.path.getmtime(self.data_file)
                ).isoformat(),
                "compressed": False,
            }

            # Save metadata
            metadata_path = backup_path.replace(".json", "_metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            logger.info(
                "Backup created successfully",
                extra={
                    "event": "backup.create.success",
                    "resource_id": backup_id,
                    "backup_id": backup_id,
                },
            )
            logging_service.log_audit_event(
                action="backup.create",
                resource_type="backup",
                resource_id=backup_id,
                size_bytes=backup_size,
                prompt_count=prompt_count,
            )
            return backup_id

        except Exception as exc:
            context = {"data_file": self.data_file}
            logger.error(
                "Failed to create backup",
                extra={"event": "backup.create.failure"},
                exc_info=exc,
            )
            raise BackupError(
                "Failed to create backup.",
                context=context,
            ) from exc

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Get list of available backups with metadata.

        Returns:
            List[Dict[str, Any]]: List of backup metadata, sorted by timestamp (newest first)
        """
        backups = []

        try:
            # Look for backup metadata files
            for filename in os.listdir(self.backups_dir):
                if filename.endswith("_metadata.json"):
                    metadata_path = os.path.join(self.backups_dir, filename)
                    try:
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                            backups.append(metadata)
                    except (json.JSONDecodeError, IOError) as exc:
                        logger.warning(
                            "Could not read backup metadata",
                            extra={
                                "event": "backup.metadata.warning",
                                "resource_id": filename,
                            },
                            exc_info=exc,
                        )

            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        except Exception as exc:
            logger.error(
                "Failed to list backups",
                extra={"event": "backup.list.failure"},
                exc_info=exc,
            )
            raise BackupError(
                "Unable to list backups.",
                context={"backups_dir": self.backups_dir},
            ) from exc

        return backups

    def restore_backup(self, backup_id: str, created_by: Optional[str] = None) -> bool:
        """
        Restore data from a specific backup.

        Args:
            backup_id (str): ID of the backup to restore

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            backup_path = self._resolve_backup_path(backup_id)
            if not backup_path or not os.path.exists(backup_path):
                logger.error(
                    "Backup file does not exist",
                    extra={
                        "event": "backup.restore.failure",
                        "resource_id": backup_id,
                    },
                )
                raise BackupError(
                    "Backup file does not exist.",
                    context={"backup_id": backup_id},
                    http_status=404,
                )

            if not self._is_valid_backup_file(backup_path):
                logger.error(
                    "Backup appears to be corrupted",
                    extra={
                        "event": "backup.restore.failure",
                        "resource_id": backup_id,
                    },
                )
                raise BackupError(
                    "Backup appears to be corrupted.",
                    context={"backup_id": backup_id},
                    http_status=400,
                )

            # Create a pre-restore backup automatically
            pre_restore_backup = self.create_backup(
                "pre_restore",
                created_by=created_by,
            )
            if not pre_restore_backup:
                logger.warning(
                    "Could not create pre-restore backup",
                    extra={"event": "backup.restore.warning"},
                )

            # Restore the backup (handle compressed files transparently)
            if backup_path.endswith(".gz"):
                with (
                    gzip.open(backup_path, "rb") as src,
                    open(self.data_file, "wb") as dst,
                ):
                    shutil.copyfileobj(src, dst)
            else:
                shutil.copy2(backup_path, self.data_file)

            logger.info(
                "Backup restored successfully",
                extra={
                    "event": "backup.restore.success",
                    "resource_id": backup_id,
                },
            )
            logging_service.log_audit_event(
                action="backup.restore",
                resource_type="backup",
                resource_id=backup_id,
            )
            return True

        except BackupError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to restore backup",
                extra={
                    "event": "backup.restore.failure",
                    "resource_id": backup_id,
                },
                exc_info=exc,
            )
            raise BackupError(
                "Failed to restore backup.",
                context={"backup_id": backup_id},
            ) from exc

    def cleanup_old_backups(self, retention_days: int = 30) -> int:
        """
        Remove old backups based on retention policy.

        Args:
            retention_days (int): Number of days to keep backups

        Returns:
            int: Number of backups removed
        """
        removed_count = 0

        try:
            cutoff_date = datetime.now().astimezone(timezone.utc) - timedelta(
                days=retention_days
            )
            backups = self.list_backups()

            for backup in backups:
                backup_date = self._parse_backup_timestamp(backup["timestamp"])

                if retention_days <= 0 or backup_date < cutoff_date:
                    # Remove backup files
                    backup_filename = backup["filename"]
                    backup_path = os.path.join(self.backups_dir, backup_filename)
                    metadata_filename = backup_filename.replace(
                        ".json", "_metadata.json"
                    )
                    metadata_path = os.path.join(self.backups_dir, metadata_filename)

                    try:
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                        if os.path.exists(metadata_path):
                            os.remove(metadata_path)
                        removed_count += 1
                        logger.info(
                            "Removed old backup during cleanup",
                            extra={
                                "event": "backup.cleanup.removal",
                                "resource_id": backup_filename,
                            },
                        )
                    except OSError as exc:
                        logger.warning(
                            "Could not remove backup during cleanup",
                            extra={
                                "event": "backup.cleanup.warning",
                                "resource_id": backup_filename,
                            },
                            exc_info=exc,
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

    def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific backup.

        Args:
            backup_id (str): ID of the backup

        Returns:
            Optional[Dict[str, Any]]: Backup metadata if found, None otherwise
        """
        backups = self.list_backups()
        for backup in backups:
            if backup["backup_id"] == backup_id:
                return backup
        return None

    def compress_old_backups(self, days_threshold: int = 7) -> int:
        """
        Compress old backups using gzip.

        Args:
            days_threshold (int): Compress backups older than this many days

        Returns:
            int: Number of backups compressed
        """
        compressed_count = 0

        try:
            cutoff_date = datetime.now().astimezone(timezone.utc) - timedelta(
                days=days_threshold
            )
            backups = self.list_backups()

            for backup in backups:
                backup_date = self._parse_backup_timestamp(backup["timestamp"])

                if days_threshold <= 0 or backup_date < cutoff_date:
                    backup_filename = backup["filename"]
                    backup_path = os.path.join(self.backups_dir, backup_filename)
                    metadata_path = backup_path.replace(".json", "_metadata.json")

                    if os.path.exists(backup_path) and not backup_filename.endswith(
                        ".gz"
                    ):
                        try:
                            # Compress the backup file
                            with open(backup_path, "rb") as f_in:
                                with gzip.open(f"{backup_path}.gz", "wb") as f_out:
                                    shutil.copyfileobj(f_in, f_out)

                            # Remove original file
                            os.remove(backup_path)

                            # Update metadata
                            backup["filename"] = f"{backup_filename}.gz"
                            backup["compressed"] = True
                            backup["original_size"] = backup["size_bytes"]
                            backup["compressed_size"] = os.path.getsize(
                                f"{backup_path}.gz"
                            )

                            with open(metadata_path, "w", encoding="utf-8") as f:
                                json.dump(backup, f, indent=2)

                            compressed_count += 1
                            logger.info(
                                "Compressed backup file",
                                extra={
                                    "event": "backup.compress.success",
                                    "resource_id": backup_filename,
                                },
                            )

                        except Exception as exc:
                            logger.warning(
                                "Could not compress backup",
                                extra={
                                    "event": "backup.compress.warning",
                                    "resource_id": backup_filename,
                                },
                                exc_info=exc,
                            )

            if compressed_count > 0:
                logger.info(
                    "Compression completed",
                    extra={
                        "event": "backup.compress.summary",
                        "compressed_count": compressed_count,
                    },
                )
                logging_service.log_audit_event(
                    action="backup.compress",
                    resource_type="backup",
                    resource_id="multiple",
                    compressed_count=compressed_count,
                )

        except Exception as exc:
            logger.error(
                "Failed to compress old backups",
                extra={"event": "backup.compress.failure"},
                exc_info=exc,
            )
            raise BackupError(
                "Failed to compress old backups.",
                context={"days_threshold": days_threshold},
            ) from exc

        return compressed_count

    def get_backup_stats(self) -> Dict[str, Any]:
        """
        Get statistics about backups.

        Returns:
            Dict[str, Any]: Backup statistics
        """
        backups = self.list_backups()

        if not backups:
            return {
                "total_backups": 0,
                "total_size": 0,
                "oldest_backup": None,
                "newest_backup": None,
                "compressed_count": 0,
                "compressed_backups": 0,
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
            "compressed_backups": compressed_count,
        }

    def delete_backup(self, backup_id: str) -> bool:
        """
        Delete a backup and its metadata files.

        Args:
            backup_id (str): Backup ID to delete

        Returns:
            bool: True if any files were removed, False otherwise
        """
        try:
            metadata = self.get_backup_info(backup_id)
            filename = metadata.get("filename") if metadata else None
            candidates = set()

            base_json = os.path.join(self.backups_dir, f"{backup_id}.json")
            candidates.add(base_json)
            candidates.add(f"{base_json}.gz")

            if filename:
                candidates.add(os.path.join(self.backups_dir, filename))

            removed = False
            for path in candidates:
                if path and os.path.exists(path):
                    os.remove(path)
                    removed = True

            metadata_path = self._metadata_path_from_filename(
                filename or f"{backup_id}.json"
            )
            if metadata_path and os.path.exists(metadata_path):
                os.remove(metadata_path)
                removed = True

            if removed:
                logging_service.log_audit_event(
                    action="backup.delete",
                    resource_type="backup",
                    resource_id=backup_id,
                )
            return removed
        except Exception as exc:
            logger.error(
                "Failed to delete backup",
                extra={"event": "backup.delete.failure", "resource_id": backup_id},
                exc_info=exc,
            )
            raise BackupError(
                "Failed to delete backup.",
                context={"backup_id": backup_id},
            ) from exc

    def _get_current_user(self) -> str:
        """
        Get the current user.

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

    def _metadata_path_from_filename(self, filename: str) -> Optional[str]:
        """Derive metadata path from a backup filename."""
        if not filename:
            return None
        if filename.endswith(".json.gz"):
            base = filename[: -len(".json.gz")]
        elif filename.endswith(".json"):
            base = filename[: -len(".json")]
        else:
            base = filename
        return os.path.join(self.backups_dir, f"{base}_metadata.json")

    def _resolve_backup_path(self, backup_id: str) -> Optional[str]:
        """Resolve the on-disk path for a backup, checking compressed variants."""
        candidate = os.path.join(self.backups_dir, f"{backup_id}.json")
        if os.path.exists(candidate):
            return candidate
        gz_candidate = f"{candidate}.gz"
        if os.path.exists(gz_candidate):
            return gz_candidate
        metadata = self.get_backup_info(backup_id)
        if metadata:
            meta_candidate = os.path.join(
                self.backups_dir, metadata.get("filename", "")
            )
            if meta_candidate and os.path.exists(meta_candidate):
                return meta_candidate
        return None

    def _is_valid_backup_file(self, backup_path: str) -> bool:
        """Validate that a backup file contains readable JSON."""
        try:
            if backup_path.endswith(".gz"):
                with gzip.open(backup_path, "rt", encoding="utf-8") as f:
                    json.load(f)
            else:
                with open(backup_path, "r", encoding="utf-8") as f:
                    json.load(f)
            return True
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Backup validation error",
                extra={
                    "event": "backup.validation.failure",
                    "resource_id": backup_path,
                },
                exc_info=exc,
            )
            return False

    @staticmethod
    def _parse_backup_timestamp(raw: str) -> datetime:
        """Return timezone-aware datetime for backup metadata."""
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
