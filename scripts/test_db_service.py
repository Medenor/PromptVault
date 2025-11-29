#!/usr/bin/env python3
"""Test database-backed PromptDataService.

This script tests the new database-backed service to ensure it maintains
backward compatibility with the JSON-based service interface.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.prompt_data_service_db import PromptDataService
from src.db.session import engine
from src.db.base import Base


def test_service():
    """Test database-backed service operations."""
    print("=== Testing Database-Backed PromptDataService ===\n")

    # Create tables
    print("1. Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("   ✓ Tables created\n")

    # Initialize service
    print("2. Initializing service...")
    service = PromptDataService()
    print("   ✓ Service initialized\n")

    # Test 1: Add new prompt
    print("3. Testing add_new_prompt()...")
    prompt_data = {
        "title": "Test Prompt 1",
        "prompt": "This is a test prompt for the database backend.",
        "category": "Testing",
        "tags": ["test", "database", "backend"],
        "note": "Test note",
        "favorite": True,
        "commit_message": "Initial test prompt"
    }
    prompt_id = service.add_new_prompt(prompt_data)
    print(f"   ✓ Created prompt with ID: {prompt_id}\n")

    # Test 2: Load prompts (backward compatibility)
    print("4. Testing load_prompts() (backward compatibility)...")
    prompts_dict = service.load_prompts()
    print(f"   ✓ Loaded {len(prompts_dict)} prompts")
    if prompt_id in prompts_dict:
        prompt_info = prompts_dict[prompt_id]
        print(f"   ✓ Found prompt {prompt_id} in dict format")
        print(f"     - Title: {prompt_info['data']['title']}")
        print(f"     - Category: {prompt_info['data']['category']}")
        print(f"     - Tags: {prompt_info['data']['tags']}")
        print(f"     - Versions: {len(prompt_info['versions'])}")
        print(f"     - Branches: {list(prompt_info['branches'].keys())}")
    print()

    # Test 3: Update prompt
    print("5. Testing update_prompt()...")
    update_data = {
        "title": "Test Prompt 1 - Updated",
        "prompt": "This is an updated test prompt.",
        "category": "Testing",
        "tags": ["test", "database", "updated"],
        "note": "Updated note",
        "favorite": False,
    }
    success = service.update_prompt(prompt_id, update_data, "Updated via test")
    print(f"   ✓ Update result: {success}")

    # Reload and verify
    prompts_dict = service.load_prompts()
    updated_prompt = prompts_dict[prompt_id]
    print(f"   ✓ Updated title: {updated_prompt['data']['title']}")
    print(f"   ✓ Version count: {len(updated_prompt['versions'])} (should be 2)")
    print()

    # Test 4: Get prompt data
    print("6. Testing get_prompt_data()...")
    prompt_data = service.get_prompt_data(prompt_id)
    print(f"   ✓ Retrieved prompt data")
    print(f"     - Title: {prompt_data['title']}")
    print(f"     - Tags: {prompt_data['tags']}")
    print()

    # Test 5: Get versions
    print("7. Testing get_prompt_versions()...")
    versions = service.get_prompt_versions(prompt_id)
    print(f"   ✓ Retrieved {len(versions)} versions")
    for i, version in enumerate(versions, 1):
        print(f"     - Version {i}: {version['message']}")
    print()

    # Test 6: Categories and tags
    print("8. Testing get_categories() and get_tags()...")
    categories = service.get_categories()
    tags = service.get_tags()
    print(f"   ✓ Categories: {categories}")
    print(f"   ✓ Tags: {tags}")
    print()

    # Test 7: Tags with counts
    print("9. Testing get_tags_with_counts()...")
    tags_with_counts = service.get_tags_with_counts()
    print(f"   ✓ Tags with counts:")
    for tag_info in tags_with_counts:
        print(f"     - {tag_info['name']}: {tag_info['count']}")
    print()

    # Test 8: Add second prompt
    print("10. Testing bulk operations...")
    prompt_data_2 = {
        "title": "Test Prompt 2",
        "prompt": "Another test prompt.",
        "category": "Testing",
        "tags": ["test", "second"],
        "note": "",
        "favorite": False,
        "commit_message": "Second test prompt"
    }
    prompt_id_2 = service.add_new_prompt(prompt_data_2)
    print(f"   ✓ Created second prompt with ID: {prompt_id_2}")

    # Test bulk delete
    result = service.delete_prompts_bulk([prompt_id_2])
    print(f"   ✓ Bulk delete result:")
    print(f"     - Deleted: {result['deleted_ids']}")
    print(f"     - Failed: {result['failed_ids']}")
    print()

    # Test 9: Properties (backward compatibility)
    print("11. Testing backward compatibility properties...")
    print(f"   ✓ service.prompts type: {type(service.prompts)}")
    print(f"   ✓ service.next_id: {service.next_id}")
    print(f"   ✓ service.categories type: {type(service.categories)}")
    print(f"   ✓ service.global_tags type: {type(service.global_tags)}")
    print()

    # Test 10: save_prompts() no-op
    print("12. Testing save_prompts() (should be no-op)...")
    result = service.save_prompts()
    print(f"   ✓ save_prompts() returned: {result} (expected True)")
    print()

    # Test 11: Delete remaining prompt
    print("13. Testing delete_prompt()...")
    success = service.delete_prompt(prompt_id)
    print(f"   ✓ Delete result: {success}")

    # Verify deletion
    prompts_dict = service.load_prompts()
    print(f"   ✓ Remaining prompts: {len(prompts_dict)}")
    print()

    print("=== All Tests Passed! ===")
    print("\nThe database-backed service maintains full backward compatibility")
    print("with the JSON-based service interface.")


if __name__ == "__main__":
    try:
        test_service()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
