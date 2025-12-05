#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Cleanup script for removing unused categories and tags from PromptVault database.

This script identifies and deletes categories and tags that are not referenced by any prompts.
It's safe to run multiple times - only unused items will be deleted.

Usage:
    python scripts/cleanup_unused_categories_tags.py

The script will:
1. Display all categories and tags with their prompt counts
2. Identify unused categories and tags (0 prompts)
3. Ask for confirmation before deleting
4. Delete unused categories and tags and report results
"""

import sys
import os
from typing import List, Tuple, Union

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.session import get_db_session
from src.db.repositories.category_repository import CategoryRepository
from src.db.repositories.tag_repository import TagRepository
from src.db.models import Category, Tag


def get_unused_categories(repo: CategoryRepository) -> List[Tuple[Category, int]]:
    """Get all categories with zero prompts.

    Args:
        repo: CategoryRepository instance

    Returns:
        List of tuples (Category, prompt_count) where prompt_count == 0
    """
    categories_with_counts = repo.list_all_with_counts()
    unused = [(cat, count) for cat, count in categories_with_counts if count == 0]
    return unused


def get_unused_tags(repo: TagRepository) -> List[Tuple[Tag, int]]:
    """Get all tags with zero prompts.

    Args:
        repo: TagRepository instance

    Returns:
        List of tuples (Tag, prompt_count) where prompt_count == 0
    """
    tags_with_counts = repo.list_all_with_counts()
    unused = [(tag, count) for tag, count in tags_with_counts if count == 0]
    return unused


def display_category_stats(categories: List[Tuple[Category, int]]) -> None:
    """Display statistics about all categories.

    Args:
        categories: List of tuples (Category, prompt_count)
    """
    if not categories:
        print("No categories found in database.")
        return

    print("\n" + "=" * 80)
    print("CATEGORY STATISTICS")
    print("=" * 80)
    print(f"{'ID':<5} {'Name':<30} {'Prompts':<10} {'Status':<15}")
    print("-" * 80)

    total_categories = len(categories)
    unused_count = 0

    for category, count in categories:
        status = "UNUSED ⚠️" if count == 0 else "IN USE ✓"
        if count == 0:
            unused_count += 1
        print(f"{category.id:<5} {category.name:<30} {count:<10} {status:<15}")

    print("-" * 80)
    print(f"Total: {total_categories} categories | Unused: {unused_count} | In Use: {total_categories - unused_count}")
    print("=" * 80 + "\n")


def display_tag_stats(tags: List[Tuple[Tag, int]]) -> None:
    """Display statistics about all tags.

    Args:
        tags: List of tuples (Tag, prompt_count)
    """
    if not tags:
        print("No tags found in database.")
        return

    print("\n" + "=" * 80)
    print("TAG STATISTICS")
    print("=" * 80)
    print(f"{'ID':<5} {'Name':<30} {'Prompts':<10} {'Status':<15}")
    print("-" * 80)

    total_tags = len(tags)
    unused_count = 0

    for tag, count in tags:
        status = "UNUSED ⚠️" if count == 0 else "IN USE ✓"
        if count == 0:
            unused_count += 1
        print(f"{tag.id:<5} {tag.name:<30} {count:<10} {status:<15}")

    print("-" * 80)
    print(f"Total: {total_tags} tags | Unused: {unused_count} | In Use: {total_tags - unused_count}")
    print("=" * 80 + "\n")


def confirm_deletion(
    unused_categories: List[Tuple[Category, int]],
    unused_tags: List[Tuple[Tag, int]]
) -> bool:
    """Ask user to confirm deletion of unused categories and tags.

    Args:
        unused_categories: List of unused categories
        unused_tags: List of unused tags

    Returns:
        True if user confirms, False otherwise
    """
    if not unused_categories and not unused_tags:
        print("No unused categories or tags to delete.")
        return False

    print(f"\n⚠️  DELETION CONFIRMATION")

    if unused_categories:
        print(f"About to delete {len(unused_categories)} unused categor{'y' if len(unused_categories) == 1 else 'ies'}:")
        for category, _ in unused_categories:
            print(f"  • {category.name}")

    if unused_tags:
        print(f"\nAbout to delete {len(unused_tags)} unused tag{'s' if len(unused_tags) != 1 else ''}:")
        for tag, _ in unused_tags:
            print(f"  • {tag.name}")

    print()
    response = input("Type 'DELETE' to confirm, or press Enter to cancel: ").strip()

    return response.upper() == "DELETE"


def cleanup_unused_items() -> Tuple[int, int]:
    """Delete all unused categories and tags from database.

    Returns:
        Tuple of (categories_deleted, tags_deleted)
    """
    print("\n🧹 PromptVault Database Cleanup Script\n")

    try:
        with get_db_session() as session:
            # Initialize repositories
            category_repo = CategoryRepository(session)
            tag_repo = TagRepository(session)

            # Get all categories and tags with counts
            all_categories = category_repo.list_all_with_counts()
            all_tags = tag_repo.list_all_with_counts()

            # Display statistics
            display_category_stats(all_categories)
            display_tag_stats(all_tags)

            # Find unused items
            unused_categories = get_unused_categories(category_repo)
            unused_tags = get_unused_tags(tag_repo)

            # Check if there's anything to delete
            if not unused_categories and not unused_tags:
                print("✅ No unused categories or tags found. Database is clean!\n")
                return 0, 0

            # Ask for confirmation
            if not confirm_deletion(unused_categories, unused_tags):
                print("❌ Cleanup cancelled by user.\n")
                return 0, 0

            # Delete unused categories
            deleted_categories = 0
            deleted_tags = 0
            failed_count = 0

            if unused_categories:
                print(f"\n🗑️  Deleting {len(unused_categories)} unused categor{'y' if len(unused_categories) == 1 else 'ies'}...\n")
                for category, _ in unused_categories:
                    try:
                        success = category_repo.delete_if_unused(category.id)
                        if success:
                            print(f"  ✅ Deleted category: {category.name}")
                            deleted_categories += 1
                        else:
                            print(f"  ⚠️  Failed to delete category: {category.name} (may have prompts)")
                            failed_count += 1
                    except Exception as e:
                        print(f"  ❌ Error deleting category {category.name}: {e}")
                        failed_count += 1

            # Delete unused tags
            if unused_tags:
                print(f"\n🗑️  Deleting {len(unused_tags)} unused tag{'s' if len(unused_tags) != 1 else ''}...\n")
                for tag, _ in unused_tags:
                    try:
                        success = tag_repo.delete_if_unused(tag.id)
                        if success:
                            print(f"  ✅ Deleted tag: {tag.name}")
                            deleted_tags += 1
                        else:
                            print(f"  ⚠️  Failed to delete tag: {tag.name} (may have prompts)")
                            failed_count += 1
                    except Exception as e:
                        print(f"  ❌ Error deleting tag {tag.name}: {e}")
                        failed_count += 1

            # Commit the session
            session.commit()

            # Print results
            print("\n" + "=" * 80)
            print("CLEANUP RESULTS")
            print("=" * 80)
            print(f"✅ Categories deleted: {deleted_categories}")
            print(f"✅ Tags deleted: {deleted_tags}")
            print(f"❌ Failed operations: {failed_count}")
            print(f"📊 Total deleted: {deleted_categories + deleted_tags}")
            print("=" * 80 + "\n")

            return deleted_categories, deleted_tags

    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}\n")
        raise


def main() -> None:
    """Main entry point."""
    try:
        deleted_cats, deleted_tags = cleanup_unused_items()
        sys.exit(0 if (deleted_cats + deleted_tags) >= 0 else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Cleanup interrupted by user.\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
