"""Service for handling version compression and archival."""

import json
import zlib
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class VersionCompressionService:
    """Service for compressing and archiving old versions."""

    def __init__(self, compression_threshold_days: int = 30):
        """
        Initialize the VersionCompressionService.

        Args:
            compression_threshold_days (int): Days before a version is eligible for compression
        """
        self.compression_threshold_days = compression_threshold_days

    def should_compress_version(self, version: Dict[str, Any]) -> bool:
        """
        Determine if a version should be compressed.

        Args:
            version (Dict[str, Any]): The version to check

        Returns:
            bool: True if version should be compressed
        """
        if version.get("compressed"):
            return False

        timestamp_str = version.get("timestamp", "")
        try:
            version_date = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            age_days = (datetime.utcnow() - version_date.replace(tzinfo=None)).days
            return age_days >= self.compression_threshold_days
        except (ValueError, AttributeError):
            return False

    def compress_version(self, version: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compress a version's data.

        Args:
            version (Dict[str, Any]): The version to compress

        Returns:
            Dict[str, Any]: The compressed version
        """
        if version.get("compressed"):
            return version

        # Create a copy to avoid modifying the original
        compressed_version = version.copy()

        # Compress the data field
        if "data" in compressed_version:
            data_json = json.dumps(compressed_version["data"])
            compressed_data = zlib.compress(data_json.encode("utf-8"))
            encoded_data = base64.b64encode(compressed_data).decode("utf-8")

            compressed_version["data"] = {
                "compressed": True,
                "algorithm": "zlib",
                "encoding": "base64",
                "original_size": len(data_json),
                "compressed_size": len(encoded_data),
                "compression_ratio": round(len(encoded_data) / len(data_json), 2),
                "data": encoded_data,
            }
            compressed_version["compressed"] = True
            compressed_version["compressed_at"] = datetime.utcnow().isoformat() + "Z"

        return compressed_version

    def decompress_version(self, version: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decompress a version's data.

        Args:
            version (Dict[str, Any]): The compressed version

        Returns:
            Dict[str, Any]: The decompressed version
        """
        if not version.get("compressed"):
            return version

        # Create a copy to avoid modifying the original
        decompressed_version = version.copy()

        # Decompress the data field
        if "data" in decompressed_version and isinstance(
            decompressed_version["data"], dict
        ):
            data_info = decompressed_version["data"]
            if data_info.get("compressed"):
                try:
                    encoded_data = data_info.get("data", "")
                    compressed_data = base64.b64decode(encoded_data.encode("utf-8"))
                    data_json = zlib.decompress(compressed_data).decode("utf-8")
                    decompressed_version["data"] = json.loads(data_json)
                    decompressed_version["compressed"] = False
                except (ValueError, zlib.error) as e:
                    raise ValueError(f"Failed to decompress version: {str(e)}")

        return decompressed_version

    def compress_old_versions(
        self, versions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Compress all old versions in a list.

        Args:
            versions (List[Dict[str, Any]]): List of versions

        Returns:
            List[Dict[str, Any]]: List with old versions compressed
        """
        compressed_versions = []

        for version in versions:
            if self.should_compress_version(version):
                compressed_versions.append(self.compress_version(version))
            else:
                compressed_versions.append(version)

        return compressed_versions

    def get_compression_statistics(
        self, versions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get compression statistics for a list of versions.

        Args:
            versions (List[Dict[str, Any]]): List of versions

        Returns:
            Dict[str, Any]: Compression statistics
        """
        total_versions = len(versions)
        compressed_versions = sum(1 for v in versions if v.get("compressed"))
        uncompressed_versions = total_versions - compressed_versions

        total_original_size = 0
        total_compressed_size = 0

        for version in versions:
            if version.get("compressed") and isinstance(version.get("data"), dict):
                data_info = version["data"]
                total_original_size += data_info.get("original_size", 0)
                total_compressed_size += data_info.get("compressed_size", 0)
            else:
                # Estimate size for uncompressed versions
                version_json = json.dumps(version)
                total_original_size += len(version_json)
                total_compressed_size += len(version_json)

        overall_ratio = (
            (total_compressed_size / total_original_size)
            if total_original_size > 0
            else 1.0
        )

        return {
            "total_versions": total_versions,
            "compressed_versions": compressed_versions,
            "uncompressed_versions": uncompressed_versions,
            "compression_percentage": (
                round((compressed_versions / total_versions * 100), 2)
                if total_versions > 0
                else 0
            ),
            "total_original_size_bytes": total_original_size,
            "total_compressed_size_bytes": total_compressed_size,
            "overall_compression_ratio": round(overall_ratio, 2),
            "space_saved_bytes": total_original_size - total_compressed_size,
            "space_saved_percentage": (
                round(
                    (
                        (total_original_size - total_compressed_size)
                        / total_original_size
                        * 100
                    ),
                    2,
                )
                if total_original_size > 0
                else 0
            ),
        }

    def archive_old_versions(
        self, versions: List[Dict[str, Any]], days_threshold: int = 90
    ) -> Dict[str, Any]:
        """
        Archive versions older than a specified threshold.

        Args:
            versions (List[Dict[str, Any]]): List of versions
            days_threshold (int): Days before a version is archived

        Returns:
            Dict[str, Any]: Archive information
        """
        archived = []
        kept = []

        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)

        for version in versions:
            timestamp_str = version.get("timestamp", "")
            try:
                version_date = datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                )
                if version_date.replace(tzinfo=None) < cutoff_date:
                    archived.append(version)
                else:
                    kept.append(version)
            except (ValueError, AttributeError):
                kept.append(version)

        return {
            "archived_count": len(archived),
            "kept_count": len(kept),
            "archived_versions": archived,
            "kept_versions": kept,
            "archive_date": datetime.utcnow().isoformat() + "Z",
            "threshold_days": days_threshold,
        }

    def estimate_compression_savings(
        self, versions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Estimate potential savings from compression.

        Args:
            versions (List[Dict[str, Any]]): List of versions

        Returns:
            Dict[str, Any]: Estimated savings
        """
        eligible_versions = [v for v in versions if self.should_compress_version(v)]

        if not eligible_versions:
            return {
                "eligible_versions": 0,
                "estimated_savings_bytes": 0,
                "estimated_savings_percentage": 0,
            }

        total_size = 0
        for version in eligible_versions:
            version_json = json.dumps(version)
            total_size += len(version_json)

        # Estimate compression ratio (typically 30-50% for JSON)
        estimated_compressed_size = int(total_size * 0.4)
        estimated_savings = total_size - estimated_compressed_size

        return {
            "eligible_versions": len(eligible_versions),
            "total_eligible_size_bytes": total_size,
            "estimated_compressed_size_bytes": estimated_compressed_size,
            "estimated_savings_bytes": estimated_savings,
            "estimated_savings_percentage": (
                round((estimated_savings / total_size * 100), 2)
                if total_size > 0
                else 0
            ),
            "compression_threshold_days": self.compression_threshold_days,
        }
