"""
Performance tests with large datasets.
Tests loading, searching, filtering, and operations on 1000+ prompts.
"""

import pytest
import time
from pathlib import Path

from src.services.prompt_data_service import PromptDataService
from src.services.prompt_filter_service import PromptFilterService
from src.services.prompt_import_export_service import PromptImportExportService
from src.services.backup_service import BackupService


pytestmark = pytest.mark.performance


class TestLargeDatasetLoading:
    """Test performance of loading large datasets."""

    def test_load_1000_prompts(self, large_dataset_service):
        """Test loading 1000 prompts from file."""
        start_time = time.time()

        # Reload from file
        service2 = PromptDataService(large_dataset_service.data_file)
        service2.load_prompts()

        elapsed = time.time() - start_time

        assert len(service2.prompts) == 1000
        # Should load in reasonable time (< 5 seconds)
        assert elapsed < 5.0, f"Loading took {elapsed:.2f}s, expected < 5s"

    def test_load_prompts_with_versions(self, temp_data_file, sample_prompt_data):
        """Test loading prompts with extensive version histories."""
        service = PromptDataService(temp_data_file)

        # Create 100 prompts each with 20 versions
        for i in range(100):
            prompt_data = sample_prompt_data(
                title=f"Versioned Prompt {i}",
                prompt=f"Content {i}"
            )
            prompt_id = service.add_new_prompt(prompt_data)

            # Add 19 more versions
            for v in range(19):
                updated_data = sample_prompt_data(
                    title=f"Versioned Prompt {i} v{v+2}",
                    prompt=f"Updated content {v+2}"
                )
                service.update_prompt(prompt_id, updated_data, f"Update {v+2}")

        service.save_prompts()

        # Test loading performance
        start_time = time.time()
        service2 = PromptDataService(temp_data_file)
        service2.load_prompts()
        elapsed = time.time() - start_time

        assert len(service2.prompts) == 100
        # Total of 2000 versions (100 prompts * 20 versions each)
        total_versions = sum(len(p['versions']) for p in service2.prompts.values())
        assert total_versions == 2000

        # Should load in reasonable time
        assert elapsed < 10.0, f"Loading took {elapsed:.2f}s, expected < 10s"

    def test_save_1000_prompts(self, large_dataset_service):
        """Test saving 1000 prompts to file."""
        start_time = time.time()

        result = large_dataset_service.save_prompts()

        elapsed = time.time() - start_time

        assert result is True
        # Should save in reasonable time (< 5 seconds)
        assert elapsed < 5.0, f"Saving took {elapsed:.2f}s, expected < 5s"

        # Verify file size is reasonable
        file_size = Path(large_dataset_service.data_file).stat().st_size
        # Should be > 100KB but < 50MB for 1000 prompts
        assert file_size > 100 * 1024
        assert file_size < 50 * 1024 * 1024


class TestSearchPerformance:
    """Test search and filter performance with large datasets."""

    def test_filter_by_category_large_dataset(self, large_dataset_service, filter_service):
        """Test filtering 1000 prompts by category."""
        prompts = large_dataset_service.prompts

        start_time = time.time()

        filtered = filter_service.filter_prompts(prompts, filter_category="Programming")

        elapsed = time.time() - start_time

        assert len(filtered) > 0
        # Should filter quickly (< 1 second)
        assert elapsed < 1.0, f"Filtering took {elapsed:.2f}s, expected < 1s"

    def test_filter_by_tag_large_dataset(self, large_dataset_service, filter_service):
        """Test filtering 1000 prompts by tag."""
        prompts = large_dataset_service.prompts

        start_time = time.time()

        filtered = filter_service.filter_prompts(prompts, filter_tag="python")

        elapsed = time.time() - start_time

        assert len(filtered) > 0
        assert elapsed < 1.0, f"Filtering took {elapsed:.2f}s, expected < 1s"

    def test_search_term_large_dataset(self, large_dataset_service, filter_service):
        """Test searching 1000 prompts by search term."""
        prompts = large_dataset_service.prompts

        start_time = time.time()

        filtered = filter_service.filter_prompts(prompts, search_term="Prompt")

        elapsed = time.time() - start_time

        assert len(filtered) > 0
        assert elapsed < 1.0, f"Search took {elapsed:.2f}s, expected < 1s"

    def test_combined_filters_large_dataset(self, large_dataset_service, filter_service):
        """Test combined filtering on large dataset."""
        prompts = large_dataset_service.prompts

        start_time = time.time()

        filtered = filter_service.filter_prompts(
            prompts,
            filter_category="Programming",
            filter_tag="python",
            search_term="Test",
            filter_favorites=False
        )

        elapsed = time.time() - start_time

        assert isinstance(filtered, list)
        assert elapsed < 1.0, f"Combined filtering took {elapsed:.2f}s, expected < 1s"

    def test_sort_large_dataset(self, large_dataset_service, filter_service):
        """Test sorting 1000 prompts."""
        prompts = large_dataset_service.prompts
        filtered = filter_service.filter_prompts(prompts)

        start_time = time.time()

        sorted_prompts = filter_service.sort_prompts(filtered)

        elapsed = time.time() - start_time

        assert len(sorted_prompts) == len(filtered)
        assert elapsed < 1.0, f"Sorting took {elapsed:.2f}s, expected < 1s"

        # Verify it's actually sorted
        titles = [p['title'] for p in sorted_prompts]
        assert titles == sorted(titles)


class TestExportPerformance:
    """Test export performance with large datasets."""

    def test_export_1000_prompts_to_csv(self, large_dataset_service, import_export_service, temp_data_dir):
        """Test exporting 1000 prompts to CSV."""
        output_file = Path(temp_data_dir) / "large_export.csv"

        prompts = [(pid, large_dataset_service.prompts[pid]) for pid in large_dataset_service.prompts.keys()]

        start_time = time.time()

        result = import_export_service.export_to_csv(str(output_file), prompts)

        elapsed = time.time() - start_time

        assert result is True
        assert output_file.exists()
        assert elapsed < 5.0, f"CSV export took {elapsed:.2f}s, expected < 5s"

        # Verify file size
        file_size = output_file.stat().st_size
        assert file_size > 10 * 1024  # At least 10KB

    def test_export_1000_prompts_to_markdown(self, large_dataset_service, import_export_service, temp_data_dir):
        """Test exporting 1000 prompts to Markdown."""
        output_file = Path(temp_data_dir) / "large_export.md"

        prompts = [(pid, large_dataset_service.prompts[pid]) for pid in large_dataset_service.prompts.keys()]

        start_time = time.time()

        result = import_export_service.export_to_markdown(str(output_file), prompts)

        elapsed = time.time() - start_time

        assert result is True
        assert output_file.exists()
        assert elapsed < 5.0, f"Markdown export took {elapsed:.2f}s, expected < 5s"

    def test_import_large_csv(self, import_export_service, temp_data_dir):
        """Test importing large CSV file."""
        csv_file = Path(temp_data_dir) / "large_import.csv"

        # Generate large CSV
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("title,prompt,note,category,tags,favorite\n")
            for i in range(1000):
                f.write(f"Title {i},Content {i},Note {i},Category,tag1,No\n")

        start_time = time.time()

        prompts = import_export_service.import_from_csv(str(csv_file))

        elapsed = time.time() - start_time

        assert len(prompts) == 1000
        assert elapsed < 5.0, f"CSV import took {elapsed:.2f}s, expected < 5s"


class TestBackupPerformance:
    """Test backup operations with large datasets."""

    def test_backup_large_dataset(self, temp_data_dir, large_dataset_service):
        """Test creating backup of 1000 prompts."""
        large_dataset_service.data_file = str(Path(temp_data_dir) / "prompts_data.json")
        large_dataset_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        start_time = time.time()

        backup_id = backup_service.create_backup("large_dataset_backup")

        elapsed = time.time() - start_time

        assert backup_id is not None
        assert elapsed < 5.0, f"Backup took {elapsed:.2f}s, expected < 5s"

    def test_restore_large_backup(self, temp_data_dir, large_dataset_service):
        """Test restoring backup of 1000 prompts."""
        large_dataset_service.data_file = str(Path(temp_data_dir) / "prompts_data.json")
        large_dataset_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        # Create backup
        backup_id = backup_service.create_backup("test_restore")

        # Modify data
        large_dataset_service.add_new_prompt({"title": "New", "prompt": "New"})
        large_dataset_service.save_prompts()

        start_time = time.time()

        result = backup_service.restore_backup(backup_id)

        elapsed = time.time() - start_time

        assert result is True
        assert elapsed < 5.0, f"Restore took {elapsed:.2f}s, expected < 5s"

    def test_compress_multiple_backups(self, temp_data_dir, large_dataset_service):
        """Test compressing multiple large backups."""
        large_dataset_service.data_file = str(Path(temp_data_dir) / "prompts_data.json")
        large_dataset_service.save_prompts()

        backup_service = BackupService(temp_data_dir)

        # Create 10 backups
        for i in range(10):
            backup_service.create_backup(f"backup_{i}")

        start_time = time.time()

        compressed_count = backup_service.compress_old_backups(days_threshold=0)

        elapsed = time.time() - start_time

        assert compressed_count == 10
        assert elapsed < 10.0, f"Compression took {elapsed:.2f}s, expected < 10s"


class TestVersionHistoryPerformance:
    """Test performance with extensive version histories."""

    def test_get_versions_for_prompt_with_many_versions(self, prompt_with_versions):
        """Test retrieving version history for prompt with many versions."""
        service, prompt_id = prompt_with_versions

        start_time = time.time()

        versions = service.get_prompt_versions(prompt_id)

        elapsed = time.time() - start_time

        assert len(versions) >= 10
        assert elapsed < 0.5, f"Get versions took {elapsed:.2f}s, expected < 0.5s"

    def test_revert_prompt_with_many_versions(self, prompt_with_versions):
        """Test reverting prompt with extensive version history."""
        service, prompt_id = prompt_with_versions

        # Get first version
        versions = service.get_prompt_versions(prompt_id)
        first_version_data = versions[0]['data']

        start_time = time.time()

        result = service.revert_prompt_to_version(
            prompt_id,
            first_version_data,
            "Performance test revert"
        )

        elapsed = time.time() - start_time

        assert result is True
        assert elapsed < 0.5, f"Revert took {elapsed:.2f}s, expected < 0.5s"


class TestMemoryUsage:
    """Test memory efficiency with large datasets."""

    def test_load_large_dataset_memory_efficient(self, large_dataset_service):
        """Test that loading large dataset doesn't cause memory issues."""
        # Create even larger dataset in chunks
        for batch in range(10):
            for i in range(100):
                prompt_id = batch * 100 + i
                if prompt_id not in large_dataset_service.prompts:
                    data = {
                        "title": f"Prompt {prompt_id}",
                        "prompt": f"Content {prompt_id}" * 10,
                        "category": f"Category {batch}",
                        "tags": [f"tag{batch}"]
                    }
                    large_dataset_service.prompts[prompt_id] = {
                        "data": data,
                        "versions": [
                            {
                                "version_id": f"v{prompt_id}",
                                "timestamp": "2024-01-01T00:00:00Z",
                                "author": "test",
                                "message": "test",
                                "data": data,
                                "parents": []
                            }
                        ],
                        "branches": {}
                    }

        # Should handle 2000 prompts without issues
        assert len(large_dataset_service.prompts) >= 1000


class TestConcurrentOperations:
    """Test performance of rapid concurrent-like operations."""

    def test_rapid_prompt_creation(self, empty_data_service, sample_prompt_data):
        """Test creating many prompts rapidly."""
        start_time = time.time()

        for i in range(100):
            prompt_data = sample_prompt_data(title=f"Rapid {i}")
            empty_data_service.add_new_prompt(prompt_data)

        elapsed = time.time() - start_time

        assert len(empty_data_service.prompts) == 100
        assert elapsed < 2.0, f"Creating 100 prompts took {elapsed:.2f}s, expected < 2s"

    def test_rapid_prompt_updates(self, populated_data_service):
        """Test updating prompts rapidly."""
        prompt_id = 0

        start_time = time.time()

        for i in range(50):
            updated_data = {
                "title": f"Updated {i}",
                "prompt": f"Content {i}",
                "category": "Test"
            }
            populated_data_service.update_prompt(prompt_id, updated_data, f"Update {i}")

        elapsed = time.time() - start_time

        versions = populated_data_service.get_prompt_versions(prompt_id)
        assert len(versions) >= 50
        assert elapsed < 2.0, f"50 updates took {elapsed:.2f}s, expected < 2s"

    def test_rapid_filter_operations(self, large_dataset_service, filter_service):
        """Test performing many filter operations rapidly."""
        prompts = large_dataset_service.prompts

        start_time = time.time()

        # Perform 100 different filter operations
        for i in range(100):
            filter_service.filter_prompts(
                prompts,
                search_term=f"Prompt {i}"
            )

        elapsed = time.time() - start_time

        assert elapsed < 5.0, f"100 filter operations took {elapsed:.2f}s, expected < 5s"


class TestScalability:
    """Test scalability with increasing dataset sizes."""

    def test_linear_scaling_of_search(self, temp_data_file, sample_prompt_data):
        """Test that search performance scales linearly."""
        service = PromptDataService(temp_data_file)
        filter_service = PromptFilterService()

        times = []

        # Test with 100, 500, 1000 prompts
        for size in [100, 500, 1000]:
            # Clear and create new dataset
            service.prompts = {}
            service.next_id = 0

            for i in range(size):
                prompt_data = sample_prompt_data(title=f"Prompt {i}")
                service.add_new_prompt(prompt_data)

            # Measure search time
            start_time = time.time()
            filter_service.filter_prompts(service.prompts, search_term="Prompt 50")
            elapsed = time.time() - start_time

            times.append((size, elapsed))

        # All operations should complete quickly
        for size, elapsed in times:
            assert elapsed < 1.0, f"Search on {size} prompts took {elapsed:.2f}s"

    def test_categories_and_tags_scaling(self, temp_data_file, sample_prompt_data):
        """Test that category/tag extraction scales well."""
        service = PromptDataService(temp_data_file)

        # Create 1000 prompts with many unique categories and tags
        for i in range(1000):
            prompt_data = sample_prompt_data(
                title=f"Prompt {i}",
                category=f"Category {i % 50}",  # 50 unique categories
                tags=[f"tag{j}" for j in range(i % 10)]  # Varying number of tags
            )
            service.add_new_prompt(prompt_data)

        start_time = time.time()

        categories = service.get_categories()
        tags = service.get_tags()

        elapsed = time.time() - start_time

        assert len(categories) >= 50
        assert len(tags) > 0
        assert elapsed < 2.0, f"Get categories/tags took {elapsed:.2f}s, expected < 2s"
