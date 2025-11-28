"""PromptVault repository layer.

This package provides the repository pattern for data access, separating
business logic from database operations.

Repositories available:
    - BaseRepository: Generic base repository with common CRUD operations
    - PromptRepository: Advanced prompt search and filtering
    - VersionRepository: Version control operations
    - CategoryRepository: Category management with statistics
    - TagRepository: Tag management with usage tracking

Usage:
    from src.db.repositories import PromptRepository, TagRepository
    from src.db import get_db_session

    with get_db_session() as session:
        prompt_repo = PromptRepository(session)
        prompts = prompt_repo.search(query="email", favorite=True)
"""

from src.db.repositories.base import BaseRepository
from src.db.repositories.prompt_repository import PromptRepository
from src.db.repositories.version_repository import VersionRepository
from src.db.repositories.category_repository import CategoryRepository
from src.db.repositories.tag_repository import TagRepository

__all__ = [
    "BaseRepository",
    "PromptRepository",
    "VersionRepository",
    "CategoryRepository",
    "TagRepository",
]
