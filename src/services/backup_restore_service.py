# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Backup restore: validate -> prepare (decompress/decrypt) -> apply
(DumpStrategy.restore) -> verify, plus selective (per-prompt) restore."""

import gzip
import os
import shutil
from datetime import UTC, datetime
from typing import Any

from src.db.models import Backup
from src.db.models.prompt import Prompt
from src.db.session import get_db_session
from src.services.backup_dump_strategy import PostgresDumpStrategy, SqliteDumpStrategy
from src.services.exceptions import BackupError
from src.services.logging_service import logging_service

logger = logging_service.get_logger(__name__)


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


class BackupRestoreService:
    def __init__(self, metadata_store, ensure_local_backup_file, create_backup_fn):
        self.metadata_store = metadata_store
        self._ensure_local_backup_file = ensure_local_backup_file
        # Bound to BackupCreationService.create_backup by the facade, so
        # pre-restore safety backups reuse the exact same creation path.
        self._create_backup_fn = create_backup_fn

    def _decrypt_for_prepare(
        self,
        backup_id: str,
        metadata: dict[str, Any],
        working_path: str,
        decompressed: bool,
        passphrase: str | None,
        suffix: str,
    ) -> str:
        """Decrypt working_path in place (to a sibling file) if the backup is
        encrypted. Returns the path callers should read prompt/dump data from.
        Cleans up the pre-decrypt working_path on both success and failure.
        """
        if not passphrase:
            raise BackupError(
                "Passphrase required for encrypted backup", http_status=400
            )
        from src.services.backup_encryption_service import BackupEncryptionService

        enc_service = BackupEncryptionService()
        with get_db_session() as session:
            backup_record = session.query(Backup).filter_by(id=backup_id).first()
            salt = (
                backup_record.encryption_salt
                if backup_record
                else metadata.get("encryption_salt")
            )
            nonce = (
                backup_record.encryption_nonce
                if backup_record
                else metadata.get("encryption_nonce")
            )
        if not salt or not nonce:
            raise BackupError(
                "Encrypted backup missing salt/nonce",
                context={"backup_id": backup_id},
            )

        decrypted_path = working_path + suffix
        shutil.copy2(working_path, decrypted_path)
        try:
            enc_service.decrypt_file(decrypted_path, passphrase, salt, nonce)
        except ValueError as exc:
            if os.path.exists(decrypted_path):
                os.remove(decrypted_path)
            if decompressed and os.path.exists(working_path):
                os.remove(working_path)
            raise BackupError(
                "Decryption failed: wrong passphrase or corrupt data",
                context={"backup_id": backup_id},
                http_status=400,
            ) from exc
        if decompressed and os.path.exists(working_path):
            os.remove(working_path)
        return decrypted_path

    def restore_backup(
        self,
        backup_id: str,
        created_by: str | None,
        get_current_user,
        passphrase: str | None = None,
    ) -> bool:
        try:
            metadata = self.metadata_store.get_backup_info(backup_id)
            if not metadata:
                raise BackupError(
                    "Backup not found",
                    context={"backup_id": backup_id},
                    http_status=404,
                )

            backup_type = metadata.get("backup_type")
            backup_path = self._ensure_local_backup_file(backup_id, metadata)

            decompressed_path = _maybe_decompress(backup_path)
            if decompressed_path != backup_path:
                backup_path = decompressed_path

            is_encrypted = metadata.get("is_encrypted", False)
            decrypted_path = None
            if is_encrypted:
                decrypted_path = self._decrypt_for_prepare(
                    backup_id,
                    metadata,
                    backup_path,
                    decompressed_path != metadata.get("storage_path"),
                    passphrase,
                    ".decrypted",
                )
                backup_path = decrypted_path

            try:
                timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")[:21]
                logger.info(
                    "Creating pre-restore backup",
                    extra={"event": "backup.restore.pre_backup"},
                )
                pre_restore_backup = self._create_backup_fn(
                    f"pre_restore_{timestamp}",
                    created_by=created_by,
                )
                if not pre_restore_backup:
                    logger.warning(
                        "Could not create pre-restore backup",
                        extra={"event": "backup.restore.warning"},
                    )

                if backup_type == "pg_dump":
                    success = PostgresDumpStrategy().restore(backup_id, backup_path)
                elif backup_type == "sqlite_copy":
                    success = SqliteDumpStrategy().restore(backup_id, backup_path)
                else:
                    raise BackupError(
                        f"Unsupported backup type: {backup_type}",
                        context={"backup_id": backup_id, "backup_type": backup_type},
                    )
            finally:
                if decrypted_path and os.path.exists(decrypted_path):
                    os.remove(decrypted_path)
                if decompressed_path != metadata.get("storage_path") and os.path.exists(
                    decompressed_path
                ):
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
                    performed_by=created_by or get_current_user(),
                )
            else:
                audit_service.log(
                    operation="backup.restore",
                    outcome="failure",
                    backup_id=backup_id,
                    performed_by=created_by or get_current_user(),
                )

            return success

        except BackupError as exc:
            from src.services.backup_audit_service import BackupAuditService

            BackupAuditService().log(
                operation="backup.restore",
                outcome="failure",
                backup_id=backup_id,
                performed_by=created_by or get_current_user(),
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
                performed_by=created_by or get_current_user(),
                detail={"error": str(exc)},
            )
            raise BackupError(
                "Failed to restore backup.", context={"backup_id": backup_id}
            ) from exc

    def selective_restore(
        self,
        backup_id: str,
        prompt_ids: list,
        created_by: str | None,
        get_current_user,
        extract_prompts_fn,
        passphrase: str | None = None,
    ) -> dict[str, Any]:
        from src.services.backup_audit_service import BackupAuditService

        audit_service = BackupAuditService()

        try:
            metadata = self.metadata_store.get_backup_info(backup_id)
            if not metadata:
                raise BackupError(
                    "Backup not found",
                    context={"backup_id": backup_id},
                    http_status=404,
                )

            pre_restore_id = self._create_backup_fn(
                custom_name=f"pre_selective_restore_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
                created_by=created_by,
            )

            backup_path = self._ensure_local_backup_file(backup_id, metadata)
            is_encrypted = metadata.get("is_encrypted", False)
            working_path = _maybe_decompress(backup_path)
            decompressed = working_path != backup_path

            if is_encrypted:
                working_path = self._decrypt_for_prepare(
                    backup_id,
                    metadata,
                    working_path,
                    decompressed,
                    passphrase,
                    ".selective_decrypted",
                )
                decompressed = True

            try:
                backup_prompts = extract_prompts_fn(
                    working_path, metadata.get("backup_type", "sqlite_copy")
                )
            finally:
                if (
                    decompressed
                    and os.path.exists(working_path)
                    and working_path != backup_path
                ):
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
                performed_by=created_by or get_current_user(),
                detail={"prompt_ids": prompt_ids, "restored_count": restored_count},
            )

            return {
                "restored": True,
                "pre_restore_backup_id": pre_restore_id,
                "count": restored_count,
            }

        except BackupError as exc:
            audit_service.log(
                operation="backup.selective_restore",
                outcome="failure",
                backup_id=backup_id,
                performed_by=created_by or get_current_user(),
                detail={"error": str(exc)},
            )
            raise
        except Exception as exc:
            logger.error(
                "Failed to selectively restore backup",
                extra={
                    "event": "backup.selective_restore.failure",
                    "resource_id": backup_id,
                },
                exc_info=exc,
            )
            audit_service.log(
                operation="backup.selective_restore",
                outcome="failure",
                backup_id=backup_id,
                performed_by=created_by or get_current_user(),
                detail={"error": str(exc)},
            )
            raise BackupError(
                "Failed to selectively restore backup.",
                context={"backup_id": backup_id},
            ) from exc
