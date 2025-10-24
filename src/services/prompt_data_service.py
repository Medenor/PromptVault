import json
import os
import uuid
from datetime import datetime
import getpass
from typing import Dict, Any, Set, List, Tuple


class PromptDataService:
    """Service for handling prompt data operations including loading, saving, and migration."""

    def __init__(self, data_file_path: str = None):
        """
        Initialize the PromptDataService.
        
        Args:
            data_file_path (str): Path to the data file. If None, uses default location.
        """
        if data_file_path is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.data_file = os.path.join(script_dir, "data", "prompts_data.json")
        else:
            self.data_file = data_file_path
            
        self.prompts = {}
        self.next_id = 0
        self.categories = []
        self.global_tags = set()

    def save_prompts(self) -> bool:
        """
        Save prompts to the data file.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update categories and tags from current prompts before saving
            self._update_categories_and_tags()

            with open(self.data_file, 'w', encoding='utf-8') as f:
                prompts_to_save = {}
                for k, v in self.prompts.items():
                    # Ensure 'history' is not saved in the new structure
                    v_copy = v.copy()
                    if 'history' in v_copy:
                        del v_copy['history']
                    prompts_to_save[str(k)] = v_copy

                save_data = {
                    'next_id': self.next_id,
                    'prompts': prompts_to_save,
                    'categories': self.categories,
                    'global_tags': sorted(list(self.global_tags))
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
            with open(self.data_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                self.next_id = loaded_data.get('next_id', 0)
                loaded_prompts = {}
                for k, v in loaded_data.get('prompts', {}).items():
                    try:
                        prompt_id = int(k)
                        if isinstance(v, dict):
                            v = self._migrate_old_data_structure(prompt_id, v)
                            loaded_prompts[prompt_id] = v
                        else:
                            print(f"Warning: Invalid structure for prompt ID '{k}', ignored.")
                    except ValueError:
                        print(f"Warning: Invalid prompt key '{k}', ignored.")

                self.prompts = loaded_prompts

                # Load categories and tags from file if they exist (for backward compatibility)
                self.categories = loaded_data.get('categories', [])
                self.global_tags = set(loaded_data.get('global_tags', []))

                # If no categories/tags in file, build them from current prompts
                if not self.categories:
                    self.categories = list(set(
                        prompt_info['data'].get('category', 'No category')
                        for prompt_info in self.prompts.values()
                    ))
                    self.categories.sort()

                if not self.global_tags:
                    all_tags = set()
                    for prompt_info in self.prompts.values():
                        prompt_tags = prompt_info['data'].get('tags', [])
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
        if 'data' in prompt_info and 'history' in prompt_info and 'versions' not in prompt_info:
            print(f"Migrating old prompt structure for ID {prompt_id}")
            current_data = prompt_info['data']
            history_entries = prompt_info['history']

            versions = []
            # Create initial version from the first history entry or current data
            if history_entries:
                first_data = history_entries[0]
                first_version_id = self._generate_version_id(first_data, "Initial import")
                versions.append({
                    'version_id': first_version_id,
                    'timestamp': self._get_current_timestamp(),
                    'author': self._get_current_user(),
                    'message': "Initial import",
                    'data': first_data,
                    'parents': []
                })
                # Add subsequent history entries as new versions
                for i in range(1, len(history_entries)):
                    prev_version_id = versions[-1]['version_id']
                    new_data = history_entries[i]
                    new_version_id = self._generate_version_id(new_data, "History migration")
                    versions.append({
                        'version_id': new_version_id,
                        'timestamp': self._get_current_timestamp(),
                        'author': self._get_current_user(),
                        'message': "History migration",
                        'data': new_data,
                        'parents': [prev_version_id]
                    })
            else:  # No history, just current data
                initial_version_id = self._generate_version_id(current_data, "Initial import")
                versions.append({
                    'version_id': initial_version_id,
                    'timestamp': self._get_current_timestamp(),
                    'author': self._get_current_user(),
                    'message': "Initial import",
                    'data': current_data,
                    'parents': []
                })
            
            # Ensure current_data is the latest in versions
            if versions and versions[-1]['data'] != current_data:
                latest_version_id = self._generate_version_id(current_data, "Current state after migration")
                versions.append({
                    'version_id': latest_version_id,
                    'timestamp': self._get_current_timestamp(),
                    'author': self._get_current_user(),
                    'message': "Current state after migration",
                    'data': current_data,
                    'parents': [versions[-1]['version_id']] if versions else []
                })

            prompt_info = {
                'data': current_data,
                'versions': versions,
                'branches': {"main": versions[-1]['version_id']} if versions else {}
            }
        
        # Ensure new fields exist for all prompts
        if 'versions' not in prompt_info:
            prompt_info['versions'] = []
        if 'branches' not in prompt_info:
            prompt_info['branches'] = {}
        if 'data' not in prompt_info:
            prompt_info['data'] = {}

        # Ensure category and favorite defaults
        if 'category' not in prompt_info['data'] or not prompt_info['data']['category']:
            prompt_info['data']['category'] = 'No category'
        if 'favorite' not in prompt_info['data']:
            prompt_info['data']['favorite'] = False
        
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
        return datetime.utcnow().isoformat() + 'Z'

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
            all_tags.update(prompt_info['data'].get('tags', []))
        return all_tags

    def _update_categories_and_tags(self) -> None:
        """
        Update categories and tags from current prompts.
        This ensures they stay in sync with the actual prompt data.
        Preserves predefined categories and tags while adding any new ones in use.
        """
        # Update categories from current prompts - merge with existing predefined categories
        current_categories = set(
            prompt_info['data'].get('category', 'No category')
            for prompt_info in self.prompts.values()
        )
        # Preserve existing predefined categories and add any new ones in use
        self.categories = sorted(list(set(self.categories) | current_categories))

        # Update tags from current prompts - merge with existing predefined tags
        all_tags = set()
        for prompt_info in self.prompts.values():
            prompt_tags = prompt_info['data'].get('tags', [])
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
        prompt_id = self.next_id
        self.next_id += 1

        commit_message = data.pop('commit_message', "Initial commit")
        version_id = self._generate_version_id(data, commit_message)
        new_version = {
            'version_id': version_id,
            'timestamp': self._get_current_timestamp(),
            'author': self._get_current_user(),
            'message': commit_message,
            'data': data,
            'parents': []
        }
        self.prompts[prompt_id] = {
            'data': data,
            'versions': [new_version],
            'branches': {"main": version_id}
        }

        # Clear cached categories and tags so they get rebuilt
        self.categories = []
        self.global_tags = set()

        return prompt_id

    def update_prompt(self, prompt_id: int, data: Dict[str, Any], commit_message: str = "Update") -> bool:
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

        current_prompt_info = self.prompts[prompt_id]
        current_data = current_prompt_info['data']

        # Get the parent version_id (current head of 'main' branch)
        parent_version_id = current_prompt_info['branches'].get("main")
        parents = [parent_version_id] if parent_version_id else []

        version_id = self._generate_version_id(data, commit_message)
        new_version = {
            'version_id': version_id,
            'timestamp': self._get_current_timestamp(),
            'author': self._get_current_user(),
            'message': commit_message,
            'data': data,
            'parents': parents
        }
        current_prompt_info['versions'].append(new_version)
        current_prompt_info['data'] = data
        current_prompt_info['branches']["main"] = version_id

        # Clear cached categories and tags so they get rebuilt
        self.categories = []
        self.global_tags = set()

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
            # Clear cached categories and tags so they get rebuilt
            self.categories = []
            self.global_tags = set()
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
            return self.prompts[prompt_id]['data']
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
            return self.prompts[prompt_id].get('versions', [])
        return []

    def revert_prompt_to_version(self, prompt_id: int, reverted_data: Dict[str, Any], commit_message: str) -> bool:
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
        parent_version_id = current_prompt_info['branches'].get("main")
        parents = [parent_version_id] if parent_version_id else []

        version_id = self._generate_version_id(reverted_data, commit_message)
        new_version = {
            'version_id': version_id,
            'timestamp': self._get_current_timestamp(),
            'author': self._get_current_user(),
            'message': commit_message,
            'data': reverted_data,
            'parents': parents
        }
        current_prompt_info['versions'].append(new_version)
        current_prompt_info['data'] = reverted_data
        current_prompt_info['branches']["main"] = version_id

        # Clear cached categories and tags so they get rebuilt
        self.categories = []
        self.global_tags = set()

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
        # Update categories from current prompts if empty
        if not self.categories:
            self.categories = list(set(
                prompt_info['data'].get('category', 'No category')
                for prompt_info in self.prompts.values()
            ))
            self.categories.sort()

        return self.categories

    def get_tags(self) -> List[str]:
        """
        Get all tags.

        Returns:
            List[str]: List of tags
        """
        # Update tags from current prompts if empty
        if not self.global_tags:
            all_tags = set()
            for prompt_info in self.prompts.values():
                prompt_tags = prompt_info['data'].get('tags', [])
                if isinstance(prompt_tags, list):
                    all_tags.update(prompt_tags)
            self.global_tags = all_tags

        return sorted(list(self.global_tags))
