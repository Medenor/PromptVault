# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

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
from src.db.models.prompt import Prompt
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

    def create_backup(
        self,
        custom_name: Optional[str] = None,
        created_by: Optional[str] = None,
        encrypt: bool = False,
        passphrase: Optional[str] = None,
        backup_kind: str = "full",
    ) -> Optional[str]:
        """Create a backup of the database.

        Args:
            custom_name (str): Optional custom name for the backup
            created_by (str): Optional username for audit metadata
            encrypt (bool): Whether to encrypt the backup
            passphrase (str): Passphrase for encryption (required if encrypt=True)

        Returns:
            Optional[str]: Backup ID if successful, None otherwise
        """
        from src.services.backup_audit_service import BackupAuditService
        audit_service = BackupAuditService()

        try:
            # Generate backup ID with microseconds for uniqueness
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[
                :21
            ]  # Include microseconds, truncate to milliseconds
            if custom_name:
                safe_suffix = self._sanitize_backup_name(custom_name)
                backup_id = (
                    f"backup_{safe_suffix}_{timestamp}"
                    if safe_suffix
                    else f"backup_{timestamp}"
                )
            else:
                backup_id = f"backup_{timestamp}"

            # Create backup based on database type
            if db_settings.is_sqlite:
                result = self._create_sqlite_backup(backup_id, created_by, encrypt=encrypt, passphrase=passphrase, backup_kind=backup_kind)
            elif db_settings.is_postgresql:
                result = self._create_pg_backup(backup_id, created_by, encrypt=encrypt, passphrase=passphrase, backup_kind=backup_kind)
            else:
                raise BackupError(
                    "Unsupported database type",
                    context={"database_url": db_settings.DATABASE_URL},
                )

            audit_service.log(
                operation="backup.create",
                outcome="success",
                backup_id=result,
                performed_by=created_by or self._get_current_user(),
            )
            return result

        except BackupError as exc:
            audit_service.log(
                operation="backup.create",
                outcome="failure",
                performed_by=created_by or self._get_current_user(),
                detail={"error": str(exc)},
            )
            raise
        except Exception as exc:
            logger.error(
                "Failed to create backup",
                extra={"event": "backup.create.failure"},
                exc_info=exc,
            )
            audit_service.log(
                operation="backup.create",
                outcome="failure",
                performed_by=created_by or self._get_current_user(),
                detail={"error": str(exc)},
            )
            raise BackupError("Failed to create backup.", context={}) from exc

    def _create_sqlite_backup(
        self, backup_id: str, created_by: Optional[str] = None,
        encrypt: bool = False, passphrase: Optional[str] = None,
        backup_kind: str = "full",
    ) -> str:
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
                    context={"database_url": db_url},
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
                    http_status=404,
                )

            # Create backup file path
            backup_filename = f"{backup_id}.db"
            backup_path = os.path.join(self.backups_dir, backup_filename)

            # Use VACUUM INTO rather than a raw file copy so the backup
            # excludes free/unused pages left behind by deletes (e.g. after
            # session cleanup sweeps). A plain shutil.copy2 would faithfully
            # copy the live file's high-water-mark size, including pages
            # SQLite has freed but not reclaimed.
            import sqlite3
            source_conn = sqlite3.connect(db_path)
            try:
                source_conn.execute("VACUUM INTO ?", (backup_path,))
            finally:
                source_conn.close()

            backup_size = os.path.getsize(backup_path)
            prompt_count = self._get_prompt_count()
            created_by_name = created_by or self._get_current_user()
            timestamp = datetime.now(timezone.utc).isoformat()

            is_encrypted = False
            encryption_salt = None
            encryption_nonce = None

            # Save metadata before encrypting so the salt/nonce are always
            # recorded even if the process dies mid-encrypt.
            metadata = {
                "backup_id": backup_id,
                "backup_type": "sqlite_copy",
                "backup_kind": backup_kind,
                "filename": backup_filename,
                "storage_path": backup_path,
                "size_bytes": backup_size,
                "prompt_count": prompt_count,
                "database_type": "sqlite",
                "created_by": created_by_name,
                "compressed": False,
                "timestamp": timestamp,
                "is_encrypted": False,
                "encryption_salt": None,
                "encryption_nonce": None,
            }

            self._save_metadata_to_db(backup_id, metadata, backup_kind=backup_kind)
            self._write_metadata_file(metadata)

            if encrypt:
                if not passphrase:
                    raise BackupError(
                        "passphrase required when encrypt=True",
                        context={"backup_id": backup_id},
                    )
                from src.services.backup_encryption_service import BackupEncryptionService
                enc_service = BackupEncryptionService()
                encryption_salt, encryption_nonce = enc_service.encrypt_file(backup_path, passphrase)
                is_encrypted = True
                metadata["is_encrypted"] = True
                metadata["encryption_salt"] = encryption_salt
                metadata["encryption_nonce"] = encryption_nonce
                self._update_backup_encryption(backup_id, encryption_salt, encryption_nonce)
                self._write_metadata_file(metadata)

            logger.info(
                "SQLite backup created successfully",
                extra={
                    "event": "backup.create.success",
                    "resource_id": backup_id,
                    "backup_type": "sqlite_copy",
                },
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
                exc_info=exc,
            )
            raise BackupError(
                "Failed to create SQLite backup.", context={"backup_id": backup_id}
            ) from exc

    def _create_pg_backup(
        self, backup_id: str, created_by: Optional[str] = None,
        encrypt: bool = False, passphrase: Optional[str] = None,
        backup_kind: str = "full",
    ) -> str:
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
                "--file",
                backup_path,
                "--format=plain",
                "--clean",
                "--if-exists",
                db_url,
            ]

            # Execute pg_dump
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            backup_size = os.path.getsize(backup_path)
            prompt_count = self._get_prompt_count()
            created_by_name = created_by or self._get_current_user()
            timestamp = datetime.now(timezone.utc).isoformat()

            is_encrypted = False
            encryption_salt = None
            encryption_nonce = None

            metadata = {
                "backup_id": backup_id,
                "backup_type": "pg_dump",
                "backup_kind": backup_kind,
                "filename": backup_filename,
                "storage_path": backup_path,
                "size_bytes": backup_size,
                "prompt_count": prompt_count,
                "database_type": "postgresql",
                "created_by": created_by_name,
                "compressed": False,
                "timestamp": timestamp,
                "is_encrypted": False,
                "encryption_salt": None,
                "encryption_nonce": None,
            }

            self._save_metadata_to_db(backup_id, metadata, backup_kind=backup_kind)
            self._write_metadata_file(metadata)

            if encrypt:
                if not passphrase:
                    raise BackupError(
                        "passphrase required when encrypt=True",
                        context={"backup_id": backup_id},
                    )
                from src.services.backup_encryption_service import BackupEncryptionService
                enc_service = BackupEncryptionService()
                encryption_salt, encryption_nonce = enc_service.encrypt_file(backup_path, passphrase)
                is_encrypted = True
                metadata["is_encrypted"] = True
                metadata["encryption_salt"] = encryption_salt
                metadata["encryption_nonce"] = encryption_nonce
                self._update_backup_encryption(backup_id, encryption_salt, encryption_nonce)
                self._write_metadata_file(metadata)

            logger.info(
                "PostgreSQL backup created successfully",
                extra={
                    "event": "backup.create.success",
                    "resource_id": backup_id,
                    "backup_type": "pg_dump",
                },
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
                    "error": error_msg,
                },
                exc_info=exc,
            )
            raise BackupError(
                f"pg_dump failed: {error_msg}", context={"backup_id": backup_id}
            ) from exc
        except Exception as exc:
            logger.error(
                "Failed to create PostgreSQL backup",
                extra={"event": "backup.create.failure", "backup_id": backup_id},
                exc_info=exc,
            )
            raise BackupError(
                "Failed to create PostgreSQL backup.", context={"backup_id": backup_id}
            ) from exc

    @staticmethod
    def _maybe_decompress(path: str) -> str:
        """If path is gzip-compressed, decompress it to a sibling temp file.

        Returns the path to a readable, uncompressed file. Callers are
        responsible for removing the returned path if it differs from the
        input path.
        """
        if not path.endswith(".gz"):
            return path
        decompressed_path = path[: -len(".gz")] + ".decompressed"
        with gzip.open(path, "rb") as src, open(decompressed_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
        return decompressed_path

    def restore_backup(
        self, backup_id: str, created_by: Optional[str] = None,
        passphrase: Optional[str] = None,
    ) -> bool:
        """Restore database from a backup.

        Creates a pre-restore backup automatically before restoring.

        Args:
            backup_id (str): ID of the backup to restore
            created_by (str): Optional username for audit metadata
            passphrase (str): Passphrase for decrypting encrypted backups

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
                    http_status=404,
                )

            backup_type = metadata.get("backup_type")

            # Verify backup file exists locally, downloading from cloud if needed
            backup_path = self._ensure_local_backup_file(backup_id, metadata)

            decompressed_path = self._maybe_decompress(backup_path)
            if decompressed_path != backup_path:
                backup_path = decompressed_path

            is_encrypted = metadata.get("is_encrypted", False)
            if is_encrypted:
                if not passphrase:
                    raise BackupError(
                        "Passphrase required for encrypted backup",
                        context={"backup_id": backup_id},
                        http_status=400,
                    )
                from src.services.backup_encryption_service import BackupEncryptionService
                enc_service = BackupEncryptionService()

                with get_db_session() as session:
                    backup_record = session.query(Backup).filter_by(id=backup_id).first()
                    if backup_record:
                        salt = backup_record.encryption_salt
                        nonce = backup_record.encryption_nonce
                    else:
                        salt = metadata.get("encryption_salt")
                        nonce = metadata.get("encryption_nonce")

                if not salt or not nonce:
                    raise BackupError(
                        "Encrypted backup missing salt/nonce",
                        context={"backup_id": backup_id},
                    )

                decrypted_path = backup_path + ".decrypted"
                shutil.copy2(backup_path, decrypted_path)
                try:
                    enc_service.decrypt_file(decrypted_path, passphrase, salt, nonce)
                    backup_path = decrypted_path
                except ValueError as exc:
                    if os.path.exists(decrypted_path):
                        os.remove(decrypted_path)
                    if decompressed_path != metadata.get("storage_path") and os.path.exists(decompressed_path):
                        os.remove(decompressed_path)
                    raise BackupError(
                        "Decryption failed: wrong passphrase or corrupt data",
                        context={"backup_id": backup_id},
                        http_status=400,
                    ) from exc
            else:
                decrypted_path = None

            try:
                # Create pre-restore backup with unique timestamp
                from datetime import datetime, timezone

                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[
                    :21
                ]  # Include microseconds for uniqueness
                logger.info(
                    "Creating pre-restore backup",
                    extra={"event": "backup.restore.pre_backup"},
                )
                pre_restore_backup = self.create_backup(
                    f"pre_restore_{timestamp}",
                    created_by=created_by,
                )
                if not pre_restore_backup:
                    logger.warning(
                        "Could not create pre-restore backup",
                        extra={"event": "backup.restore.warning"},
                    )

                # Restore based on backup type
                if backup_type == "pg_dump":
                    success = self._restore_pg_backup(backup_id, backup_path)
                elif backup_type == "sqlite_copy":
                    success = self._restore_sqlite_backup(backup_id, backup_path)
                else:
                    raise BackupError(
                        f"Unsupported backup type: {backup_type}",
                        context={"backup_id": backup_id, "backup_type": backup_type},
                    )
            finally:
                if decrypted_path and os.path.exists(decrypted_path):
                    os.remove(decrypted_path)
                if decompressed_path != metadata.get("storage_path") and os.path.exists(decompressed_path):
                    os.remove(decompressed_path)

            from src.services.backup_audit_service import BackupAuditService
            audit_service = BackupAuditService()

            if success:
                logger.info(
                    "Backup restored successfully",
                    extra={"event": "backup.restore.success", "resource_id": backup_id},
                )
                logging_service.log_audit_event(
                    action="backup.restore",
                    resource_type="backup",
                    resource_id=backup_id,
                )
                audit_service.log(
                    operation="backup.restore",
                    outcome="success",
                    backup_id=backup_id,
                    performed_by=created_by or self._get_current_user(),
                )
            else:
                audit_service.log(
                    operation="backup.restore",
                    outcome="failure",
                    backup_id=backup_id,
                    performed_by=created_by or self._get_current_user(),
                )

            return success

        except BackupError as exc:
            from src.services.backup_audit_service import BackupAuditService
            BackupAuditService().log(
                operation="backup.restore",
                outcome="failure",
                backup_id=backup_id,
                performed_by=created_by or self._get_current_user(),
                detail={"error": str(exc)},
            )
            raise
        except Exception as exc:
            logger.error(
                "Failed to restore backup",
                extra={"event": "backup.restore.failure", "resource_id": backup_id},
                exc_info=exc,
            )
            from src.services.backup_audit_service import BackupAuditService
            BackupAuditService().log(
                operation="backup.restore",
                outcome="failure",
                backup_id=backup_id,
                performed_by=created_by or self._get_current_user(),
                detail={"error": str(exc)},
            )
            raise BackupError(
                "Failed to restore backup.", context={"backup_id": backup_id}
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
                    context={"database_url": db_url},
                )

            # Resolve relative paths
            if not os.path.isabs(db_path):
                script_dir = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                db_path = os.path.join(script_dir, db_path)

            # Use SQLite's online backup API to safely replace the live database.
            # This avoids the corruption risk of a raw file copy while connections
            # are open and properly handles WAL/SHM state.
            import sqlite3
            from src.db.session import engine

            engine.dispose()

            src_conn = sqlite3.connect(backup_path)
            dst_conn = sqlite3.connect(db_path)
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
                src_conn.close()

            logger.info(
                "SQLite database restored from backup",
                extra={"event": "backup.restore.success", "backup_id": backup_id},
            )

            return True

        except Exception as exc:
            logger.error(
                "Failed to restore SQLite backup",
                extra={"event": "backup.restore.failure", "backup_id": backup_id},
                exc_info=exc,
            )
            raise BackupError(
                "Failed to restore SQLite backup.", context={"backup_id": backup_id}
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

            cmd = ["psql", "--file", backup_path, db_url]

            # Execute psql
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            logger.info(
                "PostgreSQL database restored from backup",
                extra={"event": "backup.restore.success", "backup_id": backup_id},
            )

            return True

        except subprocess.CalledProcessError as exc:
            error_msg = exc.stderr if exc.stderr else str(exc)
            logger.error(
                "psql restore failed",
                extra={
                    "event": "backup.restore.failure",
                    "backup_id": backup_id,
                    "error": error_msg,
                },
                exc_info=exc,
            )
            raise BackupError(
                f"psql restore failed: {error_msg}", context={"backup_id": backup_id}
            ) from exc
        except Exception as exc:
            logger.error(
                "Failed to restore PostgreSQL backup",
                extra={"event": "backup.restore.failure", "backup_id": backup_id},
                exc_info=exc,
            )
            raise BackupError(
                "Failed to restore PostgreSQL backup.", context={"backup_id": backup_id}
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
                        "cloud_uploaded_at": backup.cloud_uploaded_at.isoformat() if backup.cloud_uploaded_at else None,
                        "is_encrypted": backup.is_encrypted or False,
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
                exc_info=exc,
            )
            raise BackupError(
                "Unable to list backups.", context={"backups_dir": self.backups_dir}
            ) from exc

    def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific backup.

        Args:
            backup_id (str): ID of the backup

        Returns:
            Optional[Dict[str, Any]]: Backup metadata if found, None otherwise
        """
        self._validate_backup_id(backup_id)
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
                        "cloud_uploaded_at": backup.cloud_uploaded_at.isoformat() if backup.cloud_uploaded_at else None,
                    }
                    self._ensure_metadata_file(info)
                    return info

        except Exception as exc:
            logger.error(
                "Failed to get backup info",
                extra={"event": "backup.info.failure", "resource_id": backup_id},
                exc_info=exc,
            )

        # Fallback to metadata file
        return self._load_metadata_from_file(backup_id)

    def _ensure_local_backup_file(self, backup_id: str, metadata: Dict[str, Any]) -> str:
        """Ensure the backup file exists locally, downloading from cloud if needed.

        If the local storage_path is missing (e.g. removed by cleanup, or this
        backup was only ever uploaded from another machine), fall back to the
        cloud copy referenced by cloud_provider_id/cloud_path.

        Args:
            backup_id: Backup identifier
            metadata: Backup metadata dict from get_backup_info()

        Returns:
            str: Local path to the backup file (existing or freshly downloaded)

        Raises:
            BackupError: If the file is missing locally and no cloud copy is available
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

        from src.services.backup_cloud_service import BackupCloudService
        from src.db.models.backup_storage_provider import BackupStorageProvider

        with get_db_session() as session:
            provider = session.query(BackupStorageProvider).filter_by(id=cloud_provider_id).first()
            if not provider or not provider.enabled:
                raise BackupError(
                    "Cloud storage provider not found or disabled",
                    context={"backup_id": backup_id, "provider_id": cloud_provider_id},
                    http_status=404,
                )

            dest_path = backup_path or os.path.join(self.backups_dir, metadata.get("filename", f"{backup_id}.db"))
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
            extra={"event": "backup.restore.cloud_download_success", "backup_id": backup_id},
        )

        if not metadata.get("storage_path"):
            self._update_backup_record(backup_id, {**metadata, "storage_path": dest_path})

        return dest_path

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup and its files.

        Args:
            backup_id (str): Backup ID to delete

        Returns:
            bool: True if successful
        """
        self._validate_backup_id(backup_id)
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
                    from src.db.models.backup_audit_log import AuditLogEntry

                    session.query(AuditLogEntry).filter_by(backup_id=backup_id).update(
                        {"backup_id": None}
                    )
                    session.delete(backup)
                    session.flush()

                self._remove_metadata_file(backup_id)

                logging_service.log_audit_event(
                    action="backup.delete",
                    resource_type="backup",
                    resource_id=backup_id,
                )

                from src.services.backup_audit_service import BackupAuditService
                BackupAuditService().log(
                    operation="backup.delete",
                    outcome="success",
                    performed_by=self._get_current_user(),
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
                performed_by=self._get_current_user(),
                detail={"backup_id": backup_id, "error": str(exc)},
            )
            raise BackupError(
                "Failed to delete backup.", context={"backup_id": backup_id}
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
                exc_info=exc,
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
                context={"days_threshold": days_threshold},
            ) from exc

        return compressed_count

    def _save_metadata_to_db(self, backup_id: str, metadata: Dict[str, Any],
                              is_encrypted: bool = False,
                              encryption_salt: Optional[str] = None,
                              encryption_nonce: Optional[str] = None,
                              backup_kind: str = "full") -> None:
        """Save backup metadata to database.

        Args:
            backup_id: Backup identifier
            metadata: Backup metadata dictionary
            is_encrypted: Whether backup is encrypted
            encryption_salt: Hex-encoded salt for encryption
            encryption_nonce: Hex-encoded nonce for encryption
        """
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
                extra={
                    "event": "backup.metadata.update_failure",
                    "backup_id": backup_id,
                },
                exc_info=exc,
            )

    def _update_backup_encryption(
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

    def _get_prompt_count(self) -> int:
        """Return the current count of prompts for backup metadata."""
        try:
            with get_db_session() as session:
                return session.query(Prompt).count()
        except Exception as exc:
            logger.warning(
                "Failed to count prompts for backup metadata",
                extra={"event": "backup.prompt_count.warning"},
                exc_info=exc,
            )
            return 0

    _BACKUP_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,128}$')

    def _validate_backup_id(self, backup_id: str) -> None:
        """Reject backup_id values that could cause path traversal."""
        if not self._BACKUP_ID_RE.match(backup_id):
            raise BackupError(
                "Invalid backup ID",
                context={"backup_id": backup_id},
                http_status=400,
            )

    def _metadata_file_path(self, backup_id: str) -> str:
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

    def _write_metadata_file(self, metadata: Dict[str, Any]) -> None:
        """Persist metadata alongside backup for DB-restore resilience."""
        try:
            path = self._metadata_file_path(metadata["backup_id"])
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
                extra={
                    "event": "backup.metadata_file.read_failure",
                    "resource_id": backup_id,
                },
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
                        extra={
                            "event": "backup.metadata_file.parse_failure",
                            "resource_id": filename,
                        },
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
                extra={
                    "event": "backup.metadata_file.remove_failure",
                    "resource_id": backup_id,
                },
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

    def compute_restore_diff(
        self, backup_id: str, passphrase: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute a diff of what would change if this backup were restored.

        Args:
            backup_id: Backup to preview
            passphrase: Passphrase for encrypted backups

        Returns:
            Dict with 'added', 'updated', 'deleted' lists and 'summary'
        """
        import tempfile
        import json as json_lib

        metadata = self.get_backup_info(backup_id)
        if not metadata:
            raise BackupError("Backup not found", context={"backup_id": backup_id}, http_status=404)

        backup_path = self._ensure_local_backup_file(backup_id, metadata)

        working_path = self._maybe_decompress(backup_path)
        decompressed = working_path != backup_path

        is_encrypted = metadata.get("is_encrypted", False)

        if is_encrypted:
            if not passphrase:
                raise BackupError("Passphrase required for encrypted backup", http_status=400)
            from src.services.backup_encryption_service import BackupEncryptionService
            enc_service = BackupEncryptionService()
            with get_db_session() as session:
                backup_record = session.query(Backup).filter_by(id=backup_id).first()
                salt = backup_record.encryption_salt if backup_record else metadata.get("encryption_salt")
                nonce = backup_record.encryption_nonce if backup_record else metadata.get("encryption_nonce")
            if not salt or not nonce:
                raise BackupError("Encrypted backup missing salt/nonce")
            decrypted_path = working_path + ".preview_decrypted"
            shutil.copy2(working_path, decrypted_path)
            try:
                enc_service.decrypt_file(decrypted_path, passphrase, salt, nonce)
            except ValueError:
                if os.path.exists(decrypted_path):
                    os.remove(decrypted_path)
                if decompressed and os.path.exists(working_path):
                    os.remove(working_path)
                raise BackupError("Decryption failed", http_status=400)
            if decompressed and os.path.exists(working_path):
                os.remove(working_path)
            working_path = decrypted_path
            decompressed = True  # ensure cleanup below removes this temp file too

        try:
            backup_prompts = self._extract_prompts_from_backup(working_path, metadata.get("backup_type", "sqlite_copy"))
        finally:
            if decompressed and os.path.exists(working_path) and working_path != backup_path:
                os.remove(working_path)

        with get_db_session() as session:
            current_prompts = session.query(Prompt).all()
            current_map = {p.id: {"title": p.title, "prompt": p.prompt} for p in current_prompts}

        backup_map = {p["id"]: p for p in backup_prompts if "id" in p}

        added = []
        updated = []
        deleted = []

        for pid, bp in backup_map.items():
            if pid not in current_map:
                added.append({"id": pid, "title": bp.get("title", ""), "prompt": bp.get("prompt", "")[:200]})
            else:
                cp = current_map[pid]
                if cp["title"] != bp.get("title") or cp["prompt"] != bp.get("prompt"):
                    updated.append({
                        "id": pid,
                        "title": bp.get("title", ""),
                        "before": {"title": cp["title"], "prompt": cp["prompt"][:200]},
                        "after": {"title": bp.get("title", ""), "prompt": bp.get("prompt", "")[:200]},
                    })

        for pid, cp in current_map.items():
            if pid not in backup_map:
                deleted.append({"id": pid, "title": cp["title"]})

        return {
            "backup_id": backup_id,
            "summary": {"added": len(added), "updated": len(updated), "deleted": len(deleted)},
            "changes": {"added": added, "updated": updated, "deleted": deleted},
        }

    def _extract_prompts_from_backup(self, backup_path: str, backup_type: str) -> list:
        """Extract prompt records from a backup file.

        Args:
            backup_path: Path to the backup file
            backup_type: Type of backup

        Returns:
            List of prompt dicts
        """
        if backup_type == "sqlite_copy":
            import sqlite3
            try:
                conn = sqlite3.connect(backup_path)
                cursor = conn.execute("SELECT id, title, prompt, note, favorite, category_id, semantic_version FROM prompts")
                prompts = []
                for row in cursor:
                    prompts.append({
                        "id": row[0], "title": row[1], "prompt": row[2],
                        "note": row[3], "favorite": bool(row[4]),
                        "category_id": row[5], "semantic_version": row[6],
                    })
                conn.close()
                return prompts
            except Exception as exc:
                logger.error(
                    "Failed to read prompts from backup file",
                    extra={"event": "backup.extract_prompts.failure", "resource_id": backup_path},
                    exc_info=exc,
                )
                raise BackupError(
                    "Backup file is unreadable or corrupt",
                    context={"backup_path": backup_path},
                ) from exc
        return []

    def selective_restore(
        self,
        backup_id: str,
        prompt_ids: list,
        created_by: Optional[str] = None,
        passphrase: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Restore only specific prompts from a backup.

        Args:
            backup_id: Backup to restore from
            prompt_ids: List of prompt IDs to restore
            created_by: Username performing the restore
            passphrase: Passphrase for encrypted backups

        Returns:
            Dict with 'restored' and 'pre_restore_backup_id'
        """
        import tempfile
        import json as json_lib

        from src.services.backup_audit_service import BackupAuditService
        audit_service = BackupAuditService()

        try:
            metadata = self.get_backup_info(backup_id)
            if not metadata:
                raise BackupError("Backup not found", context={"backup_id": backup_id}, http_status=404)

            pre_restore_id = self.create_backup(
                custom_name=f"pre_selective_restore_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                created_by=created_by,
            )

            backup_path = self._ensure_local_backup_file(backup_id, metadata)
            is_encrypted = metadata.get("is_encrypted", False)
            working_path = self._maybe_decompress(backup_path)
            decompressed = working_path != backup_path

            if is_encrypted:
                if not passphrase:
                    raise BackupError("Passphrase required for encrypted backup", http_status=400)
                from src.services.backup_encryption_service import BackupEncryptionService
                enc_service = BackupEncryptionService()
                with get_db_session() as session:
                    backup_record = session.query(Backup).filter_by(id=backup_id).first()
                    salt = backup_record.encryption_salt if backup_record else metadata.get("encryption_salt")
                    nonce = backup_record.encryption_nonce if backup_record else metadata.get("encryption_nonce")
                if not salt or not nonce:
                    raise BackupError(
                        "Encrypted backup missing salt/nonce",
                        context={"backup_id": backup_id},
                    )
                decrypted_path = working_path + ".selective_decrypted"
                shutil.copy2(working_path, decrypted_path)
                try:
                    enc_service.decrypt_file(decrypted_path, passphrase, salt, nonce)
                except ValueError:
                    if os.path.exists(decrypted_path):
                        os.remove(decrypted_path)
                    if decompressed and os.path.exists(working_path):
                        os.remove(working_path)
                    raise BackupError("Decryption failed", http_status=400)
                if decompressed and os.path.exists(working_path):
                    os.remove(working_path)
                working_path = decrypted_path
                decompressed = True

            try:
                backup_prompts = self._extract_prompts_from_backup(working_path, metadata.get("backup_type", "sqlite_copy"))
            finally:
                if decompressed and os.path.exists(working_path) and working_path != backup_path:
                    os.remove(working_path)

            backup_map = {p["id"]: p for p in backup_prompts}
            restored_count = 0

            with get_db_session() as session:
                for pid in prompt_ids:
                    if pid not in backup_map:
                        continue
                    bp = backup_map[pid]
                    existing = session.query(Prompt).filter_by(id=pid).first()
                    if existing:
                        existing.title = bp.get("title", existing.title)
                        existing.prompt = bp.get("prompt", existing.prompt)
                        existing.note = bp.get("note", existing.note)
                        if bp.get("favorite") is not None:
                            existing.favorite = bp["favorite"]
                        restored_count += 1
                    else:
                        new_prompt = Prompt(
                            id=pid,
                            title=bp.get("title", ""),
                            prompt=bp.get("prompt", ""),
                            note=bp.get("note"),
                            favorite=bp.get("favorite", False),
                        )
                        session.add(new_prompt)
                        restored_count += 1
                session.commit()

            audit_service.log(
                operation="backup.selective_restore",
                outcome="success",
                backup_id=backup_id,
                performed_by=created_by or self._get_current_user(),
                detail={"prompt_ids": prompt_ids, "restored_count": restored_count},
            )

            return {"restored": True, "pre_restore_backup_id": pre_restore_id, "count": restored_count}

        except BackupError as exc:
            audit_service.log(
                operation="backup.selective_restore",
                outcome="failure",
                backup_id=backup_id,
                performed_by=created_by or self._get_current_user(),
                detail={"error": str(exc)},
            )
            raise
        except Exception as exc:
            logger.error(
                "Failed to selectively restore backup",
                extra={"event": "backup.selective_restore.failure", "resource_id": backup_id},
                exc_info=exc,
            )
            audit_service.log(
                operation="backup.selective_restore",
                outcome="failure",
                backup_id=backup_id,
                performed_by=created_by or self._get_current_user(),
                detail={"error": str(exc)},
            )
            raise BackupError(
                "Failed to selectively restore backup.", context={"backup_id": backup_id}
            ) from exc
