#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Seed Pagination Test Prompts Script

Populates the database with a configurable number of sample prompts,
spread across several categories and tags, for manually exercising
pagination / "Load More" / page-size behavior (see
specs/005-pagination-lazy-loading/).

Usage:
    python scripts/seed_pagination_test_prompts.py [count]

    count: Number of prompts to create (default: 150)

Notes:
    - Uses the same PromptDataService.add_new_prompt() path the app uses,
      so category/tag get-or-create and versioning behave exactly as in
      normal usage (this is not a raw-SQL insert).
    - Prompts are attributed to a "system" user (auto-created if missing),
      matching the existing migrate_json_to_db.py convention.
    - Roughly 1 in 5 seeded prompts is marked as a favorite, and titles
      include a mix of a few repeating keywords so the search/filter UI
      also has something interesting to page through.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.services.prompt_data_service_db import PromptDataService

CATEGORIES = ["Marketing", "Engineering", "Support", "Research"]
KEYWORDS = ["email", "onboarding", "release notes", "bug triage", "roadmap"]
TAGS_POOL = [
    ["draft"],
    ["reviewed"],
    ["draft", "urgent"],
    ["template"],
    [],
]


def seed(count: int) -> None:
    service = PromptDataService()
    created = 0

    for i in range(count):
        category = CATEGORIES[i % len(CATEGORIES)]
        keyword = KEYWORDS[i % len(KEYWORDS)]
        tags = TAGS_POOL[i % len(TAGS_POOL)]

        data = {
            "title": f"[{category}] {keyword.title()} prompt #{i + 1}",
            "prompt": (
                f"This is seeded test prompt #{i + 1} for pagination testing. "
                f"Category: {category}. Keyword: {keyword}."
            ),
            "note": "Seed data for pagination/lazy-loading manual testing",
            "category": category,
            "tags": tags,
            "favorite": (i % 5 == 0),
        }
        service.add_new_prompt(data, user_id=None)
        created += 1

    print(f"Seeded {created} prompts across {len(CATEGORIES)} categories.")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    seed(count)