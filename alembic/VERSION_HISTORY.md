# Alembic Migration History

This document tracks the ordered list of database migrations that ship with PromptVault
and provides guidance for maintaining a linear history.

## Current Revision Chain

| Order | Revision ID    | File                                                          | Description                                                                           | Notes       |
| ----- | -------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ----------- |
| 1     | `134639ee25d5` | `versions/134639ee25d5_initial_schema_with_users_prompts_.py` | Initial schema with users, prompts, versions, categories, tags, branches, and backups | Base schema |
| 2     | `7182f1f03364` | `versions/7182f1f03364_fix_prompts_id_autoincrement.py`       | Fix prompts id autoincrement, needed to add new prompts                               |

## Maintenance Notes

- **Keep migrations linear.** When adding a new revision, always set its `down_revision`
  to the latest head so clean installs can run `alembic upgrade head` without needing
  merge revisions.
- **Document intent.** Update the table above when introducing a migration so other
  developers can understand ordering requirements.
- **Resetting local DBs.** If you adjust the revision chain (for example, by changing
  `down_revision` relationships), drop and recreate local databases or run
  `alembic downgrade base` before applying the new sequence to avoid version conflicts.

Last updated: 2025-11-28
