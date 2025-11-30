# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Additional coverage-focused tests for BackupService edge cases.
"""

import json
import os
import gzip
from pathlib import Path

import pytest

from src.services.backup_service import BackupService
from src.services.exceptions import BackupError


SAMPLE_DATA = {
    "next_id": 2,
    "prompts": {
        "1": {
            "data": {
                "title": "Sample",
                "prompt": "Content",
                "category": "General",
                "tags": ["tag"],
                "favorite": False,
                "note": "",
            },
            "versions": [],
            "branches": {},
        }
    },
    "categories": ["General"],
    "global_tags": ["tag"],
}


def _write_sample_data(temp_dir: str) -> Path:
    data_path = Path(temp_dir) / "prompts_data.json"
    data_path.write_text(json.dumps(SAMPLE_DATA), encoding="utf-8")
    return data_path


class TestCreateBackupBranches:
    """Exercises create_backup branches that were uncovered."""

    def test_create_backup_invalid_custom_name_falls_back_to_timestamp(
        self, temp_data_dir: str
    ) -> None:
        _write_sample_data(temp_data_dir)
        backup_service = BackupService(temp_data_dir)

        backup_id = backup_service.create_backup("   ")

        assert backup_id is not None
        assert backup_id.startswith("backup_")

    def test_create_backup_without_custom_name(self, temp_data_dir: str) -> None:
        _write_sample_data(temp_data_dir)
        backup_service = BackupService(temp_data_dir)

        backup_id = backup_service.create_backup()

        assert backup_id is not None
        assert backup_id.startswith("backup_")

    def test_create_backup_handles_copy_exception(
        self, temp_data_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_sample_data(temp_data_dir)
        backup_service = BackupService(temp_data_dir)

        def raise_copy_error(*_args, **_kwargs) -> None:
            raise OSError("copy failure")

        monkeypatch.setattr("shutil.copy2", raise_copy_error)

        with pytest.raises(BackupError):
            backup_service.create_backup("failing")


class TestListBackupsBranches:
    """Covers list_backups error paths."""

    def test_list_backups_handles_metadata_decode_error(
        self, temp_data_dir: str
    ) -> None:
        backups_dir = Path(temp_data_dir) / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = backups_dir / "broken_metadata.json"
        metadata_path.write_text("{invalid json}", encoding="utf-8")

        backup_service = BackupService(temp_data_dir)

        assert backup_service.list_backups() == []

    def test_list_backups_handles_generic_exception(
        self, temp_data_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backup_service = BackupService(temp_data_dir)

        def raise_list_error(_path: str) -> None:
            raise RuntimeError("listdir failure")

        monkeypatch.setattr("os.listdir", raise_list_error)

        with pytest.raises(BackupError):
            backup_service.list_backups()


class TestRestoreBackupBranches:
    """Ensures restore_backup covers remaining branches."""

    def test_restore_backup_warns_when_pre_restore_backup_fails(
        self, temp_data_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        data_path = _write_sample_data(temp_data_dir)
        backup_service = BackupService(temp_data_dir)
        backup_id = backup_service.create_backup("original")

        data_path.write_text(
            json.dumps(
                {"next_id": 1, "prompts": {}, "categories": [], "global_tags": []}
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(
            backup_service, "create_backup", lambda *_args, **_kwargs: None
        )

        assert backup_service.restore_backup(backup_id) is True

        restored = json.loads(data_path.read_text(encoding="utf-8"))
        assert restored["prompts"]

    def test_restore_backup_from_compressed_file(self, temp_data_dir: str) -> None:
        data_path = _write_sample_data(temp_data_dir)
        backup_service = BackupService(temp_data_dir)
        backup_id = backup_service.create_backup("compress-me")

        original_path = Path(backup_service.backups_dir) / f"{backup_id}.json"
        compressed_path = Path(backup_service.backups_dir) / f"{backup_id}.json.gz"
        with open(original_path, "rb") as src, gzip.open(compressed_path, "wb") as dst:
            dst.write(src.read())
        original_path.unlink()

        data_path.write_text(
            json.dumps(
                {"next_id": 0, "prompts": {}, "categories": [], "global_tags": []}
            ),
            encoding="utf-8",
        )

        assert backup_service.restore_backup(backup_id) is True
        assert json.loads(data_path.read_text(encoding="utf-8"))["prompts"]

    def test_restore_backup_handles_generic_exception(
        self, temp_data_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_sample_data(temp_data_dir)
        backup_service = BackupService(temp_data_dir)

        monkeypatch.setattr(
            backup_service,
            "_resolve_backup_path",
            lambda _backup_id: (_ for _ in ()).throw(RuntimeError("resolve failure")),
        )

        with pytest.raises(BackupError):
            backup_service.restore_backup("missing")


class TestCleanupOldBackups:
    """Targets cleanup_old_backups exception handling."""

    def test_cleanup_handles_oserror_during_removal(
        self, temp_data_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_sample_data(temp_data_dir)
        backup_service = BackupService(temp_data_dir)
        backup_id = backup_service.create_backup("old-backup")
        metadata_path = Path(backup_service.backups_dir) / f"{backup_id}_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["timestamp"] = "2000-01-01T00:00:00Z"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        def raise_remove_error(_path: str) -> None:
            raise OSError("cannot remove")

        monkeypatch.setattr("os.remove", raise_remove_error)

        assert backup_service.cleanup_old_backups(retention_days=1) == 0

    def test_cleanup_handles_generic_exception(
        self, temp_data_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backup_service = BackupService(temp_data_dir)

        monkeypatch.setattr(
            backup_service,
            "list_backups",
            lambda: (_ for _ in ()).throw(RuntimeError("listing failed")),
        )

        with pytest.raises(BackupError):
            backup_service.cleanup_old_backups()


class TestCompressOldBackups:
    """Ensures compress_old_backups error branches are covered."""

    def test_compress_handles_compression_exception(
        self, temp_data_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_sample_data(temp_data_dir)
        backup_service = BackupService(temp_data_dir)
        backup_id = backup_service.create_backup("to-compress")

        metadata_path = Path(backup_service.backups_dir) / f"{backup_id}_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["timestamp"] = "2000-01-01T00:00:00Z"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        def raise_gzip_error(*_args, **_kwargs) -> None:
            raise OSError("gzip failed")

        monkeypatch.setattr("gzip.open", raise_gzip_error)

        assert backup_service.compress_old_backups(days_threshold=1) == 0

    def test_compress_handles_generic_exception(
        self, temp_data_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backup_service = BackupService(temp_data_dir)

        monkeypatch.setattr(
            backup_service,
            "list_backups",
            lambda: (_ for _ in ()).throw(RuntimeError("listing failed")),
        )

        with pytest.raises(BackupError):
            backup_service.compress_old_backups()


class TestDeleteAndUtilityHelpers:
    """Covers remaining helper branches."""

    def test_delete_backup_handles_exception(
        self, temp_data_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backup_service = BackupService(temp_data_dir)

        monkeypatch.setattr(
            backup_service,
            "get_backup_info",
            lambda _backup_id: (_ for _ in ()).throw(RuntimeError("info failure")),
        )

        with pytest.raises(BackupError):
            backup_service.delete_backup("any")

    def test_get_current_user_fallback(
        self, temp_data_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backup_service = BackupService(temp_data_dir)

        monkeypatch.setattr(
            "getpass.getuser", lambda: (_ for _ in ()).throw(OSError("no user"))
        )

        assert backup_service._get_current_user() == "unknown"

    def test_sanitize_backup_name_empty(self, temp_data_dir: str) -> None:
        backup_service = BackupService(temp_data_dir)

        assert backup_service._sanitize_backup_name("") == ""

    def test_metadata_path_from_none(self, temp_data_dir: str) -> None:
        backup_service = BackupService(temp_data_dir)

        assert backup_service._metadata_path_from_filename(None) is None

    def test_metadata_path_from_gz(self, temp_data_dir: str) -> None:
        backup_service = BackupService(temp_data_dir)

        expected = Path(backup_service.backups_dir) / "entry_metadata.json"
        assert backup_service._metadata_path_from_filename("entry.json.gz") == str(
            expected
        )

    def test_metadata_path_from_unknown_extension(self, temp_data_dir: str) -> None:
        backup_service = BackupService(temp_data_dir)

        expected = Path(backup_service.backups_dir) / "archive_metadata.json"
        assert backup_service._metadata_path_from_filename("archive") == str(expected)

    def test_resolve_backup_path_finds_gz(self, temp_data_dir: str) -> None:
        backup_service = BackupService(temp_data_dir)
        backups_dir = Path(backup_service.backups_dir)
        backups_dir.mkdir(parents=True, exist_ok=True)

        target = backups_dir / "custom.json.gz"
        with gzip.open(target, "wt", encoding="utf-8") as handle:
            json.dump(SAMPLE_DATA, handle)

        assert backup_service._resolve_backup_path("custom") == str(target)

    def test_resolve_backup_path_uses_metadata_filename(
        self, temp_data_dir: str
    ) -> None:
        backup_service = BackupService(temp_data_dir)
        backups_dir = Path(backup_service.backups_dir)
        backups_dir.mkdir(parents=True, exist_ok=True)

        actual_path = backups_dir / "external.json"
        actual_path.write_text(json.dumps(SAMPLE_DATA), encoding="utf-8")

        metadata = {
            "backup_id": "external",
            "filename": "external.json",
            "timestamp": "2024-01-01T00:00:00Z",
            "size_bytes": len(actual_path.read_bytes()),
            "prompt_count": 1,
            "created_by": "tester",
            "data_file_modified": "2024-01-01T00:00:00Z",
            "compressed": False,
        }
        metadata_path = backups_dir / "external_metadata.json"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        assert backup_service._resolve_backup_path("external") == str(actual_path)

    def test_is_valid_backup_file_accepts_gz(self, temp_data_dir: str) -> None:
        backup_service = BackupService(temp_data_dir)
        target = Path(backup_service.backups_dir) / "valid.json.gz"
        with gzip.open(target, "wt", encoding="utf-8") as handle:
            json.dump(SAMPLE_DATA, handle)

        assert backup_service._is_valid_backup_file(str(target)) is True
