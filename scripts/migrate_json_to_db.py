# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

#!/usr/bin/env python3
"""Migrate PromptVault data from JSON file storage to database.

This script migrates existing JSON-based prompt data to the new database schema
while preserving all data including:
- Prompt IDs (critical for backward compatibility)
- Version history with complete snapshots
- Categories and tags
- Branch information
- User attribution

Usage:
    # Preview migration without writing
    python scripts/migrate_json_to_db.py --source data/prompts_data.json --dry-run

    # Execute actual migration
    python scripts/migrate_json_to_db.py --source data/prompts_data.json

    # Migration with custom database URL
    DATABASE_URL=postgresql://user:pass@host/db python scripts/migrate_json_to_db.py --source data/prompts_data.json
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
import uuid

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# Import database components
from src.db import get_db_session, db_settings
from src.db.models import (
    User, Category, Tag, Prompt, PromptVersion,
    PromptBranch, prompt_tags
)


class MigrationStats:
    """Track migration statistics."""

    def __init__(self):
        self.prompts_migrated = 0
        self.versions_migrated = 0
        self.categories_created = 0
        self.tags_created = 0
        self.branches_created = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)

    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)

    def print_summary(self):
        """Print migration summary."""
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)
        print(f"Prompts migrated:     {self.prompts_migrated}")
        print(f"Versions migrated:    {self.versions_migrated}")
        print(f"Categories created:   {self.categories_created}")
        print(f"Tags created:         {self.tags_created}")
        print(f"Branches created:     {self.branches_created}")

        if self.warnings:
            print(f"\n⚠️  Warnings: {len(self.warnings)}")
            for warning in self.warnings[:10]:  # Show first 10
                print(f"   - {warning}")
            if len(self.warnings) > 10:
                print(f"   ... and {len(self.warnings) - 10} more")

        if self.errors:
            print(f"\n❌ Errors: {len(self.errors)}")
            for error in self.errors[:10]:  # Show first 10
                print(f"   - {error}")
            if len(self.errors) > 10:
                print(f"   ... and {len(self.errors) - 10} more")
        else:
            print("\n✅ Migration completed successfully with no errors")

        print("=" * 70)


def load_json_data(json_path: str) -> Dict[str, Any]:
    """Load and parse JSON data file.

    Args:
        json_path: Path to JSON file

    Returns:
        Parsed JSON data as dictionary

    Raises:
        FileNotFoundError: If JSON file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    print(f"Loading JSON data from: {json_path}")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"✅ JSON loaded: {len(data.get('prompts', {}))} prompts found")
    return data


def create_default_user(session: Session) -> User:
    """Create or get the default 'system' user.

    Args:
        session: Database session

    Returns:
        User object for system user
    """
    # Check if system user already exists
    user = session.query(User).filter_by(username="system").first()

    if not user:
        user = User(
            id=str(uuid.uuid4()),
            username="system",
            display_name="System User",
            email=None,
            role="system"
        )
        session.add(user)
        session.flush()
        print("✅ Created default 'system' user")
    else:
        print("✅ Using existing 'system' user")

    return user


def migrate_categories(
    session: Session,
    json_data: Dict[str, Any],
    stats: MigrationStats
) -> Dict[str, Category]:
    """Migrate categories from JSON to database.

    Args:
        session: Database session
        json_data: Source JSON data
        stats: Migration statistics

    Returns:
        Dictionary mapping category names to Category objects
    """
    print("\nMigrating categories...")
    category_map = {}

    # Extract unique categories from prompts
    categories_set: Set[str] = set()
    for prompt_data in json_data.get("prompts", {}).values():
        category_name = prompt_data.get("data", {}).get("category")
        if category_name and category_name.strip():
            categories_set.add(category_name.strip())

    # Also check global categories if present
    if "categories" in json_data:
        categories_set.update(json_data["categories"])

    # Create category objects
    for cat_name in sorted(categories_set):
        # Check if already exists
        cat = session.query(Category).filter_by(name=cat_name).first()

        if not cat:
            cat = Category(name=cat_name)
            session.add(cat)
            session.flush()
            stats.categories_created += 1

        category_map[cat_name] = cat

    print(f"✅ Categories migrated: {len(category_map)} total")
    return category_map


def migrate_tags(
    session: Session,
    json_data: Dict[str, Any],
    stats: MigrationStats
) -> Dict[str, Tag]:
    """Migrate tags from JSON to database.

    Args:
        session: Database session
        json_data: Source JSON data
        stats: Migration statistics

    Returns:
        Dictionary mapping tag names to Tag objects
    """
    print("\nMigrating tags...")
    tag_map = {}

    # Extract unique tags from prompts
    tags_set: Set[str] = set()
    for prompt_data in json_data.get("prompts", {}).values():
        tags_list = prompt_data.get("data", {}).get("tags", [])
        for tag in tags_list:
            if tag and tag.strip():
                tags_set.add(tag.strip())

    # Also check global tags if present
    if "global_tags" in json_data:
        tags_set.update(json_data["global_tags"])

    # Create tag objects
    for tag_name in sorted(tags_set):
        # Check if already exists
        tag = session.query(Tag).filter_by(name=tag_name).first()

        if not tag:
            tag = Tag(name=tag_name)
            session.add(tag)
            session.flush()
            stats.tags_created += 1

        tag_map[tag_name] = tag

    print(f"✅ Tags migrated: {len(tag_map)} total")
    return tag_map


def migrate_prompts_and_versions(
    session: Session,
    json_data: Dict[str, Any],
    default_user: User,
    category_map: Dict[str, Category],
    tag_map: Dict[str, Tag],
    stats: MigrationStats
):
    """Migrate prompts and their version history.

    Args:
        session: Database session
        json_data: Source JSON data
        default_user: Default user for attribution
        category_map: Category name to object mapping
        tag_map: Tag name to object mapping
        stats: Migration statistics
    """
    print("\nMigrating prompts and versions...")

    prompts_data = json_data.get("prompts", {})

    for prompt_id_str, prompt_data in prompts_data.items():
        try:
            prompt_id = int(prompt_id_str)
            data = prompt_data.get("data", {})

            # Get category
            category_name = data.get("category", "").strip()
            category = category_map.get(category_name) if category_name else None

            # Create prompt (with preserved ID)
            prompt = Prompt(
                id=prompt_id,
                title=data.get("title", "Untitled"),
                prompt=data.get("prompt", ""),
                category=category,
                note=data.get("note", ""),
                favorite=data.get("favorite", False),
                user=default_user
            )

            session.add(prompt)
            session.flush()

            # Add tags (many-to-many)
            for tag_name in data.get("tags", []):
                tag_name = tag_name.strip()
                if tag_name in tag_map:
                    prompt.tags.append(tag_map[tag_name])

            stats.prompts_migrated += 1

            # Migrate versions
            versions_data = prompt_data.get("versions", [])
            for idx, version_data in enumerate(versions_data):
                try:
                    version = PromptVersion(
                        prompt_id=prompt_id,
                        version_id=version_data.get("version_id", str(uuid.uuid4())),
                        version_number=idx + 1,
                        title=version_data.get("data", {}).get("title"),
                        prompt=version_data.get("data", {}).get("prompt"),
                        category_id=category.id if category else None,
                        note=version_data.get("data", {}).get("note"),
                        tags=json.dumps(version_data.get("data", {}).get("tags", [])),
                        favorite=version_data.get("data", {}).get("favorite", False),
                        author=version_data.get("author", "system"),
                        message=version_data.get("message", "Initial version"),
                        created_at=datetime.fromisoformat(
                            version_data.get("timestamp", datetime.utcnow().isoformat()).replace("Z", "+00:00")
                        ),
                        parent_version_id=version_data.get("parents", [None])[0] if version_data.get("parents") else None
                    )

                    session.add(version)
                    stats.versions_migrated += 1

                except Exception as e:
                    error_msg = f"Prompt {prompt_id}, version {idx + 1}: {str(e)}"
                    stats.add_error(error_msg)

            # Migrate branches
            branches_data = prompt_data.get("branches", {})
            for branch_name, version_id in branches_data.items():
                try:
                    branch = PromptBranch(
                        prompt_id=prompt_id,
                        branch_name=branch_name,
                        current_version_id=version_id
                    )
                    session.add(branch)
                    stats.branches_created += 1

                except Exception as e:
                    error_msg = f"Prompt {prompt_id}, branch '{branch_name}': {str(e)}"
                    stats.add_error(error_msg)

            session.flush()

        except Exception as e:
            error_msg = f"Prompt {prompt_id_str}: {str(e)}"
            stats.add_error(error_msg)
            # Continue with next prompt
            continue

    print(f"✅ Prompts migrated: {stats.prompts_migrated}")
    print(f"✅ Versions migrated: {stats.versions_migrated}")
    print(f"✅ Branches migrated: {stats.branches_created}")


def migrate_data(
    json_path: str,
    dry_run: bool = False
) -> MigrationStats:
    """Execute the migration from JSON to database.

    Args:
        json_path: Path to source JSON file
        dry_run: If True, don't commit changes

    Returns:
        Migration statistics

    Raises:
        Exception: If migration fails
    """
    stats = MigrationStats()

    # Load JSON data
    try:
        json_data = load_json_data(json_path)
    except Exception as e:
        print(f"❌ Failed to load JSON: {e}")
        raise

    # Perform migration in a transaction
    print(f"\nDatabase: {db_settings.database_type} at {db_settings.DATABASE_URL}")
    print(f"Mode: {'DRY-RUN (no changes will be saved)' if dry_run else 'LIVE MIGRATION'}")

    with get_db_session() as session:
        try:
            # Step 1: Create default user
            print("\n" + "=" * 70)
            print("STEP 1: Creating default user")
            print("=" * 70)
            default_user = create_default_user(session)

            # Step 2: Migrate categories
            print("\n" + "=" * 70)
            print("STEP 2: Migrating categories")
            print("=" * 70)
            category_map = migrate_categories(session, json_data, stats)

            # Step 3: Migrate tags
            print("\n" + "=" * 70)
            print("STEP 3: Migrating tags")
            print("=" * 70)
            tag_map = migrate_tags(session, json_data, stats)

            # Step 4: Migrate prompts and versions
            print("\n" + "=" * 70)
            print("STEP 4: Migrating prompts and versions")
            print("=" * 70)
            migrate_prompts_and_versions(
                session, json_data, default_user,
                category_map, tag_map, stats
            )

            if dry_run:
                print("\n⚠️  DRY-RUN mode: Rolling back all changes")
                session.rollback()
            else:
                print("\n✅ Committing changes to database")
                session.commit()

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            session.rollback()
            raise

    return stats


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate PromptVault data from JSON to database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to source JSON file (e.g., data/prompts_data.json)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without writing to database"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("PROMPTVAULT JSON TO DATABASE MIGRATION")
    print("=" * 70)
    print(f"Source file: {args.source}")
    print(f"Dry-run: {args.dry_run}")

    try:
        stats = migrate_data(args.source, args.dry_run)
        stats.print_summary()

        # Exit with error code if there were errors
        if stats.errors:
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\n❌ Invalid JSON: {e}")
        sys.exit(1)
    except SQLAlchemyError as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
