# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""SQLAlchemy Base configuration for PromptVault database models."""

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

# Naming convention for database constraints
# This ensures consistent naming across PostgreSQL and SQLite
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    All models inherit from this class to use the declarative base pattern.
    The metadata object with naming conventions ensures consistent constraint
    naming across different database backends (PostgreSQL, SQLite).
    """

    metadata = metadata
