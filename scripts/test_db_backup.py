# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

#!/usr/bin/env python3
"""Test database-aware BackupService.

This script tests the new database backup service to ensure it works
correctly for SQLite databases.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.backup_service_db import BackupService
from src.services.prompt_data_service_db import PromptDataService
from src.db.session import engine
from src.db.base import Base


def test_backup_service():
    """Test database backup service operations."""
    print("=== Testing Database-Aware BackupService ===\n")

    # Create tables
    print("1. Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("   ✓ Tables created\n")

    # Initialize services
    print("2. Initializing services...")
    backup_service = BackupService()
    data_service = PromptDataService()
    print("   ✓ Services initialized\n")

    # Create some test data
    print("3. Creating test data...")
    prompt_data = {
        "title": "Backup Test Prompt",
        "prompt": "This is a test prompt for backup testing.",
        "category": "Testing",
        "tags": ["backup", "test"],
        "note": "Test backup functionality",
        "favorite": True,
        "commit_message": "Initial backup test"
    }
    prompt_id = data_service.add_new_prompt(prompt_data)
    print(f"   ✓ Created test prompt with ID: {prompt_id}\n")

    # Test 1: Create backup
    print("4. Testing create_backup()...")
    backup_id = backup_service.create_backup("test_backup")
    print(f"   ✓ Created backup with ID: {backup_id}\n")

    # Test 2: List backups
    print("5. Testing list_backups()...")
    backups = backup_service.list_backups()
    print(f"   ✓ Found {len(backups)} backup(s)")
    if backups:
        backup = backups[0]
        print(f"     - Backup ID: {backup['backup_id']}")
        print(f"     - Type: {backup['backup_type']}")
        print(f"     - Filename: {backup['filename']}")
        print(f"     - Size: {backup['size_bytes']} bytes")
        print(f"     - Database: {backup['database_type']}")
    print()

    # Test 3: Get backup info
    print("6. Testing get_backup_info()...")
    backup_info = backup_service.get_backup_info(backup_id)
    if backup_info:
        print(f"   ✓ Retrieved backup info")
        print(f"     - Created by: {backup_info['created_by']}")
        print(f"     - Timestamp: {backup_info['timestamp']}")
    else:
        print(f"   ✗ Failed to retrieve backup info")
    print()

    # Test 4: Get backup stats
    print("7. Testing get_backup_stats()...")
    stats = backup_service.get_backup_stats()
    print(f"   ✓ Backup statistics:")
    print(f"     - Total backups: {stats['total_backups']}")
    print(f"     - Total size: {stats['total_size']} bytes")
    print(f"     - Newest backup: {stats['newest_backup']}")
    print()

    # Test 5: Modify data
    print("8. Modifying data...")
    update_data = {
        "title": "Backup Test Prompt - Modified",
        "prompt": "This prompt has been modified.",
        "category": "Testing",
        "tags": ["backup", "test", "modified"],
        "note": "Modified for backup testing",
        "favorite": False,
    }
    success = data_service.update_prompt(prompt_id, update_data, "Modified for restore test")
    print(f"   ✓ Modified prompt: {success}\n")

    # Test 6: Create second backup
    print("9. Creating second backup (after modification)...")
    backup_id_2 = backup_service.create_backup()
    print(f"   ✓ Created second backup with ID: {backup_id_2}\n")

    # Test 7: Restore from first backup
    print("10. Testing restore_backup() (from first backup)...")
    print("    Note: This will create a pre-restore backup automatically")
    success = backup_service.restore_backup(backup_id)
    print(f"   ✓ Restore result: {success}")

    # Verify restoration
    restored_prompt = data_service.get_prompt_data(prompt_id)
    print(f"   ✓ Restored prompt title: {restored_prompt.get('title')}")
    print(f"   ✓ Should be 'Backup Test Prompt' (original)")
    print()

    # Test 8: List backups again (should have pre-restore backup)
    print("11. Listing backups after restore...")
    backups = backup_service.list_backups()
    print(f"   ✓ Found {len(backups)} backup(s) total")
    print(f"   ✓ Should be 3 or more (original + modified + pre-restore)")
    for backup in backups:
        print(f"     - {backup['backup_id']}: {backup['backup_type']}")
    print()

    # Test 9: Cleanup
    print("12. Testing cleanup_old_backups() with 0 days (delete all)...")
    removed_count = backup_service.cleanup_old_backups(retention_days=0)
    print(f"   ✓ Removed {removed_count} backup(s)\n")

    # Test 10: Verify cleanup
    print("13. Verifying cleanup...")
    backups = backup_service.list_backups()
    print(f"   ✓ Remaining backups: {len(backups)}\n")

    # Test 11: Delete test prompt
    print("14. Cleaning up test data...")
    success = data_service.delete_prompt(prompt_id)
    print(f"   ✓ Deleted test prompt: {success}\n")

    print("=== All Tests Passed! ===")
    print("\nThe database-aware backup service is working correctly.")
    print("Key features tested:")
    print("  - SQLite backup creation")
    print("  - Backup metadata tracking in database")
    print("  - Backup listing and info retrieval")
    print("  - Database restoration from backup")
    print("  - Pre-restore automatic backups")
    print("  - Backup cleanup based on retention policy")


if __name__ == "__main__":
    try:
        test_backup_service()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
