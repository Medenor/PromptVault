from typing import List, Dict, Any, Optional


class PromptFilterService:
    """Service for handling prompt filtering and searching operations."""

    def __init__(self):
        """Initialize the PromptFilterService."""
        pass

    def filter_prompts(self, 
                       prompts: Dict[int, Dict[str, Any]], 
                       filter_category: Optional[str] = None, 
                       filter_tag: Optional[str] = None, 
                       search_term: str = "", 
                       filter_favorites: bool = False,
                       case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Filter prompts based on various criteria.
        
        Args:
            prompts (Dict[int, Dict[str, Any]]): Dictionary of prompts to filter
            filter_category (Optional[str]): Category to filter by
            filter_tag (Optional[str]): Tag to filter by
            search_term (str): Text to search for
            filter_favorites (bool): Whether to filter by favorites only
            case_sensitive (bool): Whether search is case sensitive
            
        Returns:
            List[Dict[str, Any]]: Filtered list of prompts
        """
        processed_search_term = search_term if case_sensitive else search_term.lower()
        
        filtered_prompts = []
        for prompt_id, prompt_info in prompts.items():
            data = prompt_info['data']
            category = data.get('category') or 'No category'
            tags = data.get('tags') or []
            if not isinstance(tags, list):
                tags = []
            is_favorite = bool(data.get('favorite', False))

            title_text = data.get('title') or ''
            prompt_text = data.get('prompt') or ''
            note_text = data.get('note') or ''

            processed_title = title_text if case_sensitive else title_text.lower()
            processed_prompt = prompt_text if case_sensitive else prompt_text.lower()
            processed_note = note_text if case_sensitive else note_text.lower()

            category_match = filter_category is None or category == filter_category
            tag_match = filter_tag is None or filter_tag in tags
            search_match = (
                processed_search_term == "" or
                processed_search_term in processed_title or
                processed_search_term in processed_prompt or
                processed_search_term in processed_note
            )
            favorite_match = (not filter_favorites) or is_favorite
            
            if category_match and tag_match and search_match and favorite_match:
                filtered_prompts.append({'id': prompt_id, **data})
        return filtered_prompts

    def sort_prompts(self, prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort prompts by title.
        
        Args:
            prompts (List[Dict[str, Any]]): List of prompts to sort
            
        Returns:
            List[Dict[str, Any]]: Sorted list of prompts
        """
        return sorted(prompts, key=lambda p: p.get('title', ''))
