# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Base repository class for PromptVault.

This module provides a generic base repository with common CRUD operations
that can be inherited by specific model repositories.
"""

from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

from src.db.base import Base

# Generic type for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic base repository with common CRUD operations.

    This class provides standard create, read, update, delete operations
    that can be reused across different model repositories.

    Type Parameters:
        ModelType: The SQLAlchemy model class this repository manages

    Attributes:
        model: The SQLAlchemy model class
        session: The database session
    """

    def __init__(self, model: type[ModelType], session: Session):
        """Initialize repository.

        Args:
            model: The SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session

    def get_by_id(self, id: Any) -> ModelType | None:
        """Get a single record by ID.

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found
        """
        return self.session.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int | None = None) -> list[ModelType]:
        """Get all records with optional pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of model instances
        """
        query = self.session.query(self.model).offset(skip)
        if limit:
            query = query.limit(limit)
        return query.all()

    def create(self, **kwargs) -> ModelType:
        """Create a new record.

        Args:
            **kwargs: Model attributes

        Returns:
            Created model instance

        Raises:
            SQLAlchemyError: If creation fails
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.flush()
        return instance

    def update(self, id: Any, **kwargs) -> ModelType | None:
        """Update an existing record.

        Args:
            id: Primary key value
            **kwargs: Attributes to update

        Returns:
            Updated model instance or None if not found
        """
        instance = self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            self.session.flush()
        return instance

    def delete(self, id: Any) -> bool:
        """Delete a record by ID.

        Args:
            id: Primary key value

        Returns:
            True if deleted, False if not found
        """
        instance = self.get_by_id(id)
        if instance:
            self.session.delete(instance)
            self.session.flush()
            return True
        return False

    def delete_many(self, ids: list[Any]) -> int:
        """Delete multiple records by ID.

        Args:
            ids: List of primary key values

        Returns:
            Number of records deleted
        """
        count = (
            self.session.query(self.model)
            .filter(self.model.id.in_(ids))
            .delete(synchronize_session=False)
        )
        self.session.flush()
        return count

    def count(self) -> int:
        """Get total count of records.

        Returns:
            Total number of records
        """
        return self.session.query(self.model).count()

    def exists(self, id: Any) -> bool:
        """Check if a record exists by ID.

        Args:
            id: Primary key value

        Returns:
            True if exists, False otherwise
        """
        return (
            self.session.query(self.model).filter(self.model.id == id).first()
            is not None
        )
