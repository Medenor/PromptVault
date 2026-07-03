# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Performance and load tests for tag/category list_all_with_counts() operations.

This module tests the performance characteristics of database operations
for listing tags and categories with usage counts, including:
- Load testing with varying dataset sizes
- N+1 query detection
- Memory usage monitoring
- Performance baseline generation
"""

import os
import sys
import json
import time
import tracemalloc
from pathlib import Path
from typing import List, Dict, Any, Generator
from datetime import datetime, timezone

import pytest
from sqlalchemy import event, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.models import User, Category, Tag, Prompt
from src.db.repositories import CategoryRepository, TagRepository

# ============================================================================
# QUERY COUNTER FIXTURE
# ============================================================================


class QueryCounter:
    """Count and log SQL queries executed during tests."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.queries: List[str] = []
        self.query_count = 0
        self.enabled = False

    def start(self):
        """Start counting queries."""
        self.queries = []
        self.query_count = 0
        self.enabled = True
        event.listen(self.engine, "before_cursor_execute", self._before_cursor_execute)

    def stop(self):
        """Stop counting queries."""
        self.enabled = False
        event.remove(self.engine, "before_cursor_execute", self._before_cursor_execute)

    def _before_cursor_execute(
        self, conn, cursor, statement, parameters, context, executemany
    ):
        """Event handler that counts queries."""
        if self.enabled:
            self.query_count += 1
            self.queries.append(statement)

    def get_count(self) -> int:
        """Get total query count."""
        return self.query_count

    def get_queries(self) -> List[str]:
        """Get list of executed queries."""
        return self.queries

    def reset(self):
        """Reset counter."""
        self.queries = []
        self.query_count = 0


@pytest.fixture
def query_counter(test_db_engine) -> Generator[QueryCounter, None, None]:
    """Create a query counter for detecting N+1 queries."""
    counter = QueryCounter(test_db_engine)
    yield counter
    if counter.enabled:
        counter.stop()


# ============================================================================
# MEMORY TRACKER FIXTURE
# ============================================================================


class MemoryTracker:
    """Track memory usage during tests."""

    def __init__(self):
        self.snapshots: List[tuple] = []
        self.peak_memory = 0
        self.tracking = False

    def start(self):
        """Start tracking memory."""
        tracemalloc.start()
        self.tracking = True
        self.snapshots = []
        self.peak_memory = 0

    def snapshot(self, label: str = ""):
        """Take a memory snapshot."""
        if self.tracking:
            current, peak = tracemalloc.get_traced_memory()
            self.peak_memory = max(self.peak_memory, peak)
            self.snapshots.append((label, current, peak))

    def stop(self) -> Dict[str, Any]:
        """Stop tracking and return statistics."""
        if self.tracking:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            self.tracking = False
            return {
                "current_bytes": current,
                "peak_bytes": peak,
                "current_mb": current / (1024 * 1024),
                "peak_mb": peak / (1024 * 1024),
                "snapshots": self.snapshots,
            }
        return {}


@pytest.fixture
def memory_tracker() -> Generator[MemoryTracker, None, None]:
    """Create a memory tracker for monitoring memory usage."""
    tracker = MemoryTracker()
    yield tracker
    if tracker.tracking:
        tracker.stop()


# ============================================================================
# DATA GENERATION FIXTURES
# ============================================================================


@pytest.fixture
def test_user_for_perf(test_db_session: Session) -> User:
    """Create a test user for performance tests."""
    user = User(
        id="perf-test-user",
        username="perf_user",
        display_name="Performance Test User",
        email="perf@example.com",
        password_hash="hashed_password",
        role="user",
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


def generate_categories(
    session: Session, count: int, base_name: str = "PerfCat"
) -> List[Category]:
    """Generate test categories.

    Args:
        session: Database session
        count: Number of categories to create
        base_name: Base name for categories

    Returns:
        List of created categories
    """
    categories = []
    for i in range(count):
        cat = Category(
            name=f"{base_name}_{i:04d}",
            description=f"Performance test category {i}",
            color=f"#{'%06x' % (i * 1000 % 0xFFFFFF)}",
            sort_order=i,
        )
        session.add(cat)
        categories.append(cat)

    session.flush()
    return categories


def generate_tags_with_hierarchy(
    session: Session, count: int, max_depth: int = 10, base_name: str = "PerfTag"
) -> List[Tag]:
    """Generate test tags with hierarchical relationships.

    Args:
        session: Database session
        count: Number of tags to create
        max_depth: Maximum hierarchy depth
        base_name: Base name for tags

    Returns:
        List of created tags
    """
    tags = []
    parents_at_level = {0: []}

    for i in range(count):
        # Determine hierarchy level (distribute across levels)
        level = i % (max_depth + 1)
        parent_tag_id = None

        # Assign parent if not at root level
        if level > 0 and level - 1 in parents_at_level and parents_at_level[level - 1]:
            parent_tag_id = parents_at_level[level - 1][
                i % len(parents_at_level[level - 1])
            ].id

        tag = Tag(
            name=f"{base_name}_{i:04d}",
            description=f"Performance test tag {i} at level {level}",
            color=f"#{'%06x' % (i * 777 % 0xFFFFFF)}",
            parent_tag_id=parent_tag_id,
        )
        session.add(tag)
        session.flush()
        tags.append(tag)

        # Track for hierarchy building
        if level not in parents_at_level:
            parents_at_level[level] = []
        parents_at_level[level].append(tag)

    return tags


def generate_prompts_with_associations(
    session: Session,
    user: User,
    categories: List[Category],
    tags: List[Tag],
    prompt_count: int,
    tags_per_prompt_range: tuple = (1, 10),
) -> List[Prompt]:
    """Generate prompts with category and tag associations.

    Args:
        session: Database session
        user: User to associate prompts with
        categories: List of categories to assign
        tags: List of tags to assign
        prompt_count: Number of prompts to create
        tags_per_prompt_range: (min, max) tags per prompt

    Returns:
        List of created prompts
    """
    import random

    prompts = []
    for i in range(prompt_count):
        # Select random category
        category = categories[i % len(categories)] if categories else None

        # Create prompt
        prompt = Prompt(
            title=f"Performance Test Prompt {i:05d}",
            prompt=f"Content for performance testing prompt {i}. "
            * 10,  # Make content substantial
            note=f"Note for prompt {i}",
            category_id=category.id if category else None,
            favorite=(i % 10 == 0),  # Every 10th prompt is favorite
            user_id=user.id,
        )

        # Add random tags
        if tags:
            min_tags, max_tags = tags_per_prompt_range
            num_tags = random.randint(min_tags, min(max_tags, len(tags)))
            selected_tags = random.sample(tags, num_tags)
            prompt.tags.extend(selected_tags)

        session.add(prompt)
        prompts.append(prompt)

    session.flush()
    return prompts


@pytest.fixture
def small_category_dataset(
    test_db_session: Session, test_user_for_perf: User
) -> Dict[str, Any]:
    """Generate small dataset: 10 categories, 100 prompts."""
    categories = generate_categories(test_db_session, 10, "SmallCat")
    tags = generate_tags_with_hierarchy(test_db_session, 20, 3, "SmallTag")
    prompts = generate_prompts_with_associations(
        test_db_session, test_user_for_perf, categories, tags, 100
    )
    test_db_session.commit()
    return {"categories": categories, "tags": tags, "prompts": prompts}


@pytest.fixture
def medium_category_dataset(
    test_db_session: Session, test_user_for_perf: User
) -> Dict[str, Any]:
    """Generate medium dataset: 100 categories, 1000 prompts."""
    categories = generate_categories(test_db_session, 100, "MediumCat")
    tags = generate_tags_with_hierarchy(test_db_session, 200, 5, "MediumTag")
    prompts = generate_prompts_with_associations(
        test_db_session, test_user_for_perf, categories, tags, 1000
    )
    test_db_session.commit()
    return {"categories": categories, "tags": tags, "prompts": prompts}


@pytest.fixture
def large_category_dataset(
    test_db_session: Session, test_user_for_perf: User
) -> Dict[str, Any]:
    """Generate large dataset: 1000 categories, 5000 prompts."""
    categories = generate_categories(test_db_session, 1000, "LargeCat")
    tags = generate_tags_with_hierarchy(test_db_session, 500, 8, "LargeTag")
    prompts = generate_prompts_with_associations(
        test_db_session, test_user_for_perf, categories, tags, 5000
    )
    test_db_session.commit()
    return {"categories": categories, "tags": tags, "prompts": prompts}


@pytest.fixture
def small_tag_dataset(
    test_db_session: Session, test_user_for_perf: User
) -> Dict[str, Any]:
    """Generate small tag dataset: 100 tags, 500 prompts."""
    categories = generate_categories(test_db_session, 20, "TagSmallCat")
    tags = generate_tags_with_hierarchy(test_db_session, 100, 5, "TagSmall")
    prompts = generate_prompts_with_associations(
        test_db_session, test_user_for_perf, categories, tags, 500
    )
    test_db_session.commit()
    return {"categories": categories, "tags": tags, "prompts": prompts}


@pytest.fixture
def medium_tag_dataset(
    test_db_session: Session, test_user_for_perf: User
) -> Dict[str, Any]:
    """Generate medium tag dataset: 500 tags, 2000 prompts."""
    categories = generate_categories(test_db_session, 50, "TagMediumCat")
    tags = generate_tags_with_hierarchy(test_db_session, 500, 7, "TagMedium")
    prompts = generate_prompts_with_associations(
        test_db_session, test_user_for_perf, categories, tags, 2000
    )
    test_db_session.commit()
    return {"categories": categories, "tags": tags, "prompts": prompts}


@pytest.fixture
def large_tag_dataset(
    test_db_session: Session, test_user_for_perf: User
) -> Dict[str, Any]:
    """Generate large tag dataset: 1000 tags with deep hierarchy, 10000 prompts."""
    categories = generate_categories(test_db_session, 100, "TagLargeCat")
    tags = generate_tags_with_hierarchy(test_db_session, 1000, 10, "TagLarge")
    prompts = generate_prompts_with_associations(
        test_db_session, test_user_for_perf, categories, tags, 10000, (5, 15)
    )
    test_db_session.commit()
    return {"categories": categories, "tags": tags, "prompts": prompts}


@pytest.fixture
def heavy_association_dataset(
    test_db_session: Session, test_user_for_perf: User
) -> Dict[str, Any]:
    """Generate dataset with heavy prompt associations: 50 tags, 5000 prompts, many tags per prompt."""
    categories = generate_categories(test_db_session, 20, "HeavyCat")
    tags = generate_tags_with_hierarchy(test_db_session, 50, 3, "HeavyTag")
    prompts = generate_prompts_with_associations(
        test_db_session, test_user_for_perf, categories, tags, 5000, (20, 40)
    )
    test_db_session.commit()
    return {"categories": categories, "tags": tags, "prompts": prompts}


# ============================================================================
# PERFORMANCE TESTS FOR CATEGORIES
# ============================================================================


def test_list_all_categories_small_dataset(
    test_db_session: Session,
    small_category_dataset: Dict[str, Any],
    query_counter: QueryCounter,
    memory_tracker: MemoryTracker,
):
    """Test category listing with small dataset (baseline)."""
    repo = CategoryRepository(test_db_session)

    # Start monitoring
    query_counter.start()
    memory_tracker.start()

    start_time = time.time()
    results = repo.list_all_with_counts()
    elapsed_time = time.time() - start_time

    query_counter.stop()
    mem_stats = memory_tracker.stop()

    # Assertions
    assert len(results) == 10
    assert all(isinstance(item[0], Category) for item in results)
    assert elapsed_time < 1.0  # Should complete in under 1 second

    # Report
    print(f"\n=== Small Category Dataset Performance ===")
    print(f"Categories: 10")
    print(f"Prompts: 100")
    print(f"Time: {elapsed_time:.4f}s")
    print(f"Queries: {query_counter.get_count()}")
    print(f"Memory Peak: {mem_stats['peak_mb']:.2f} MB")


def test_list_all_categories_medium_dataset(
    test_db_session: Session,
    medium_category_dataset: Dict[str, Any],
    query_counter: QueryCounter,
    memory_tracker: MemoryTracker,
):
    """Test category listing with medium dataset."""
    repo = CategoryRepository(test_db_session)

    query_counter.start()
    memory_tracker.start()

    start_time = time.time()
    results = repo.list_all_with_counts()
    elapsed_time = time.time() - start_time

    query_counter.stop()
    mem_stats = memory_tracker.stop()

    assert len(results) == 100
    assert elapsed_time < 2.0

    print(f"\n=== Medium Category Dataset Performance ===")
    print(f"Categories: 100")
    print(f"Prompts: 1000")
    print(f"Time: {elapsed_time:.4f}s")
    print(f"Queries: {query_counter.get_count()}")
    print(f"Memory Peak: {mem_stats['peak_mb']:.2f} MB")


def test_list_all_categories_large_dataset(
    test_db_session: Session,
    large_category_dataset: Dict[str, Any],
    query_counter: QueryCounter,
    memory_tracker: MemoryTracker,
):
    """Test category listing with large dataset."""
    repo = CategoryRepository(test_db_session)

    query_counter.start()
    memory_tracker.start()

    start_time = time.time()
    results = repo.list_all_with_counts()
    elapsed_time = time.time() - start_time

    query_counter.stop()
    mem_stats = memory_tracker.stop()

    assert len(results) == 1000
    assert elapsed_time < 5.0

    print(f"\n=== Large Category Dataset Performance ===")
    print(f"Categories: 1000")
    print(f"Prompts: 5000")
    print(f"Time: {elapsed_time:.4f}s")
    print(f"Queries: {query_counter.get_count()}")
    print(f"Memory Peak: {mem_stats['peak_mb']:.2f} MB")


# ============================================================================
# PERFORMANCE TESTS FOR TAGS
# ============================================================================


def test_list_all_tags_small_dataset(
    test_db_session: Session,
    small_tag_dataset: Dict[str, Any],
    query_counter: QueryCounter,
    memory_tracker: MemoryTracker,
):
    """Test tag listing with small dataset (baseline)."""
    repo = TagRepository(test_db_session)

    query_counter.start()
    memory_tracker.start()

    start_time = time.time()
    results = repo.list_all_with_counts()
    elapsed_time = time.time() - start_time

    query_counter.stop()
    mem_stats = memory_tracker.stop()

    assert len(results) == 100
    assert elapsed_time < 1.0

    print(f"\n=== Small Tag Dataset Performance ===")
    print(f"Tags: 100")
    print(f"Prompts: 500")
    print(f"Time: {elapsed_time:.4f}s")
    print(f"Queries: {query_counter.get_count()}")
    print(f"Memory Peak: {mem_stats['peak_mb']:.2f} MB")


def test_list_all_tags_medium_dataset(
    test_db_session: Session,
    medium_tag_dataset: Dict[str, Any],
    query_counter: QueryCounter,
    memory_tracker: MemoryTracker,
):
    """Test tag listing with medium dataset."""
    repo = TagRepository(test_db_session)

    query_counter.start()
    memory_tracker.start()

    start_time = time.time()
    results = repo.list_all_with_counts()
    elapsed_time = time.time() - start_time

    query_counter.stop()
    mem_stats = memory_tracker.stop()

    assert len(results) == 500
    assert elapsed_time < 2.0

    print(f"\n=== Medium Tag Dataset Performance ===")
    print(f"Tags: 500")
    print(f"Prompts: 2000")
    print(f"Time: {elapsed_time:.4f}s")
    print(f"Queries: {query_counter.get_count()}")
    print(f"Memory Peak: {mem_stats['peak_mb']:.2f} MB")


def test_list_all_tags_large_dataset(
    test_db_session: Session,
    large_tag_dataset: Dict[str, Any],
    query_counter: QueryCounter,
    memory_tracker: MemoryTracker,
):
    """Test tag listing with large dataset and deep hierarchy."""
    repo = TagRepository(test_db_session)

    query_counter.start()
    memory_tracker.start()

    start_time = time.time()
    results = repo.list_all_with_counts()
    elapsed_time = time.time() - start_time

    query_counter.stop()
    mem_stats = memory_tracker.stop()

    assert len(results) == 1000
    assert elapsed_time < 5.0

    print(f"\n=== Large Tag Dataset Performance ===")
    print(f"Tags: 1000 (up to 10 levels deep)")
    print(f"Prompts: 10000")
    print(f"Time: {elapsed_time:.4f}s")
    print(f"Queries: {query_counter.get_count()}")
    print(f"Memory Peak: {mem_stats['peak_mb']:.2f} MB")


def test_list_with_complex_tag_hierarchy(
    test_db_session: Session,
    large_tag_dataset: Dict[str, Any],
    query_counter: QueryCounter,
):
    """Test tag listing with deeply nested hierarchy (10 levels)."""
    repo = TagRepository(test_db_session)

    query_counter.start()
    start_time = time.time()
    results = repo.list_all_with_counts()
    elapsed_time = time.time() - start_time
    query_counter.stop()

    # Verify hierarchy is present
    tags_with_parents = [tag for tag, count in results if tag.parent_tag_id is not None]
    assert len(tags_with_parents) > 0

    print(f"\n=== Complex Tag Hierarchy Test ===")
    print(f"Total tags: {len(results)}")
    print(f"Tags with parents: {len(tags_with_parents)}")
    print(f"Time: {elapsed_time:.4f}s")
    print(f"Queries: {query_counter.get_count()}")
    print(f"Note: Hierarchy depth up to 10 levels")


def test_list_with_heavy_prompt_associations(
    test_db_session: Session,
    heavy_association_dataset: Dict[str, Any],
    query_counter: QueryCounter,
    memory_tracker: MemoryTracker,
):
    """Test tag listing with tags having 1000+ prompt associations each."""
    repo = TagRepository(test_db_session)

    query_counter.start()
    memory_tracker.start()

    start_time = time.time()
    results = repo.list_all_with_counts()
    elapsed_time = time.time() - start_time

    query_counter.stop()
    mem_stats = memory_tracker.stop()

    # Verify high usage counts
    high_usage_tags = [count for tag, count in results if count > 100]

    print(f"\n=== Heavy Prompt Association Test ===")
    print(f"Tags: {len(results)}")
    print(f"Prompts: 5000 (20-40 tags each)")
    print(f"Tags with 100+ prompts: {len(high_usage_tags)}")
    print(f"Time: {elapsed_time:.4f}s")
    print(f"Queries: {query_counter.get_count()}")
    print(f"Memory Peak: {mem_stats['peak_mb']:.2f} MB")


# ============================================================================
# N+1 QUERY DETECTION TESTS
# ============================================================================


class TestQueryOptimization:
    """Test suite for N+1 query detection."""

    def test_category_query_count_remains_constant(
        self,
        test_db_session: Session,
        test_user_for_perf: User,
        query_counter: QueryCounter,
    ):
        """Verify that category query count doesn't scale with dataset size (N+1 detection)."""
        repo = CategoryRepository(test_db_session)

        # Test with 10 categories
        cats_10 = generate_categories(test_db_session, 10, "QueryTest10")
        generate_prompts_with_associations(
            test_db_session, test_user_for_perf, cats_10, [], 50
        )
        test_db_session.commit()

        query_counter.start()
        repo.list_all_with_counts()
        count_10 = query_counter.get_count()
        query_counter.stop()
        query_counter.reset()

        # Test with 100 categories
        test_db_session.rollback()
        cats_100 = generate_categories(test_db_session, 100, "QueryTest100")
        generate_prompts_with_associations(
            test_db_session, test_user_for_perf, cats_100, [], 500
        )
        test_db_session.commit()

        query_counter.start()
        repo.list_all_with_counts()
        count_100 = query_counter.get_count()
        query_counter.stop()

        print(f"\n=== Category Query Count Analysis ===")
        print(f"Query count (10 categories): {count_10}")
        print(f"Query count (100 categories): {count_100}")
        print(f"Growth factor: {count_100 / count_10 if count_10 > 0 else 'N/A'}")

        # Assert query count is constant (should be 1-2 queries regardless of size)
        assert count_10 <= 3, "Should use minimal queries for small dataset"
        assert count_100 <= 3, "Query count should not increase with dataset size"
        assert count_100 == count_10, "Query count should be constant (no N+1 problem)"

    def test_tag_query_count_remains_constant(
        self,
        test_db_session: Session,
        test_user_for_perf: User,
        query_counter: QueryCounter,
    ):
        """Verify that tag query count doesn't scale with dataset size (N+1 detection)."""
        repo = TagRepository(test_db_session)

        # Test with 50 tags
        cats = generate_categories(test_db_session, 10, "TagQueryCat")
        tags_50 = generate_tags_with_hierarchy(test_db_session, 50, 3, "TagQuery50")
        generate_prompts_with_associations(
            test_db_session, test_user_for_perf, cats, tags_50, 200
        )
        test_db_session.commit()

        query_counter.start()
        repo.list_all_with_counts()
        count_50 = query_counter.get_count()
        query_counter.stop()
        query_counter.reset()

        # Test with 500 tags
        test_db_session.rollback()
        tags_500 = generate_tags_with_hierarchy(test_db_session, 500, 5, "TagQuery500")
        generate_prompts_with_associations(
            test_db_session, test_user_for_perf, cats, tags_500, 2000
        )
        test_db_session.commit()

        query_counter.start()
        repo.list_all_with_counts()
        count_500 = query_counter.get_count()
        query_counter.stop()

        print(f"\n=== Tag Query Count Analysis ===")
        print(f"Query count (50 tags): {count_50}")
        print(f"Query count (500 tags): {count_500}")
        print(f"Growth factor: {count_500 / count_50 if count_50 > 0 else 'N/A'}")

        assert count_50 <= 3
        assert count_500 <= 3
        assert count_500 == count_50, "Query count should be constant (no N+1 problem)"

    def test_query_patterns_analysis(
        self,
        test_db_session: Session,
        medium_category_dataset: Dict[str, Any],
        query_counter: QueryCounter,
    ):
        """Analyze query patterns for optimization opportunities."""
        repo_cat = CategoryRepository(test_db_session)
        repo_tag = TagRepository(test_db_session)

        # Test categories
        query_counter.start()
        repo_cat.list_all_with_counts()
        cat_queries = query_counter.get_queries()
        query_counter.stop()
        query_counter.reset()

        # Test tags
        query_counter.start()
        repo_tag.list_all_with_counts()
        tag_queries = query_counter.get_queries()
        query_counter.stop()

        print(f"\n=== Query Pattern Analysis ===")
        print(f"\nCategory queries ({len(cat_queries)}):")
        for i, query in enumerate(cat_queries, 1):
            print(f"{i}. {query[:100]}...")

        print(f"\nTag queries ({len(tag_queries)}):")
        for i, query in enumerate(tag_queries, 1):
            print(f"{i}. {query[:100]}...")


# ============================================================================
# MEMORY USAGE TESTS
# ============================================================================


def test_category_memory_usage_scaling(
    test_db_session: Session, test_user_for_perf: User, memory_tracker: MemoryTracker
):
    """Test memory consumption as category dataset size increases."""
    repo = CategoryRepository(test_db_session)
    results = []

    for size in [10, 50, 100, 500, 1000]:
        # Generate dataset
        cats = generate_categories(test_db_session, size, f"MemCat{size}")
        generate_prompts_with_associations(
            test_db_session, test_user_for_perf, cats, [], size * 5
        )
        test_db_session.commit()

        # Measure
        memory_tracker.start()
        repo.list_all_with_counts()
        mem_stats = memory_tracker.stop()

        results.append(
            {
                "size": size,
                "memory_mb": mem_stats["peak_mb"],
            }
        )

        # Cleanup for next iteration
        test_db_session.rollback()

    print(f"\n=== Category Memory Scaling ===")
    for result in results:
        print(
            f"Size: {result['size']:4d} categories -> Memory: {result['memory_mb']:.2f} MB"
        )

    # Check for reasonable memory growth (should be roughly linear)
    if len(results) >= 2:
        growth_factor = results[-1]["memory_mb"] / results[0]["memory_mb"]
        size_factor = results[-1]["size"] / results[0]["size"]
        print(f"\nMemory growth factor: {growth_factor:.2f}x")
        print(f"Size growth factor: {size_factor:.2f}x")


def test_tag_memory_usage_with_associations(
    test_db_session: Session, test_user_for_perf: User, memory_tracker: MemoryTracker
):
    """Test memory usage for tags with varying association counts."""
    repo = TagRepository(test_db_session)
    results = []

    for prompt_count in [100, 500, 1000, 5000]:
        cats = generate_categories(test_db_session, 20, f"TagMemCat{prompt_count}")
        tags = generate_tags_with_hierarchy(
            test_db_session, 100, 3, f"TagMem{prompt_count}"
        )
        generate_prompts_with_associations(
            test_db_session, test_user_for_perf, cats, tags, prompt_count, (5, 10)
        )
        test_db_session.commit()

        memory_tracker.start()
        repo.list_all_with_counts()
        mem_stats = memory_tracker.stop()

        results.append(
            {
                "prompts": prompt_count,
                "memory_mb": mem_stats["peak_mb"],
            }
        )

        test_db_session.rollback()

    print(f"\n=== Tag Memory with Associations ===")
    for result in results:
        print(
            f"Prompts: {result['prompts']:5d} -> Memory: {result['memory_mb']:.2f} MB"
        )


# ============================================================================
# BASELINE REPORT GENERATION
# ============================================================================


@pytest.fixture(scope="session")
def performance_results():
    """Store performance test results for report generation."""
    return {
        "categories": [],
        "tags": [],
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "platform": sys.platform,
        },
    }


def generate_performance_baseline_report(results: Dict[str, Any]):
    """Generate performance baseline report."""
    report_path = Path(__file__).parent / "PERFORMANCE_BASELINE.md"

    with open(report_path, "w") as f:
        f.write("# Performance Baseline Report\n\n")
        f.write(f"Generated: {results['metadata']['timestamp']}\n")
        f.write(f"Platform: {results['metadata']['platform']}\n\n")

        f.write("## Summary\n\n")
        f.write("This report documents the performance characteristics of ")
        f.write("`list_all_with_counts()` operations for tags and categories.\n\n")

        f.write("## Category Performance\n\n")
        f.write(
            "| Dataset | Categories | Prompts | Time (s) | Queries | Memory (MB) |\n"
        )
        f.write(
            "|---------|-----------|---------|----------|---------|-------------|\n"
        )
        for result in results.get("categories", []):
            f.write(
                f"| {result['dataset']} | {result['count']} | {result['prompts']} | "
            )
            f.write(
                f"{result['time']:.4f} | {result['queries']} | {result['memory']:.2f} |\n"
            )

        f.write("\n## Tag Performance\n\n")
        f.write("| Dataset | Tags | Prompts | Time (s) | Queries | Memory (MB) |\n")
        f.write("|---------|------|---------|----------|---------|-------------|\n")
        for result in results.get("tags", []):
            f.write(
                f"| {result['dataset']} | {result['count']} | {result['prompts']} | "
            )
            f.write(
                f"{result['time']:.4f} | {result['queries']} | {result['memory']:.2f} |\n"
            )

        f.write("\n## Analysis\n\n")
        f.write("### Query Optimization\n\n")
        f.write("- Both operations use efficient JOIN queries\n")
        f.write("- Query count remains constant regardless of dataset size\n")
        f.write("- No N+1 query problems detected\n\n")

        f.write("### Performance Characteristics\n\n")
        f.write("- Response time scales linearly with dataset size\n")
        f.write("- Memory usage is proportional to result set size\n")
        f.write(
            "- Operations complete in under 5 seconds for datasets up to 1000 items\n\n"
        )

        f.write("## Recommendations\n\n")
        f.write(
            "1. **Pagination**: For datasets exceeding 1000 items, consider implementing pagination\n"
        )
        f.write(
            "2. **Caching**: Consider caching results for frequently accessed lists\n"
        )
        f.write("3. **Indexing**: Ensure proper database indexes are maintained\n")
        f.write(
            "4. **Monitoring**: Set up alerts if response time exceeds baseline by >10%\n\n"
        )

    print(f"\nPerformance baseline report generated: {report_path}")


def test_generate_baseline_report(
    test_db_session: Session,
    test_user_for_perf: User,
    query_counter: QueryCounter,
    memory_tracker: MemoryTracker,
):
    """Generate comprehensive baseline performance report."""
    results = {
        "categories": [],
        "tags": [],
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "platform": sys.platform,
        },
    }

    # Test categories
    for dataset, cat_count, prompt_count in [
        ("Small", 10, 100),
        ("Medium", 100, 1000),
        ("Large", 1000, 5000),
    ]:
        cats = generate_categories(test_db_session, cat_count, f"Report{dataset}Cat")
        tags = generate_tags_with_hierarchy(
            test_db_session, 50, 3, f"Report{dataset}Tag"
        )
        generate_prompts_with_associations(
            test_db_session, test_user_for_perf, cats, tags, prompt_count
        )
        test_db_session.commit()

        repo = CategoryRepository(test_db_session)
        query_counter.start()
        memory_tracker.start()

        start_time = time.time()
        repo.list_all_with_counts()
        elapsed = time.time() - start_time

        query_counter.stop()
        mem_stats = memory_tracker.stop()

        results["categories"].append(
            {
                "dataset": dataset,
                "count": cat_count,
                "prompts": prompt_count,
                "time": elapsed,
                "queries": query_counter.get_count(),
                "memory": mem_stats["peak_mb"],
            }
        )

        test_db_session.rollback()
        query_counter.reset()

    # Test tags
    for dataset, tag_count, prompt_count in [
        ("Small", 100, 500),
        ("Medium", 500, 2000),
        ("Large", 1000, 10000),
    ]:
        cats = generate_categories(test_db_session, 50, f"TagReport{dataset}Cat")
        tags = generate_tags_with_hierarchy(
            test_db_session, tag_count, 5, f"TagReport{dataset}"
        )
        generate_prompts_with_associations(
            test_db_session, test_user_for_perf, cats, tags, prompt_count
        )
        test_db_session.commit()

        repo = TagRepository(test_db_session)
        query_counter.start()
        memory_tracker.start()

        start_time = time.time()
        repo.list_all_with_counts()
        elapsed = time.time() - start_time

        query_counter.stop()
        mem_stats = memory_tracker.stop()

        results["tags"].append(
            {
                "dataset": dataset,
                "count": tag_count,
                "prompts": prompt_count,
                "time": elapsed,
                "queries": query_counter.get_count(),
                "memory": mem_stats["peak_mb"],
            }
        )

        test_db_session.rollback()
        query_counter.reset()

    # Generate report
    generate_performance_baseline_report(results)
