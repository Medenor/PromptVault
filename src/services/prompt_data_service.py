import json
import os
import uuid
from datetime import datetime
import getpass
from typing import Dict, Any, Set, List, Tuple, Iterable

# Import sanitization utilities from validators
from src.web.validators import (
    sanitize_text_field,
    sanitize_tags,
    MAX_TITLE_LENGTH,
    MAX_PROMPT_LENGTH,
    MAX_CATEGORY_LENGTH,
    MAX_NOTE_LENGTH,
    MAX_TAG_COUNT,
    MAX_TAG_LENGTH,
)


class PromptDataService:
    """Service for handling prompt data operations including loading, saving, and migration."""

    def __init__(self, data_file_path: str = None):
        """
        Initialize the PromptDataService.

        Args:
            data_file_path (str): Path to the data file. If None, uses default location.
        """
        if data_file_path is None:
            script_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            self.data_file = os.path.join(script_dir, "data", "prompts_data.json")
        else:
            self.data_file = data_file_path

        self.prompts = {}
        self.next_id = 0
        self.categories = []
        self.global_tags = set()

    def _normalize_tags(self, tags: Iterable[Any]) -> List[str]:
        """
        Normalize a collection of tags by trimming whitespace and dropping blanks.

        Args:
            tags (Iterable[Any]): Raw tag values.

        Returns:
            List[str]: Cleaned tag strings preserving input order.
        """
        normalized: List[str] = []
        for tag in tags or []:
            if not isinstance(tag, str):
                continue
            cleaned = tag.strip()
            if cleaned:
                normalized.append(cleaned)
        return normalized

    def _normalize_prompt_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize prompt payload fields such as tags prior to persistence.

        This provides defense-in-depth by sanitizing data at the service layer,
        even if API validation is bypassed or data comes from other sources.

        Args:
            data (Dict[str, Any]): Prompt data to normalize.

        Returns:
            Dict[str, Any]: Normalized prompt data.

        Sanitization applied:
            - Title: Control character removal, whitespace normalization, length limit
            - Prompt: Control character removal (preserves newlines), length limit
            - Category: Control character removal, whitespace normalization, length limit
            - Note: Control character removal (preserves newlines), length limit
            - Tags: Deduplication, sanitization, length limits
        """
        if not isinstance(data, dict):
            return {}

        # Sanitize title
        if "title" in data and data["title"]:
            data["title"] = sanitize_text_field(
                str(data["title"]), max_length=MAX_TITLE_LENGTH, allow_newlines=False
            )

        # Sanitize prompt content
        if "prompt" in data and data["prompt"]:
            data["prompt"] = sanitize_text_field(
                str(data["prompt"]), max_length=MAX_PROMPT_LENGTH, allow_newlines=True
            )

        # Sanitize category
        if "category" in data and data["category"]:
            data["category"] = sanitize_text_field(
                str(data["category"]), max_length=MAX_CATEGORY_LENGTH, allow_newlines=False
            )

        # Sanitize note
        if "note" in data and data["note"]:
            data["note"] = sanitize_text_field(
                str(data["note"]), max_length=MAX_NOTE_LENGTH, allow_newlines=True
            )

        # Sanitize and deduplicate tags
        tags = data.get("tags", [])
        if isinstance(tags, list):
            data["tags"] = sanitize_tags(tags, max_count=MAX_TAG_COUNT, max_length_per_tag=MAX_TAG_LENGTH)
        else:
            data["tags"] = []

        return data

    def save_prompts(self) -> bool:
        """
        Save prompts to the data file.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update categories and tags from current prompts before saving
            self._update_categories_and_tags()

            with open(self.data_file, "w", encoding="utf-8") as f:
                prompts_to_save = {}
                for k, v in self.prompts.items():
                    # Ensure 'history' is not saved in the new structure
                    v_copy = v.copy()
                    if "history" in v_copy:
                        del v_copy["history"]
                    prompts_to_save[str(k)] = v_copy

                save_data = {
                    "next_id": self.next_id,
                    "prompts": prompts_to_save,
                    "categories": self.categories,
                    "global_tags": sorted(list(self.global_tags)),
                }
                json.dump(save_data, f, ensure_ascii=False, indent=4)
            return True
        except IOError as e:
            print(f"Save Error: Could not save prompts: {e}")
            return False
        except Exception as e:
            print(f"Unknown Save Error: An unexpected error occurred while saving: {e}")
            return False

    def load_prompts(self) -> Dict[int, Dict]:
        """
        Load prompts from the data file.

        Returns:
            Dict[int, Dict]: The loaded prompts
        """
        if not os.path.exists(self.data_file):
            self.prompts = {}
            self.next_id = 0
            self.categories = []
            self.global_tags = set()
            return self.prompts

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
                raw_next_id = loaded_data.get("next_id", 0)
                try:
                    self.next_id = int(raw_next_id)
                except (TypeError, ValueError):
                    self.next_id = 0
                loaded_prompts = {}
                for k, v in loaded_data.get("prompts", {}).items():
                    try:
                        prompt_id = int(k)
                        if isinstance(v, dict):
                            v = self._migrate_old_data_structure(prompt_id, v)
                            if "data" in v and isinstance(v["data"], dict):
                                v["data"] = self._normalize_prompt_payload(v["data"])
                            for version in v.get("versions", []):
                                if isinstance(version, dict) and isinstance(
                                    version.get("data"), dict
                                ):
                                    version["data"] = self._normalize_prompt_payload(
                                        version["data"]
                                    )
                            loaded_prompts[prompt_id] = v
                        else:
                            print(
                                f"Warning: Invalid structure for prompt ID '{k}', ignored."
                            )
                    except ValueError:
                        print(f"Warning: Invalid prompt key '{k}', ignored.")

                self.prompts = loaded_prompts

                # Load categories and tags from file if they exist (for backward compatibility)
                categories_data = loaded_data.get("categories")
                self.categories = (
                    categories_data if isinstance(categories_data, list) else []
                )

                raw_global_tags = loaded_data.get("global_tags", [])
                if isinstance(raw_global_tags, list):
                    self.global_tags = set(self._normalize_tags(raw_global_tags))
                else:
                    self.global_tags = set()

                # If no categories/tags in file, build them from current prompts
                if not self.categories:
                    self.categories = list(
                        set(
                            prompt_info["data"].get("category", "No category")
                            for prompt_info in self.prompts.values()
                        )
                    )
                    self.categories.sort()

                if not self.global_tags:
                    all_tags = set()
                    for prompt_info in self.prompts.values():
                        prompt_tags = prompt_info["data"].get("tags", [])
                        if isinstance(prompt_tags, list):
                            all_tags.update(prompt_tags)
                    self.global_tags = all_tags

            return self.prompts
        except (IOError, json.JSONDecodeError) as e:
            print(f"Load Error: Could not load prompts from {self.data_file}: {e}")
            self.prompts = {}
            self.next_id = 0
            self.categories = []
            self.global_tags = set()
            return self.prompts
        except Exception as e:
            print(f"Unknown Error: An unexpected error occurred while loading: {e}")
            self.prompts = {}
            self.next_id = 0
            self.categories = []
            self.global_tags = set()
            return self.prompts

    def _migrate_old_data_structure(self, prompt_id: int, prompt_info: Dict) -> Dict:
        """
        Migrate old data structure to new format.

        Args:
            prompt_id (int): The ID of the prompt
            prompt_info (Dict): The prompt information to migrate

        Returns:
            Dict: Migrated prompt information
        """
        # Migration logic for old data structure
        if (
            "data" in prompt_info
            and "history" in prompt_info
            and "versions" not in prompt_info
        ):
            print(f"Migrating old prompt structure for ID {prompt_id}")
            current_data = prompt_info["data"]
            history_entries = prompt_info["history"]

            versions = []
            # Create initial version from the first history entry or current data
            if history_entries:
                first_data = history_entries[0]
                first_version_id = self._generate_version_id(
                    first_data, "Initial import"
                )
                versions.append(
                    {
                        "version_id": first_version_id,
                        "timestamp": self._get_current_timestamp(),
                        "author": self._get_current_user(),
                        "message": "Initial import",
                        "data": first_data,
                        "parents": [],
                    }
                )
                # Add subsequent history entries as new versions
                for i in range(1, len(history_entries)):
                    prev_version_id = versions[-1]["version_id"]
                    new_data = history_entries[i]
                    new_version_id = self._generate_version_id(
                        new_data, "History migration"
                    )
                    versions.append(
                        {
                            "version_id": new_version_id,
                            "timestamp": self._get_current_timestamp(),
                            "author": self._get_current_user(),
                            "message": "History migration",
                            "data": new_data,
                            "parents": [prev_version_id],
                        }
                    )
            else:  # No history, just current data
                initial_version_id = self._generate_version_id(
                    current_data, "Initial import"
                )
                versions.append(
                    {
                        "version_id": initial_version_id,
                        "timestamp": self._get_current_timestamp(),
                        "author": self._get_current_user(),
                        "message": "Initial import",
                        "data": current_data,
                        "parents": [],
                    }
                )

            # Ensure current_data is the latest in versions
            if versions and versions[-1]["data"] != current_data:
                latest_version_id = self._generate_version_id(
                    current_data, "Current state after migration"
                )
                versions.append(
                    {
                        "version_id": latest_version_id,
                        "timestamp": self._get_current_timestamp(),
                        "author": self._get_current_user(),
                        "message": "Current state after migration",
                        "data": current_data,
                        "parents": [versions[-1]["version_id"]] if versions else [],
                    }
                )

            prompt_info = {
                "data": current_data,
                "versions": versions,
                "branches": {"main": versions[-1]["version_id"]} if versions else {},
            }

        # Ensure new fields exist for all prompts
        if "versions" not in prompt_info:
            prompt_info["versions"] = []
        if "branches" not in prompt_info:
            prompt_info["branches"] = {}
        if "data" not in prompt_info:
            prompt_info["data"] = {}

        # Ensure category and favorite defaults
        if "category" not in prompt_info["data"] or not prompt_info["data"]["category"]:
            prompt_info["data"]["category"] = "No category"
        if "favorite" not in prompt_info["data"]:
            prompt_info["data"]["favorite"] = False

        return prompt_info

    def _generate_version_id(self, data: Dict, message: str) -> str:
        """
        Generate a unique version ID.

        Args:
            data (Dict): The data for the version
            message (str): The commit message

        Returns:
            str: A unique version ID
        """
        return str(uuid.uuid4())

    def _get_current_timestamp(self) -> str:
        """
        Get the current timestamp in ISO format.

        Returns:
            str: Current timestamp
        """
        return datetime.utcnow().isoformat() + "Z"

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

    def get_all_tags_from_prompts(self) -> Set[str]:
        """
        Get all unique tags from all prompts.

        Returns:
            Set[str]: Set of all tags
        """
        all_tags = set()
        for prompt_info in self.prompts.values():
            all_tags.update(prompt_info["data"].get("tags", []))
        return all_tags

    def _update_categories_and_tags(self) -> None:
        """
        Update categories and tags from current prompts.

        Keeps existing category ordering while appending any new categories in the
        order they are first observed. This ensures the persisted category list
        respects the configuration file ordering while still learning new values.
        """

        def normalize_category(raw_value: Any) -> str:
            if isinstance(raw_value, str):
                cleaned = raw_value.strip()
                if cleaned:
                    return cleaned
            return "No category"

        ordered_categories: List[str] = []
        seen_categories: Set[str] = set()

        for predefined in self.categories:
            normalized = normalize_category(predefined)
            if normalized not in seen_categories:
                ordered_categories.append(normalized)
                seen_categories.add(normalized)

        for prompt_info in self.prompts.values():
            raw_category = prompt_info["data"].get("category", "No category")
            normalized = normalize_category(raw_category)
            if normalized not in seen_categories:
                ordered_categories.append(normalized)
                seen_categories.add(normalized)

        if not ordered_categories:
            ordered_categories.append("No category")

        self.categories = ordered_categories

        # Update tags from current prompts - merge with existing predefined tags
        all_tags = set()
        for prompt_info in self.prompts.values():
            prompt_tags = prompt_info["data"].get("tags", [])
            if isinstance(prompt_tags, list):
                all_tags.update(prompt_tags)
        # Preserve existing predefined tags and add any new ones in use
        self.global_tags = self.global_tags | all_tags

    def add_new_prompt(self, data: Dict[str, Any]) -> int:
        """
        Add a new prompt with initial version.

        Args:
            data (Dict[str, Any]): The prompt data

        Returns:
            int: The ID of the new prompt
        """
        data = self._normalize_prompt_payload(data.copy())

        prompt_id = self.next_id
        self.next_id += 1

        commit_message = data.pop("commit_message", "Initial commit")
        version_id = self._generate_version_id(data, commit_message)
        new_version = {
            "version_id": version_id,
            "timestamp": self._get_current_timestamp(),
            "author": self._get_current_user(),
            "message": commit_message,
            "data": data,
            "parents": [],
        }
        self.prompts[prompt_id] = {
            "data": data,
            "versions": [new_version],
            "branches": {"main": version_id},
        }

        # Note: Do not clear categories and tags to preserve predefined ones
        return prompt_id

    def update_prompt(
        self, prompt_id: int, data: Dict[str, Any], commit_message: str = "Update"
    ) -> bool:
        """
        Update an existing prompt with a new version.

        Args:
            prompt_id (int): The ID of the prompt to update
            data (Dict[str, Any]): The updated prompt data
            commit_message (str): The commit message

        Returns:
            bool: True if successful, False otherwise
        """
        if prompt_id not in self.prompts:
            return False

        data = self._normalize_prompt_payload(data.copy())

        current_prompt_info = self.prompts[prompt_id]

        # Get the parent version_id (current head of 'main' branch)
        parent_version_id = current_prompt_info["branches"].get("main")
        parents = [parent_version_id] if parent_version_id else []

        version_id = self._generate_version_id(data, commit_message)
        new_version = {
            "version_id": version_id,
            "timestamp": self._get_current_timestamp(),
            "author": self._get_current_user(),
            "message": commit_message,
            "data": data,
            "parents": parents,
        }
        current_prompt_info["versions"].append(new_version)
        current_prompt_info["data"] = data
        current_prompt_info["branches"]["main"] = version_id

        # Note: Do not clear categories and tags to preserve predefined ones
        return True

    def delete_prompt(self, prompt_id: int) -> bool:
        """
        Delete a prompt.

        Args:
            prompt_id (int): The ID of the prompt to delete

        Returns:
            bool: True if successful, False otherwise
        """
        if prompt_id in self.prompts:
            del self.prompts[prompt_id]
            # Note: Do not clear categories and tags to preserve predefined ones
            return True
        return False

    def clear_all_prompts(self) -> bool:
        """
        Clear all prompts and reset the data service to initial state.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Clear all data in memory
            self.prompts = {}
            self.next_id = 0
            self.categories = []
            self.global_tags = set()

            # Save the empty state to disk
            return self.save_prompts()
        except Exception as e:
            print(f"Error clearing all prompts: {e}")
            return False

    def get_prompt_data(self, prompt_id: int) -> Dict[str, Any]:
        """
        Get the current data for a prompt.

        Args:
            prompt_id (int): The ID of the prompt

        Returns:
            Dict[str, Any]: The prompt data, or empty dict if not found
        """
        if prompt_id in self.prompts:
            return self.prompts[prompt_id]["data"]
        return {}

    def get_prompt_versions(self, prompt_id: int) -> List[Dict[str, Any]]:
        """
        Get the version history for a prompt.

        Args:
            prompt_id (int): The ID of the prompt

        Returns:
            List[Dict[str, Any]]: The version history, or empty list if not found
        """
        if prompt_id in self.prompts:
            return self.prompts[prompt_id].get("versions", [])
        return []

    def revert_prompt_to_version(
        self, prompt_id: int, reverted_data: Dict[str, Any], commit_message: str
    ) -> bool:
        """
        Revert a prompt to a specific version.

        Args:
            prompt_id (int): The ID of the prompt to revert
            reverted_data (Dict[str, Any]): The data to revert to
            commit_message (str): The commit message

        Returns:
            bool: True if successful, False otherwise
        """
        if prompt_id not in self.prompts:
            return False

        current_prompt_info = self.prompts[prompt_id]

        # Create a new version with the reverted data
        parent_version_id = current_prompt_info["branches"].get("main")
        parents = [parent_version_id] if parent_version_id else []

        version_id = self._generate_version_id(reverted_data, commit_message)
        new_version = {
            "version_id": version_id,
            "timestamp": self._get_current_timestamp(),
            "author": self._get_current_user(),
            "message": commit_message,
            "data": reverted_data,
            "parents": parents,
        }
        current_prompt_info["versions"].append(new_version)
        current_prompt_info["data"] = reverted_data
        current_prompt_info["branches"]["main"] = version_id

        # Note: Do not clear categories and tags to preserve predefined ones
        return True

    def create_prompt(self, data: Dict[str, Any]) -> int:
        """
        Create a new prompt (alias for add_new_prompt).

        Args:
            data (Dict[str, Any]): The prompt data

        Returns:
            int: The ID of the new prompt
        """
        return self.add_new_prompt(data)

    def get_categories(self) -> List[str]:
        """
        Get all categories.

        Returns:
            List[str]: List of categories
        """
        # Always update categories from current prompts to ensure they are current
        self._update_categories_and_tags()
        return self.categories

    def get_tags(self) -> List[str]:
        """
        Get all tags.

        Returns:
            List[str]: List of tags
        """
        # Always update tags from current prompts to ensure they are current
        self._update_categories_and_tags()
        return sorted(list(self.global_tags))

    def get_tags_with_counts(self) -> List[Dict[str, Any]]:
        """
        Get all tags with their usage counts.

        Returns:
            List[Dict[str, Any]]: List of dictionaries with 'name' and 'count' keys,
                                  sorted by tag name
        """
        # Always update tags from current prompts to ensure they are current
        self._update_categories_and_tags()

        # Count tag usage across all prompts
        tag_counts: Dict[str, int] = {}
        for prompt_info in self.prompts.values():
            prompt_tags = prompt_info["data"].get("tags", [])
            if isinstance(prompt_tags, list):
                for tag in prompt_tags:
                    if isinstance(tag, str):
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Build result list with all tags (including unused ones with count 0)
        result = []
        for tag in sorted(self.global_tags):
            result.append({"name": tag, "count": tag_counts.get(tag, 0)})

        return result
