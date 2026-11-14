# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Schema helpers for tests that need the database as it was before skills."""

import sqlalchemy as sa

FEATURE_TABLES = {"skill_packages", "skill_files"}


def pre_feature_metadata() -> sa.MetaData:
    """Copy of the ORM metadata without this feature's tables and column.

    alembic/env.py cannot replay the whole chain on SQLite (an older migration
    uses PostgreSQL-only DDL), so the pre-feature schema is built from a copy
    of the ORM metadata with the feature's objects removed.
    """
    import src.db.models  # noqa: F401 -- populate Base.metadata
    from src.db.base import Base

    copy = sa.MetaData()
    for table in Base.metadata.sorted_tables:
        if table.name in FEATURE_TABLES:
            continue
        table.to_metadata(copy)
    prompts = copy.tables["prompts"]
    for constraint in list(prompts.constraints):
        if getattr(constraint, "name", None) == "ck_prompts_item_type":
            prompts.constraints.discard(constraint)
    for index in list(prompts.indexes):
        if index.name == "idx_prompts_item_type":
            prompts.indexes.discard(index)
    prompts._columns.remove(prompts.c.item_type)
    return copy
