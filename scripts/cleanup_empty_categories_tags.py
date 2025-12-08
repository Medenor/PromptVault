#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Clean up empty category and tag names from database.

This script removes categories and tags with empty or whitespace-only names.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.db.session import get_db_session
from src.db.repositories.category_repository import CategoryRepository
from src.db.repositories.tag_repository import TagRepository


def cleanup_empty_categories() -> int:
    """Remove categories with empty or whitespace-only names.

    Returns:
        Number of categories deleted
    """
    deleted_count = 0

    try:
        with get_db_session() as session:
            category_repo = CategoryRepository(session)
            
            # Get all categories
            all_categories = category_repo.get_all()
            
            # Filter empty ones
            empty_categories = [
                cat for cat in all_categories 
                if not cat.name or not cat.name.strip()
            ]
            
            if not empty_categories:
                print("✅ No empty categories found.")
                return 0
            
            print(f"Found {len(empty_categories)} empty categories:")
            for cat in empty_categories:
                print(f"  - ID: {cat.id}, Name: '{cat.name}'")
            
            # Delete them
            for cat in empty_categories:
                session.delete(cat)
                deleted_count += 1
            
            session.commit()
            print(f"✅ Successfully deleted {deleted_count} empty categories.")
            return deleted_count

    except Exception as e:
        print(f"❌ Error deleting categories: {e}")
        return -1


def cleanup_empty_tags() -> int:
    """Remove tags with empty or whitespace-only names.

    Returns:
        Number of tags deleted
    """
    deleted_count = 0

    try:
        with get_db_session() as session:
            tag_repo = TagRepository(session)
            
            # Get all tags
            all_tags = tag_repo.get_all()
            
            # Filter empty ones
            empty_tags = [
                tag for tag in all_tags 
                if not tag.name or not tag.name.strip()
            ]
            
            if not empty_tags:
                print("✅ No empty tags found.")
                return 0
            
            print(f"Found {len(empty_tags)} empty tags:")
            for tag in empty_tags:
                print(f"  - ID: {tag.id}, Name: '{tag.name}'")
            
            # Delete them
            for tag in empty_tags:
                session.delete(tag)
                deleted_count += 1
            
            session.commit()
            print(f"✅ Successfully deleted {deleted_count} empty tags.")
            return deleted_count

    except Exception as e:
        print(f"❌ Error deleting tags: {e}")
        return -1


def main() -> int:
    """Run all cleanup operations.

    Returns:
        0 on success, 1 on failure
    """
    print("=" * 60)
    print("Cleaning up empty categories and tags...")
    print("=" * 60 + "\n")
    
    cat_result = cleanup_empty_categories()
    print()
    tag_result = cleanup_empty_tags()
    
    print("\n" + "=" * 60)
    if cat_result >= 0 and tag_result >= 0:
        total_deleted = cat_result + tag_result
        print(f"✅ Cleanup completed! Total items deleted: {total_deleted}")
        print("=" * 60)
        return 0
    else:
        print("❌ Cleanup failed!")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    result = main()
    sys.exit(result)
