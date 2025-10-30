"""
Comprehensive unit tests for VersionCompressionService.
Tests compression, decompression, statistics, and archival.
"""

import pytest
import json
from datetime import datetime, timedelta

from src.services.version_compression_service import VersionCompressionService


class TestCompressionBasics:
    """Test basic compression and decompression."""

    def test_compress_uncompressed_version(
        self, compression_service, sample_version_data
    ):
        """Test compressing an uncompressed version."""
        version = sample_version_data()

        compressed = compression_service.compress_version(version)

        assert compressed["compressed"] is True
        assert "compressed_at" in compressed
        assert isinstance(compressed["data"], dict)
        assert compressed["data"]["compressed"] is True
        assert "compressed_size" in compressed["data"]
        assert "original_size" in compressed["data"]

    def test_compress_already_compressed_version(
        self, compression_service, sample_version_data
    ):
        """Test compressing a version that's already compressed."""
        version = sample_version_data()

        # Compress once
        compressed1 = compression_service.compress_version(version)

        # Try to compress again
        compressed2 = compression_service.compress_version(compressed1)

        # Should return the same compressed version
        assert compressed2 == compressed1

    def test_decompress_compressed_version(
        self, compression_service, sample_version_data
    ):
        """Test decompressing a compressed version."""
        original_version = sample_version_data(
            data={"title": "Test", "prompt": "Content", "category": "Test"}
        )

        # Compress
        compressed = compression_service.compress_version(original_version)

        # Decompress
        decompressed = compression_service.decompress_version(compressed)

        assert decompressed["compressed"] is False
        assert decompressed["data"] == original_version["data"]

    def test_decompress_uncompressed_version(
        self, compression_service, sample_version_data
    ):
        """Test decompressing a version that's not compressed."""
        version = sample_version_data()

        decompressed = compression_service.decompress_version(version)

        # Should return the same version
        assert decompressed == version

    def test_compression_ratio_calculated(
        self, compression_service, sample_version_data
    ):
        """Test that compression ratio is calculated."""
        version = sample_version_data()

        compressed = compression_service.compress_version(version)

        assert "compression_ratio" in compressed["data"]
        assert compressed["data"]["compression_ratio"] > 0

    def test_compression_with_large_data(
        self, compression_service, sample_version_data
    ):
        """Test compressing version with large data."""
        large_data = {
            "title": "Large Prompt",
            "prompt": "This is a very long prompt content. " * 100,
            "category": "Test",
            "tags": ["tag"] * 50,
            "note": "Large note content. " * 100,
        }

        version = sample_version_data(data=large_data)

        compressed = compression_service.compress_version(version)

        assert compressed["compressed"] is True
        # Large data should compress well
        assert (
            compressed["data"]["compressed_size"] < compressed["data"]["original_size"]
        )


class TestCompressionRoundTrip:
    """Test compression/decompression round trips."""

    def test_round_trip_preserves_data(self, compression_service, sample_version_data):
        """Test that compress->decompress preserves original data."""
        original_version = sample_version_data(
            data={
                "title": "Round Trip Test",
                "prompt": "Original content",
                "category": "Test",
                "tags": ["tag1", "tag2"],
                "favorite": True,
            }
        )

        # Compress and decompress
        compressed = compression_service.compress_version(original_version)
        decompressed = compression_service.decompress_version(compressed)

        assert decompressed["data"] == original_version["data"]

    def test_round_trip_with_unicode(self, compression_service, sample_version_data):
        """Test round trip with Unicode characters."""
        original_version = sample_version_data(
            data={
                "title": "Unicode 你好",
                "prompt": "Content with 🚀 emoji",
                "category": "Test",
            }
        )

        compressed = compression_service.compress_version(original_version)
        decompressed = compression_service.decompress_version(compressed)

        assert decompressed["data"]["title"] == "Unicode 你好"
        assert "🚀" in decompressed["data"]["prompt"]

    def test_round_trip_with_special_characters(
        self, compression_service, sample_version_data
    ):
        """Test round trip with special characters."""
        original_version = sample_version_data(
            data={
                "title": "Special: <>&\"'",
                "prompt": "Content with\nNewlines\tand\ttabs",
                "category": "Test",
            }
        )

        compressed = compression_service.compress_version(original_version)
        decompressed = compression_service.decompress_version(compressed)

        assert decompressed["data"] == original_version["data"]


class TestCompressionThreshold:
    """Test compression threshold logic."""

    def test_should_compress_old_version(self, sample_version_data):
        """Test that old versions should be compressed."""
        service = VersionCompressionService(compression_threshold_days=30)

        # Create version with old timestamp (60 days ago)
        old_timestamp = (datetime.utcnow() - timedelta(days=60)).isoformat() + "Z"
        old_version = sample_version_data(timestamp=old_timestamp)

        assert service.should_compress_version(old_version) is True

    def test_should_not_compress_recent_version(self, sample_version_data):
        """Test that recent versions should not be compressed."""
        service = VersionCompressionService(compression_threshold_days=30)

        # Create recent version
        recent_timestamp = datetime.utcnow().isoformat() + "Z"
        recent_version = sample_version_data(timestamp=recent_timestamp)

        assert service.should_compress_version(recent_version) is False

    def test_should_not_compress_already_compressed(self, sample_version_data):
        """Test that already compressed versions are not re-compressed."""
        service = VersionCompressionService(compression_threshold_days=0)

        # Create old version
        old_timestamp = (datetime.utcnow() - timedelta(days=60)).isoformat() + "Z"
        old_version = sample_version_data(timestamp=old_timestamp)

        # Mark as compressed
        old_version["compressed"] = True

        assert service.should_compress_version(old_version) is False

    def test_threshold_boundary_condition(self, sample_version_data):
        """Test compression at exact threshold boundary."""
        service = VersionCompressionService(compression_threshold_days=30)

        # Create version exactly at threshold (30 days ago)
        boundary_timestamp = (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"
        boundary_version = sample_version_data(timestamp=boundary_timestamp)

        # Should be eligible for compression
        assert service.should_compress_version(boundary_version) is True

    def test_invalid_timestamp_format(self, sample_version_data):
        """Test handling of invalid timestamp format."""
        service = VersionCompressionService(compression_threshold_days=30)

        invalid_version = sample_version_data(timestamp="invalid_timestamp")

        # Should return False, not crash
        assert service.should_compress_version(invalid_version) is False


class TestBulkCompression:
    """Test compressing multiple versions."""

    def test_compress_old_versions_in_list(
        self, compression_service, sample_version_data
    ):
        """Test compressing old versions in a list."""
        # Override threshold for testing
        service = VersionCompressionService(compression_threshold_days=0)

        versions = [
            sample_version_data(
                version_id="v1",
                timestamp=(datetime.utcnow() - timedelta(days=60)).isoformat() + "Z",
            ),
            sample_version_data(
                version_id="v2",
                timestamp=(datetime.utcnow() - timedelta(days=45)).isoformat() + "Z",
            ),
            sample_version_data(
                version_id="v3", timestamp=datetime.utcnow().isoformat() + "Z"
            ),
        ]

        compressed_versions = service.compress_old_versions(versions)

        # All should be compressed with threshold=0
        assert len(compressed_versions) == 3
        assert all(v.get("compressed", False) for v in compressed_versions)

    def test_compress_preserves_order(self, compression_service, sample_version_data):
        """Test that compression preserves version order."""
        service = VersionCompressionService(compression_threshold_days=0)

        version_ids = ["v1", "v2", "v3", "v4", "v5"]
        versions = [
            sample_version_data(
                version_id=vid,
                timestamp=(datetime.utcnow() - timedelta(days=60)).isoformat() + "Z",
            )
            for vid in version_ids
        ]

        compressed_versions = service.compress_old_versions(versions)

        compressed_ids = [v["version_id"] for v in compressed_versions]
        assert compressed_ids == version_ids

    def test_compress_empty_list(self, compression_service):
        """Test compressing an empty list of versions."""
        compressed_versions = compression_service.compress_old_versions([])

        assert compressed_versions == []


class TestCompressionStatistics:
    """Test compression statistics calculation."""

    def test_stats_with_no_versions(self, compression_service):
        """Test statistics with no versions."""
        stats = compression_service.get_compression_statistics([])

        assert stats["total_versions"] == 0
        assert stats["compressed_versions"] == 0
        assert stats["uncompressed_versions"] == 0

    def test_stats_with_mixed_versions(self, compression_service, sample_version_data):
        """Test statistics with mixed compressed and uncompressed versions."""
        versions = [
            sample_version_data(version_id="v1"),
            sample_version_data(version_id="v2"),
            sample_version_data(version_id="v3"),
        ]

        # Compress some
        versions[0] = compression_service.compress_version(versions[0])
        versions[1] = compression_service.compress_version(versions[1])

        stats = compression_service.get_compression_statistics(versions)

        assert stats["total_versions"] == 3
        assert stats["compressed_versions"] == 2
        assert stats["uncompressed_versions"] == 1

    def test_stats_calculates_space_saved(
        self, compression_service, sample_version_data
    ):
        """Test that statistics calculate space saved."""
        large_data = {"title": "Large", "prompt": "Content " * 100, "category": "Test"}

        version = sample_version_data(data=large_data)
        compressed = compression_service.compress_version(version)

        stats = compression_service.get_compression_statistics([compressed])

        assert stats["space_saved_bytes"] > 0
        assert stats["space_saved_percentage"] > 0

    def test_stats_overall_compression_ratio(
        self, compression_service, sample_version_data
    ):
        """Test overall compression ratio calculation."""
        versions = [sample_version_data(version_id=f"v{i}") for i in range(5)]

        # Compress all
        compressed_versions = [
            compression_service.compress_version(v) for v in versions
        ]

        stats = compression_service.get_compression_statistics(compressed_versions)

        assert "overall_compression_ratio" in stats
        assert stats["overall_compression_ratio"] > 0


class TestVersionArchival:
    """Test version archival functionality."""

    def test_archive_old_versions(self, compression_service, sample_version_data):
        """Test archiving versions older than threshold."""
        versions = [
            sample_version_data(
                version_id="old1",
                timestamp=(datetime.utcnow() - timedelta(days=120)).isoformat() + "Z",
            ),
            sample_version_data(
                version_id="old2",
                timestamp=(datetime.utcnow() - timedelta(days=100)).isoformat() + "Z",
            ),
            sample_version_data(
                version_id="recent", timestamp=datetime.utcnow().isoformat() + "Z"
            ),
        ]

        result = compression_service.archive_old_versions(versions, days_threshold=90)

        assert result["archived_count"] == 2
        assert result["kept_count"] == 1
        assert len(result["archived_versions"]) == 2
        assert len(result["kept_versions"]) == 1

    def test_archive_boundary_condition(self, compression_service, sample_version_data):
        """Test archival at exact threshold boundary."""
        versions = [
            sample_version_data(
                version_id="boundary",
                timestamp=(datetime.utcnow() - timedelta(days=90)).isoformat() + "Z",
            ),
        ]

        result = compression_service.archive_old_versions(versions, days_threshold=90)

        # Version at exactly 90 days should be archived
        assert result["archived_count"] == 1

    def test_archive_empty_list(self, compression_service):
        """Test archiving an empty list."""
        result = compression_service.archive_old_versions([], days_threshold=90)

        assert result["archived_count"] == 0
        assert result["kept_count"] == 0

    def test_archive_invalid_timestamps(self, compression_service, sample_version_data):
        """Test archiving with invalid timestamps."""
        versions = [
            sample_version_data(version_id="invalid", timestamp="invalid_timestamp"),
            sample_version_data(
                version_id="valid", timestamp=datetime.utcnow().isoformat() + "Z"
            ),
        ]

        result = compression_service.archive_old_versions(versions, days_threshold=90)

        # Invalid timestamp version should be kept (safe default)
        assert result["kept_count"] >= 1


class TestEstimatedSavings:
    """Test compression savings estimation."""

    def test_estimate_savings_with_eligible_versions(
        self, compression_service, sample_version_data
    ):
        """Test estimating savings for eligible versions."""
        service = VersionCompressionService(compression_threshold_days=30)

        # Create old versions
        versions = [
            sample_version_data(
                version_id=f"old{i}",
                timestamp=(datetime.utcnow() - timedelta(days=60)).isoformat() + "Z",
                data={"title": f"Version {i}", "prompt": "Content " * 50},
            )
            for i in range(5)
        ]

        estimate = service.estimate_compression_savings(versions)

        assert estimate["eligible_versions"] == 5
        assert estimate["total_eligible_size_bytes"] > 0
        assert estimate["estimated_savings_bytes"] > 0
        assert estimate["estimated_savings_percentage"] > 0

    def test_estimate_savings_no_eligible_versions(
        self, compression_service, sample_version_data
    ):
        """Test estimating savings when no versions are eligible."""
        service = VersionCompressionService(compression_threshold_days=30)

        # Create recent versions
        versions = [
            sample_version_data(
                version_id=f"v{i}", timestamp=datetime.utcnow().isoformat() + "Z"
            )
            for i in range(5)
        ]

        estimate = service.estimate_compression_savings(versions)

        assert estimate["eligible_versions"] == 0
        assert estimate["estimated_savings_bytes"] == 0

    def test_estimate_savings_empty_list(self, compression_service):
        """Test estimating savings for empty list."""
        estimate = compression_service.estimate_compression_savings([])

        assert estimate["eligible_versions"] == 0
        assert estimate["estimated_savings_bytes"] == 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_compress_version_with_no_data_field(
        self, compression_service, sample_version_data
    ):
        """Test compressing a version without data field."""
        version = sample_version_data()
        del version["data"]

        # Should handle gracefully
        compressed = compression_service.compress_version(version)

        # Might return unchanged or handle differently
        assert isinstance(compressed, dict)

    def test_decompress_corrupted_data(self, compression_service):
        """Test decompressing with corrupted compressed data."""
        corrupted_version = {
            "version_id": "test",
            "compressed": True,
            "data": {
                "compressed": True,
                "algorithm": "zlib",
                "encoding": "base64",
                "data": "invalid_base64_data_!!!",
                "original_size": 100,
                "compressed_size": 50,
            },
        }

        # Should raise ValueError
        with pytest.raises(ValueError):
            compression_service.decompress_version(corrupted_version)

    def test_decompress_missing_compressed_data(self, compression_service):
        """Test decompressing when compressed data is missing."""
        incomplete_version = {
            "version_id": "test",
            "compressed": True,
            "data": {
                "compressed": True,
                # Missing 'data' field
            },
        }

        # Should handle gracefully or raise appropriate error
        try:
            decompressed = compression_service.decompress_version(incomplete_version)
            # If it doesn't raise an error, check it returns something reasonable
            assert isinstance(decompressed, dict)
        except (ValueError, KeyError):
            # Expected error
            pass
