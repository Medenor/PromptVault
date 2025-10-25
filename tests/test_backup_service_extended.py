"""
Extended unit tests for BackupService with edge cases.
Complements existing test_backup_system.py with additional scenarios.
"""

import pytest
import json
import os
import gzip
from pathlib import Path
from datetime import datetime, timedelta

from src.services.backup_service import BackupService


class TestBackupEdgeCases:
    """Test edge cases and error scenarios for backup creation."""

    def test_backup_nonexistent_data_file(self, temp_data_dir):
        """Test creating backup when data file doesn't exist."""
        backup_service = BackupService(temp_data_dir)

        # Should handle gracefully
        backup_id = backup_service.create_backup("test_nonexistent")

        # Might return None or handle it differently
        # Check that it doesn't crash
        assert backup_id is None or isinstance(backup_id, str)

    def test_backup_with_very_long_description(self, temp_data_dir, populated_data_service):
        """Test creating backup with very long description."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        long_description = "A" * 1000  # Very long description
        backup_id = backup_service.create_backup(long_description)

        assert backup_id is not None

        backups = backup_service.list_backups()
        assert any(b['backup_id'] == backup_id for b in backups)

    def test_backup_with_special_characters_in_description(self, temp_data_dir, populated_data_service):
        """Test creating backup with special characters in description."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        special_desc = "Backup: <>&\"' 你好 🚀"
        backup_id = backup_service.create_backup(special_desc)

        assert backup_id is not None

    def test_multiple_rapid_backups(self, temp_data_dir, populated_data_service):
        """Test creating multiple backups in rapid succession."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        backup_ids = []
        for i in range(10):
            backup_id = backup_service.create_backup(f"Rapid backup {i}")
            backup_ids.append(backup_id)

        # All backups should be created
        assert len(backup_ids) == 10
        assert len(set(backup_ids)) == 10  # All unique

        backups = backup_service.list_backups()
        assert len(backups) == 10

    def test_backup_with_empty_data_file(self, temp_data_dir):
        """Test creating backup with empty data file."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        data_file.write_text("{}", encoding='utf-8')

        backup_service = BackupService(temp_data_dir)

        backup_id = backup_service.create_backup("empty_data")

        # Should handle empty file
        assert backup_id is None or isinstance(backup_id, str)


class TestBackupRestoration:
    """Test backup restoration with various scenarios."""

    def test_restore_nonexistent_backup(self, temp_data_dir):
        """Test restoring a backup that doesn't exist."""
        backup_service = BackupService(temp_data_dir)

        result = backup_service.restore_backup("nonexistent_backup_id")

        assert result is False

    def test_restore_corrupted_backup_file(self, temp_data_dir, populated_data_service):
        """Test restoring a corrupted backup file."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        # Create a backup
        backup_id = backup_service.create_backup("test")

        # Corrupt the backup file
        backup_path = Path(backup_service.backups_dir) / f"{backup_id}.json"
        backup_path.write_text("{invalid json}", encoding='utf-8')

        # Try to restore
        result = backup_service.restore_backup(backup_id)

        # Should fail gracefully
        assert result is False

    def test_restore_with_invalid_metadata(self, temp_data_dir, populated_data_service):
        """Test restoring backup with invalid metadata."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        # Create a backup
        backup_id = backup_service.create_backup("test")

        # Corrupt the metadata file
        metadata_path = Path(backup_service.backups_dir) / f"{backup_id}_metadata.json"
        metadata_path.write_text("{}", encoding='utf-8')

        # Try to restore
        result = backup_service.restore_backup(backup_id)

        # Might still work if main backup file is valid
        assert isinstance(result, bool)

    def test_restore_creates_pre_restore_backup(self, temp_data_dir, populated_data_service):
        """Test that restore creates a pre-restore safety backup."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        # Create a backup
        backup_id = backup_service.create_backup("original")

        # Modify data
        populated_data_service.add_new_prompt({"title": "New", "prompt": "New"})
        populated_data_service.save_prompts()

        initial_backup_count = len(backup_service.list_backups())

        # Restore
        backup_service.restore_backup(backup_id)

        # Should have created a pre-restore backup
        final_backup_count = len(backup_service.list_backups())
        assert final_backup_count > initial_backup_count

    def test_restore_maintains_data_integrity(self, temp_data_dir, populated_data_service):
        """Test that restored data matches original backup data."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        # Save original data
        with open(data_file, 'r', encoding='utf-8') as f:
            original_data = json.load(f)

        backup_service = BackupService(temp_data_dir)

        # Create backup
        backup_id = backup_service.create_backup("original")

        # Modify data
        populated_data_service.add_new_prompt({"title": "Modified", "prompt": "Modified"})
        populated_data_service.save_prompts()

        # Restore
        backup_service.restore_backup(backup_id)

        # Load restored data
        with open(data_file, 'r', encoding='utf-8') as f:
            restored_data = json.load(f)

        # Should match original
        assert restored_data == original_data


class TestBackupCleanup:
    """Test backup cleanup functionality."""

    def test_cleanup_with_no_backups(self, temp_data_dir):
        """Test cleanup when no backups exist."""
        backup_service = BackupService(temp_data_dir)

        removed_count = backup_service.cleanup_old_backups(retention_days=30)

        assert removed_count == 0

    def test_cleanup_doesnt_remove_recent_backups(self, temp_data_dir, populated_data_service):
        """Test that cleanup doesn't remove recent backups."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        # Create recent backup
        backup_id = backup_service.create_backup("recent")

        # Cleanup with large retention
        removed_count = backup_service.cleanup_old_backups(retention_days=30)

        # Should not remove recent backup
        assert removed_count == 0

        backups = backup_service.list_backups()
        assert len(backups) == 1

    def test_cleanup_invalid_retention_days(self, temp_data_dir, populated_data_service):
        """Test cleanup with invalid retention days."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        backup_service.create_backup("test")

        # Try with negative retention days
        removed_count = backup_service.cleanup_old_backups(retention_days=-1)

        # Should handle gracefully
        assert isinstance(removed_count, int)


class TestBackupCompression:
    """Test backup compression functionality."""

    def test_compress_already_compressed_backup(self, temp_data_dir, populated_data_service):
        """Test compressing a backup that's already compressed."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        backup_id = backup_service.create_backup("test")

        # Compress once
        compressed_count1 = backup_service.compress_old_backups(days_threshold=0)
        assert compressed_count1 == 1

        # Try to compress again
        compressed_count2 = backup_service.compress_old_backups(days_threshold=0)
        assert compressed_count2 == 0  # Already compressed

    def test_compress_with_no_backups(self, temp_data_dir):
        """Test compression when no backups exist."""
        backup_service = BackupService(temp_data_dir)

        compressed_count = backup_service.compress_old_backups(days_threshold=0)

        assert compressed_count == 0

    def test_compress_removes_original_file(self, temp_data_dir, populated_data_service):
        """Test that compression removes the original uncompressed file."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        backup_id = backup_service.create_backup("test")

        original_path = Path(backup_service.backups_dir) / f"{backup_id}.json"
        compressed_path = Path(backup_service.backups_dir) / f"{backup_id}.json.gz"

        # Verify original exists
        assert original_path.exists()

        # Compress
        backup_service.compress_old_backups(days_threshold=0)

        # Original should be removed, compressed should exist
        assert not original_path.exists()
        assert compressed_path.exists()

    def test_compressed_file_is_valid_gzip(self, temp_data_dir, populated_data_service):
        """Test that compressed backup is valid gzip format."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        backup_id = backup_service.create_backup("test")

        backup_service.compress_old_backups(days_threshold=0)

        compressed_path = Path(backup_service.backups_dir) / f"{backup_id}.json.gz"

        # Try to decompress and verify
        with gzip.open(compressed_path, 'rt', encoding='utf-8') as f:
            decompressed_data = json.load(f)

        # Should be valid JSON
        assert isinstance(decompressed_data, dict)


class TestBackupStatistics:
    """Test backup statistics functionality."""

    def test_stats_with_no_backups(self, temp_data_dir):
        """Test statistics when no backups exist."""
        backup_service = BackupService(temp_data_dir)

        stats = backup_service.get_backup_stats()

        assert stats['total_backups'] == 0
        assert stats['total_size'] == 0
        assert stats['newest_backup'] is None
        assert stats['oldest_backup'] is None

    def test_stats_with_single_backup(self, temp_data_dir, populated_data_service):
        """Test statistics with a single backup."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        backup_id = backup_service.create_backup("test")

        stats = backup_service.get_backup_stats()

        assert stats['total_backups'] == 1
        assert stats['total_size'] > 0
        assert stats['newest_backup'] is not None
        assert stats['oldest_backup'] is not None

    def test_stats_with_mixed_compressed_uncompressed(self, temp_data_dir, populated_data_service):
        """Test statistics with mix of compressed and uncompressed backups."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        # Create backups
        backup_service.create_backup("backup1")
        backup_service.create_backup("backup2")
        backup_service.create_backup("backup3")

        # Compress old ones (with threshold 0, all will be compressed)
        backup_service.compress_old_backups(days_threshold=0)

        stats = backup_service.get_backup_stats()

        assert stats['total_backups'] == 3
        assert stats['compressed_backups'] == 3


class TestBackupInfo:
    """Test getting backup information."""

    def test_get_backup_info_existing(self, temp_data_dir, populated_data_service):
        """Test getting info for an existing backup."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        backup_id = backup_service.create_backup("test")

        info = backup_service.get_backup_info(backup_id)

        assert info is not None
        assert info['backup_id'] == backup_id
        assert 'timestamp' in info
        assert 'size_bytes' in info

    def test_get_backup_info_nonexistent(self, temp_data_dir):
        """Test getting info for a nonexistent backup."""
        backup_service = BackupService(temp_data_dir)

        info = backup_service.get_backup_info("nonexistent")

        assert info is None


class TestBackupDeletion:
    """Test backup deletion functionality."""

    def test_delete_existing_backup(self, temp_data_dir, populated_data_service):
        """Test deleting an existing backup."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        backup_id = backup_service.create_backup("test")

        initial_count = len(backup_service.list_backups())

        # Delete
        result = backup_service.delete_backup(backup_id)

        assert result is True

        final_count = len(backup_service.list_backups())
        assert final_count == initial_count - 1

    def test_delete_nonexistent_backup(self, temp_data_dir):
        """Test deleting a backup that doesn't exist."""
        backup_service = BackupService(temp_data_dir)

        result = backup_service.delete_backup("nonexistent")

        assert result is False

    def test_delete_removes_metadata_file(self, temp_data_dir, populated_data_service):
        """Test that deleting a backup also removes its metadata file."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        backup_id = backup_service.create_backup("test")

        backup_path = Path(backup_service.backups_dir) / f"{backup_id}.json"
        metadata_path = Path(backup_service.backups_dir) / f"{backup_id}_metadata.json"

        # Verify files exist
        assert backup_path.exists() or Path(str(backup_path) + ".gz").exists()
        assert metadata_path.exists()

        # Delete
        backup_service.delete_backup(backup_id)

        # Both should be removed
        assert not backup_path.exists()
        assert not metadata_path.exists()


class TestBackupListOrdering:
    """Test backup listing and ordering."""

    def test_list_backups_ordered_by_timestamp(self, temp_data_dir, populated_data_service):
        """Test that backups are listed in chronological order."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        # Create multiple backups
        for i in range(5):
            backup_service.create_backup(f"backup_{i}")

        backups = backup_service.list_backups()

        # Check that they're ordered by timestamp (newest first or oldest first)
        timestamps = [b['timestamp'] for b in backups]
        assert timestamps == sorted(timestamps) or timestamps == sorted(timestamps, reverse=True)

    def test_list_backups_includes_all_metadata(self, temp_data_dir, populated_data_service):
        """Test that list_backups includes all metadata fields."""
        data_file = Path(temp_data_dir) / "prompts_data.json"
        populated_data_service.data_file = str(data_file)
        populated_data_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        backup_service.create_backup("test")

        backups = backup_service.list_backups()

        assert len(backups) == 1
        backup = backups[0]

        # Check required fields
        assert 'backup_id' in backup
        assert 'filename' in backup
        assert 'timestamp' in backup
        assert 'size_bytes' in backup
