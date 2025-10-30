import json
import os
import re
import shutil
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import getpass


class BackupService:
    """Service for handling prompt data backup and restoration operations."""

    def __init__(self, data_dir: str = None):
        """
        Initialize the BackupService.

        Args:
            data_dir (str): Path to the data directory. If None, uses default location.
        """
        if data_dir is None:
            script_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            self.data_dir = os.path.join(script_dir, "data")
        else:
            self.data_dir = data_dir

        self.backups_dir = os.path.join(self.data_dir, "backups")
        self.data_file = os.path.join(self.data_dir, "prompts_data.json")

        # Ensure backups directory exists
        os.makedirs(self.backups_dir, exist_ok=True)

    def create_backup(self, custom_name: str = None) -> Optional[str]:
        """
        Create a timestamped backup of the current data.

        Args:
            custom_name (str): Optional custom name for the backup

        Returns:
            Optional[str]: Backup ID if successful, None otherwise
        """
        try:
            # Check if data file exists
            if not os.path.exists(self.data_file):
                print(f"Backup Error: Data file {self.data_file} does not exist")
                return None

            # Generate backup filename
            if custom_name:
                safe_suffix = self._sanitize_backup_name(custom_name)
                if safe_suffix:
                    backup_filename = f"backup_{safe_suffix}.json"
                else:
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    backup_filename = f"backup_{timestamp}.json"
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                backup_filename = f"backup_{timestamp}.json"

            backup_path = os.path.join(self.backups_dir, backup_filename)

            # Copy the data file to backup location
            shutil.copy2(self.data_file, backup_path)

            # Get backup metadata
            backup_size = os.path.getsize(backup_path)

            # Load data to count prompts
            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                prompt_count = len(data.get("prompts", {}))

            # Create backup metadata
            backup_id = backup_filename.replace(".json", "")
            metadata = {
                "backup_id": backup_id,
                "filename": backup_filename,
                "timestamp": datetime.now().isoformat(),
                "size_bytes": backup_size,
                "prompt_count": prompt_count,
                "created_by": self._get_current_user(),
                "data_file_modified": datetime.fromtimestamp(
                    os.path.getmtime(self.data_file)
                ).isoformat(),
                "compressed": False,
            }

            # Save metadata
            metadata_path = backup_path.replace(".json", "_metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            print(f"Backup created successfully: {backup_filename}")
            return backup_id

        except Exception as e:
            print(f"Backup Error: Failed to create backup: {e}")
            return None

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Get list of available backups with metadata.

        Returns:
            List[Dict[str, Any]]: List of backup metadata, sorted by timestamp (newest first)
        """
        backups = []

        try:
            # Look for backup metadata files
            for filename in os.listdir(self.backups_dir):
                if filename.endswith("_metadata.json"):
                    metadata_path = os.path.join(self.backups_dir, filename)
                    try:
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                            backups.append(metadata)
                    except (json.JSONDecodeError, IOError) as e:
                        print(
                            f"Warning: Could not read backup metadata {filename}: {e}"
                        )

            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        except Exception as e:
            print(f"Error listing backups: {e}")

        return backups

    def restore_backup(self, backup_id: str) -> bool:
        """
        Restore data from a specific backup.

        Args:
            backup_id (str): ID of the backup to restore

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            backup_path = self._resolve_backup_path(backup_id)
            if not backup_path or not os.path.exists(backup_path):
                print(f"Restore Error: Backup file for ID {backup_id} does not exist")
                return False

            if not self._is_valid_backup_file(backup_path):
                print(f"Restore Error: Backup {backup_id} appears to be corrupted")
                return False

            # Create a pre-restore backup automatically
            print("Creating pre-restore backup...")
            pre_restore_backup = self.create_backup("pre_restore")
            if not pre_restore_backup:
                print("Warning: Could not create pre-restore backup")

            # Restore the backup (handle compressed files transparently)
            if backup_path.endswith(".gz"):
                with gzip.open(backup_path, "rb") as src, open(
                    self.data_file, "wb"
                ) as dst:
                    shutil.copyfileobj(src, dst)
            else:
                shutil.copy2(backup_path, self.data_file)

            print(f"Backup {backup_id} restored successfully")
            return True

        except Exception as e:
            print(f"Restore Error: Failed to restore backup {backup_id}: {e}")
            return False

    def cleanup_old_backups(self, retention_days: int = 30) -> int:
        """
        Remove old backups based on retention policy.

        Args:
            retention_days (int): Number of days to keep backups

        Returns:
            int: Number of backups removed
        """
        removed_count = 0

        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            backups = self.list_backups()

            for backup in backups:
                backup_date = datetime.fromisoformat(
                    backup["timestamp"].replace("Z", "+00:00")
                )

                if backup_date < cutoff_date:
                    # Remove backup files
                    backup_filename = backup["filename"]
                    backup_path = os.path.join(self.backups_dir, backup_filename)
                    metadata_filename = backup_filename.replace(
                        ".json", "_metadata.json"
                    )
                    metadata_path = os.path.join(self.backups_dir, metadata_filename)

                    try:
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                        if os.path.exists(metadata_path):
                            os.remove(metadata_path)
                        removed_count += 1
                        print(f"Removed old backup: {backup_filename}")
                    except OSError as e:
                        print(
                            f"Warning: Could not remove backup {backup_filename}: {e}"
                        )

            if removed_count > 0:
                print(f"Cleanup completed: {removed_count} old backups removed")

        except Exception as e:
            print(f"Cleanup Error: Failed to cleanup old backups: {e}")

        return removed_count

    def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific backup.

        Args:
            backup_id (str): ID of the backup

        Returns:
            Optional[Dict[str, Any]]: Backup metadata if found, None otherwise
        """
        backups = self.list_backups()
        for backup in backups:
            if backup["backup_id"] == backup_id:
                return backup
        return None

    def compress_old_backups(self, days_threshold: int = 7) -> int:
        """
        Compress old backups using gzip.

        Args:
            days_threshold (int): Compress backups older than this many days

        Returns:
            int: Number of backups compressed
        """
        compressed_count = 0

        try:
            cutoff_date = datetime.now() - timedelta(days=days_threshold)
            backups = self.list_backups()

            for backup in backups:
                backup_date = datetime.fromisoformat(
                    backup["timestamp"].replace("Z", "+00:00")
                )

                if backup_date < cutoff_date:
                    backup_filename = backup["filename"]
                    backup_path = os.path.join(self.backups_dir, backup_filename)
                    metadata_path = backup_path.replace(".json", "_metadata.json")

                    if os.path.exists(backup_path) and not backup_filename.endswith(
                        ".gz"
                    ):
                        try:
                            # Compress the backup file
                            with open(backup_path, "rb") as f_in:
                                with gzip.open(f"{backup_path}.gz", "wb") as f_out:
                                    shutil.copyfileobj(f_in, f_out)

                            # Remove original file
                            os.remove(backup_path)

                            # Update metadata
                            backup["filename"] = f"{backup_filename}.gz"
                            backup["compressed"] = True
                            backup["original_size"] = backup["size_bytes"]
                            backup["compressed_size"] = os.path.getsize(
                                f"{backup_path}.gz"
                            )

                            with open(metadata_path, "w", encoding="utf-8") as f:
                                json.dump(backup, f, indent=2)

                            compressed_count += 1
                            print(f"Compressed backup: {backup_filename}")

                        except Exception as e:
                            print(
                                f"Warning: Could not compress backup {backup_filename}: {e}"
                            )

            if compressed_count > 0:
                print(f"Compression completed: {compressed_count} backups compressed")

        except Exception as e:
            print(f"Compression Error: Failed to compress old backups: {e}")

        return compressed_count

    def get_backup_stats(self) -> Dict[str, Any]:
        """
        Get statistics about backups.

        Returns:
            Dict[str, Any]: Backup statistics
        """
        backups = self.list_backups()

        if not backups:
            return {
                "total_backups": 0,
                "total_size": 0,
                "oldest_backup": None,
                "newest_backup": None,
                "compressed_count": 0,
                "compressed_backups": 0,
            }

        total_size = sum(backup.get("size_bytes", 0) for backup in backups)
        compressed_count = sum(
            1 for backup in backups if backup.get("compressed", False)
        )

        return {
            "total_backups": len(backups),
            "total_size": total_size,
            "oldest_backup": backups[-1]["timestamp"] if backups else None,
            "newest_backup": backups[0]["timestamp"] if backups else None,
            "compressed_count": compressed_count,
            "compressed_backups": compressed_count,
        }

    def delete_backup(self, backup_id: str) -> bool:
        """
        Delete a backup and its metadata files.

        Args:
            backup_id (str): Backup ID to delete

        Returns:
            bool: True if any files were removed, False otherwise
        """
        try:
            metadata = self.get_backup_info(backup_id)
            filename = metadata.get("filename") if metadata else None
            candidates = set()

            base_json = os.path.join(self.backups_dir, f"{backup_id}.json")
            candidates.add(base_json)
            candidates.add(f"{base_json}.gz")

            if filename:
                candidates.add(os.path.join(self.backups_dir, filename))

            removed = False
            for path in candidates:
                if path and os.path.exists(path):
                    os.remove(path)
                    removed = True

            metadata_path = self._metadata_path_from_filename(
                filename or f"{backup_id}.json"
            )
            if metadata_path and os.path.exists(metadata_path):
                os.remove(metadata_path)
                removed = True

            return removed
        except Exception as e:
            print(f"Delete Error: Failed to delete backup {backup_id}: {e}")
            return False

    def _get_current_user(self) -> str:
        """
        Get the current user.

        Returns:
            str: Current user name
        """
        try:
            return getpass.getuser()
        except Exception:
            return "unknown"

    def _sanitize_backup_name(self, name: str) -> str:
        """Sanitize custom backup names for safe filenames."""
        if not name:
            return ""
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip())
        return cleaned[:64]

    def _metadata_path_from_filename(self, filename: str) -> Optional[str]:
        """Derive metadata path from a backup filename."""
        if not filename:
            return None
        if filename.endswith(".json.gz"):
            base = filename[: -len(".json.gz")]
        elif filename.endswith(".json"):
            base = filename[: -len(".json")]
        else:
            base = filename
        return os.path.join(self.backups_dir, f"{base}_metadata.json")

    def _resolve_backup_path(self, backup_id: str) -> Optional[str]:
        """Resolve the on-disk path for a backup, checking compressed variants."""
        candidate = os.path.join(self.backups_dir, f"{backup_id}.json")
        if os.path.exists(candidate):
            return candidate
        gz_candidate = f"{candidate}.gz"
        if os.path.exists(gz_candidate):
            return gz_candidate
        metadata = self.get_backup_info(backup_id)
        if metadata:
            meta_candidate = os.path.join(
                self.backups_dir, metadata.get("filename", "")
            )
            if meta_candidate and os.path.exists(meta_candidate):
                return meta_candidate
        return None

    def _is_valid_backup_file(self, backup_path: str) -> bool:
        """Validate that a backup file contains readable JSON."""
        try:
            if backup_path.endswith(".gz"):
                with gzip.open(backup_path, "rt", encoding="utf-8") as f:
                    json.load(f)
            else:
                with open(backup_path, "r", encoding="utf-8") as f:
                    json.load(f)
            return True
        except (OSError, json.JSONDecodeError) as e:
            print(f"Backup Validation Error: {e}")
            return False
