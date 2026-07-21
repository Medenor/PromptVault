# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Backup creation: builds a new backup file via the appropriate
DumpStrategy, then records its metadata (and optionally encrypts it)."""

import os
from datetime import datetime, timezone
from typing import Optional

from src.db.session import get_db_session
from src.db.models.prompt import Prompt
from src.services.exceptions import BackupError
from src.services.logging_service import logging_service
from src.services.backup_dump_strategy import get_dump_strategy
from src.services.backup_metadata_store import BackupMetadataStore

logger = logging_service.get_logger(__name__)


class BackupCreationService:
    def __init__(self, backups_dir: str, metadata_store: BackupMetadataStore):
        self.backups_dir = backups_dir
        self.metadata_store = metadata_store

    def create_backup(
        self,
        custom_name: Optional[str],
        created_by: Optional[str],
        get_current_user,
        encrypt: bool = False,
        passphrase: Optional[str] = None,
        backup_kind: str = "full",
    ) -> Optional[str]:
        from src.services.backup_audit_service import BackupAuditService

        audit_service = BackupAuditService()

        try:
            backup_id = self._generate_backup_id(custom_name)
            backup_type, strategy = get_dump_strategy()

            extension = ".db" if backup_type == "sqlite_copy" else ".sql"
            backup_filename = f"{backup_id}{extension}"
            backup_path = os.path.join(self.backups_dir, backup_filename)

            try:
                strategy.dump(backup_path)
            except BackupError:
                raise
            except Exception as exc:
                logger.error(
                    "Failed to create backup",
                    extra={"event": "backup.create.failure", "backup_id": backup_id},
                    exc_info=exc,
                )
                raise BackupError(
                    f"Failed to create {backup_type} backup.",
                    context={"backup_id": backup_id},
                ) from exc

            backup_size = os.path.getsize(backup_path)
            prompt_count = self._get_prompt_count()
            created_by_name = created_by or get_current_user()
            timestamp = datetime.now(timezone.utc).isoformat()

            metadata = {
                "backup_id": backup_id,
                "backup_type": backup_type,
                "backup_kind": backup_kind,
                "filename": backup_filename,
                "storage_path": backup_path,
                "size_bytes": backup_size,
                "prompt_count": prompt_count,
                "database_type": "sqlite" if backup_type == "sqlite_copy" else "postgresql",
                "created_by": created_by_name,
                "compressed": False,
                "timestamp": timestamp,
                "is_encrypted": False,
                "encryption_salt": None,
                "encryption_nonce": None,
            }

            # Save metadata before encrypting so the salt/nonce are always
            # recorded even if the process dies mid-encrypt.
            self.metadata_store.save_metadata_to_db(
                backup_id, metadata, backup_kind=backup_kind
            )
            self.metadata_store.write_metadata_file(metadata)

            if encrypt:
                if not passphrase:
                    raise BackupError(
                        "passphrase required when encrypt=True",
                        context={"backup_id": backup_id},
                    )
                from src.services.backup_encryption_service import (
                    BackupEncryptionService,
                )

                enc_service = BackupEncryptionService()
                encryption_salt, encryption_nonce = enc_service.encrypt_file(
                    backup_path, passphrase
                )
                metadata["is_encrypted"] = True
                metadata["encryption_salt"] = encryption_salt
                metadata["encryption_nonce"] = encryption_nonce
                self.metadata_store.update_backup_encryption(
                    backup_id, encryption_salt, encryption_nonce
                )
                self.metadata_store.write_metadata_file(metadata)

            logger.info(
                f"{metadata['database_type'].capitalize()} backup created successfully",
                extra={
                    "event": "backup.create.success",
                    "resource_id": backup_id,
                    "backup_type": backup_type,
                },
            )
            logging_service.log_audit_event(
                action="backup.create",
                resource_type="backup",
                resource_id=backup_id,
                backup_type=backup_type,
                size_bytes=backup_size,
            )

            audit_service.log(
                operation="backup.create",
                outcome="success",
                backup_id=backup_id,
                performed_by=created_by_name,
            )
            return backup_id

        except BackupError as exc:
            audit_service.log(
                operation="backup.create",
                outcome="failure",
                performed_by=created_by or get_current_user(),
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
                performed_by=created_by or get_current_user(),
                detail={"error": str(exc)},
            )
            raise BackupError("Failed to create backup.", context={}) from exc

    def _generate_backup_id(self, custom_name: Optional[str]) -> str:
        # Include microseconds, truncate to milliseconds, for uniqueness.
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:21]
        if custom_name:
            safe_suffix = self._sanitize_backup_name(custom_name)
            return f"backup_{safe_suffix}_{timestamp}" if safe_suffix else f"backup_{timestamp}"
        return f"backup_{timestamp}"

    @staticmethod
    def _sanitize_backup_name(name: str) -> str:
        """Sanitize custom backup names for safe filenames."""
        import re

        if not name:
            return ""
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip())
        return cleaned[:64]

    @staticmethod
    def _get_prompt_count() -> int:
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
