# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Preview what a restore would change, and extract prompt rows from a
backup file without touching the live database."""

import os
import shutil
from typing import Any

from src.db.models import Backup
from src.db.models.prompt import Prompt
from src.db.session import get_db_session
from src.services.backup_restore_service import _maybe_decompress
from src.services.exceptions import BackupError
from src.services.logging_service import logging_service

logger = logging_service.get_logger(__name__)


def extract_prompts_from_backup(backup_path: str, backup_type: str) -> list:
    """Extract prompt records from a backup file."""
    if backup_type == "sqlite_copy":
        import sqlite3

        try:
            conn = sqlite3.connect(backup_path)
            cursor = conn.execute(
                "SELECT id, title, prompt, note, favorite, category_id, semantic_version FROM prompts"
            )
            prompts = []
            for row in cursor:
                prompts.append(
                    {
                        "id": row[0],
                        "title": row[1],
                        "prompt": row[2],
                        "note": row[3],
                        "favorite": bool(row[4]),
                        "category_id": row[5],
                        "semantic_version": row[6],
                    }
                )
            conn.close()
            return prompts
        except Exception as exc:
            logger.error(
                "Failed to read prompts from backup file",
                extra={
                    "event": "backup.extract_prompts.failure",
                    "resource_id": backup_path,
                },
                exc_info=exc,
            )
            raise BackupError(
                "Backup file is unreadable or corrupt",
                context={"backup_path": backup_path},
            ) from exc
    return []


class BackupDiffService:
    def __init__(self, metadata_store, ensure_local_backup_file):
        self.metadata_store = metadata_store
        self._ensure_local_backup_file = ensure_local_backup_file

    def compute_restore_diff(
        self, backup_id: str, passphrase: str | None = None
    ) -> dict[str, Any]:
        metadata = self.metadata_store.get_backup_info(backup_id)
        if not metadata:
            raise BackupError(
                "Backup not found", context={"backup_id": backup_id}, http_status=404
            )

        backup_path = self._ensure_local_backup_file(backup_id, metadata)

        working_path = _maybe_decompress(backup_path)
        decompressed = working_path != backup_path

        is_encrypted = metadata.get("is_encrypted", False)

        if is_encrypted:
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
                raise BackupError("Encrypted backup missing salt/nonce")
            decrypted_path = working_path + ".preview_decrypted"
            shutil.copy2(working_path, decrypted_path)
            try:
                enc_service.decrypt_file(decrypted_path, passphrase, salt, nonce)
            except ValueError as e:
                if os.path.exists(decrypted_path):
                    os.remove(decrypted_path)
                if decompressed and os.path.exists(working_path):
                    os.remove(working_path)
                raise BackupError("Decryption failed", http_status=400) from e
            if decompressed and os.path.exists(working_path):
                os.remove(working_path)
            working_path = decrypted_path
            decompressed = True  # ensure cleanup below removes this temp file too

        try:
            backup_prompts = extract_prompts_from_backup(
                working_path, metadata.get("backup_type", "sqlite_copy")
            )
        finally:
            if (
                decompressed
                and os.path.exists(working_path)
                and working_path != backup_path
            ):
                os.remove(working_path)

        with get_db_session() as session:
            current_prompts = session.query(Prompt).all()
            current_map = {
                p.id: {"title": p.title, "prompt": p.prompt} for p in current_prompts
            }

        backup_map = {p["id"]: p for p in backup_prompts if "id" in p}

        added = []
        updated = []
        deleted = []

        for pid, bp in backup_map.items():
            if pid not in current_map:
                added.append(
                    {
                        "id": pid,
                        "title": bp.get("title", ""),
                        "prompt": bp.get("prompt", "")[:200],
                    }
                )
            else:
                cp = current_map[pid]
                if cp["title"] != bp.get("title") or cp["prompt"] != bp.get("prompt"):
                    updated.append(
                        {
                            "id": pid,
                            "title": bp.get("title", ""),
                            "before": {
                                "title": cp["title"],
                                "prompt": cp["prompt"][:200],
                            },
                            "after": {
                                "title": bp.get("title", ""),
                                "prompt": bp.get("prompt", "")[:200],
                            },
                        }
                    )

        for pid, cp in current_map.items():
            if pid not in backup_map:
                deleted.append({"id": pid, "title": cp["title"]})

        return {
            "backup_id": backup_id,
            "summary": {
                "added": len(added),
                "updated": len(updated),
                "deleted": len(deleted),
            },
            "changes": {"added": added, "updated": updated, "deleted": deleted},
        }
