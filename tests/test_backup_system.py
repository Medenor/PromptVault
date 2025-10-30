#!/usr/bin/env python3
"""
Test script for the DATA BACKUP SYSTEM functionality.
This script tests backup creation, restoration, cleanup, and compression features.
"""

import os
import sys
import json
import shutil
import tempfile
from datetime import datetime

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.services.backup_service import BackupService


def create_test_data():
    """Create test data file for backup testing."""
    test_data = {
        "next_id": 3,
        "prompts": {
            "1": {
                "data": {
                    "title": "Test Prompt 1",
                    "prompt": "This is a test prompt for backup testing.",
                    "category": "Test",
                    "tags": ["test", "backup"],
                    "favorite": True,
                },
                "versions": [],
                "branches": {},
            },
            "2": {
                "data": {
                    "title": "Test Prompt 2",
                    "prompt": "Another test prompt for backup verification.",
                    "category": "Test",
                    "tags": ["test"],
                    "favorite": False,
                },
                "versions": [],
                "branches": {},
            },
        },
        "categories": ["Test", "Work"],
        "global_tags": ["test", "backup", "important"],
    }

    return test_data


def test_backup_creation():
    """Test backup creation functionality."""
    print("Testing backup creation...")

    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test data file
        data_file = os.path.join(temp_dir, "prompts_data.json")
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(create_test_data(), f, indent=2)

        # Initialize backup service
        backup_service = BackupService(temp_dir)

        # Test backup creation
        backup_id = backup_service.create_backup("test_backup")
        assert backup_id is not None, "Backup creation failed"
        print(f"✓ Backup created successfully: {backup_id}")

        # Verify backup files exist
        backup_filename = f"{backup_id}.json"
        backup_path = os.path.join(backup_service.backups_dir, backup_filename)
        metadata_path = backup_path.replace(".json", "_metadata.json")

        assert os.path.exists(backup_path), "Backup file not found"
        assert os.path.exists(metadata_path), "Backup metadata file not found"
        print("✓ Backup files created successfully")

        # Test listing backups
        backups = backup_service.list_backups()
        assert len(backups) == 1, "Backup not found in list"
        assert backups[0]["backup_id"] == backup_id, "Backup ID mismatch"
        print("✓ Backup listing works correctly")

        return True


def test_backup_restoration():
    """Test backup restoration functionality."""
    print("Testing backup restoration...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create original data
        original_data = create_test_data()
        data_file = os.path.join(temp_dir, "prompts_data.json")
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(original_data, f, indent=2)

        backup_service = BackupService(temp_dir)

        # Create backup
        backup_id = backup_service.create_backup("restore_test")
        assert backup_id is not None, "Backup creation failed"

        # Modify original data
        modified_data = original_data.copy()
        modified_data["prompts"]["1"]["data"]["title"] = "Modified Title"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(modified_data, f, indent=2)

        # Restore backup
        success = backup_service.restore_backup(backup_id)
        assert success, "Backup restoration failed"
        print("✓ Backup restored successfully")

        # Verify data was restored
        with open(data_file, "r", encoding="utf-8") as f:
            restored_data = json.load(f)

        assert (
            restored_data["prompts"]["1"]["data"]["title"] == "Test Prompt 1"
        ), "Data not properly restored"
        print("✓ Restored data matches original")

        return True


def test_backup_cleanup():
    """Test backup cleanup functionality."""
    print("Testing backup cleanup...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test data file
        data_file = os.path.join(temp_dir, "prompts_data.json")
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(create_test_data(), f, indent=2)

        backup_service = BackupService(temp_dir)

        # Create multiple backups with different timestamps
        backup_ids = []
        for i in range(5):
            backup_id = backup_service.create_backup(f"cleanup_test_{i}")
            assert backup_id is not None, f"Backup {i} creation failed"
            backup_ids.append(backup_id)

        # Verify all backups exist
        backups = backup_service.list_backups()
        assert len(backups) == 5, "Not all backups created"
        print("✓ Multiple backups created successfully")

        # Test cleanup (keep only last 2 days - should remove all since they're recent)
        removed_count = backup_service.cleanup_old_backups(retention_days=2)
        print(f"✓ Cleanup completed: {removed_count} backups removed")

        # Test cleanup with very short retention (should remove all)
        removed_count = backup_service.cleanup_old_backups(retention_days=0)
        remaining_backups = backup_service.list_backups()
        assert len(remaining_backups) == 0, "Cleanup did not remove all old backups"
        print("✓ All old backups cleaned up successfully")

        return True


def test_backup_compression():
    """Test backup compression functionality."""
    print("Testing backup compression...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test data file
        data_file = os.path.join(temp_dir, "prompts_data.json")
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(create_test_data(), f, indent=2)

        backup_service = BackupService(temp_dir)

        # Create a backup
        backup_id = backup_service.create_backup("compression_test")
        assert backup_id is not None, "Backup creation failed"

        # Test compression
        compressed_count = backup_service.compress_old_backups(days_threshold=0)
        assert compressed_count == 1, "Compression failed or count incorrect"
        print("✓ Backup compressed successfully")

        # Verify compressed file exists
        backup_filename = f"{backup_id}.json"
        compressed_path = os.path.join(
            backup_service.backups_dir, f"{backup_filename}.gz"
        )
        assert os.path.exists(compressed_path), "Compressed backup file not found"

        # Verify original file is removed
        original_path = os.path.join(backup_service.backups_dir, backup_filename)
        assert not os.path.exists(
            original_path
        ), "Original backup file should be removed after compression"
        print("✓ Original backup file removed after compression")

        return True


def test_backup_stats():
    """Test backup statistics functionality."""
    print("Testing backup statistics...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test data file
        data_file = os.path.join(temp_dir, "prompts_data.json")
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(create_test_data(), f, indent=2)

        backup_service = BackupService(temp_dir)

        # Test stats with no backups
        stats = backup_service.get_backup_stats()
        assert stats["total_backups"] == 0, "Stats should show 0 backups initially"
        print("✓ Empty backup stats work correctly")

        # Create a backup and test stats
        backup_id = backup_service.create_backup("stats_test")
        assert backup_id is not None, "Backup creation failed"

        stats = backup_service.get_backup_stats()
        assert stats["total_backups"] == 1, "Stats should show 1 backup"
        assert stats["total_size"] > 0, "Stats should show backup size"
        assert (
            stats["newest_backup"] is not None
        ), "Stats should show newest backup timestamp"
        print("✓ Backup statistics work correctly")

        return True


def run_all_tests():
    """Run all backup system tests."""
    print("Starting DATA BACKUP SYSTEM tests...\n")

    tests = [
        test_backup_creation,
        test_backup_restoration,
        test_backup_cleanup,
        test_backup_compression,
        test_backup_stats,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✅ {test.__name__} PASSED\n")
            else:
                failed += 1
                print(f"❌ {test.__name__} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} FAILED with exception: {e}\n")

    print(f"Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! Backup system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
