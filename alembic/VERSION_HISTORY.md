# Alembic Migration History

This document tracks the ordered list of database migrations that ship with PromptVault
and provides guidance for maintaining a linear history.

## Current Revision Chain

| Order | Revision ID    | File                                                               | Description                                                                                  | Notes       |
| ----- | -------------- | ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- | ----------- |
| 1     | `134639ee25d5` | `versions/134639ee25d5_initial_schema_with_users_prompts_.py`      | Initial schema with users, prompts, versions, categories, tags, branches, and backups        | Base schema |
| 2     | `7182f1f03364` | `versions/7182f1f03364_fix_prompts_id_autoincrement.py`            | Fix prompts id autoincrement, needed to add new prompts                                      |             |
| 3     | `da013146c222` | `versions/da013146c222_add_authentication_fields_to_users.py`      | Add authentication fields and session tables                                                 |             |
| 4     | `ccdab5b31836` | `versions/ccdab5b31836_assign_existing_prompts_to_default_user.py` | Assign orphaned prompts to default system user                                               |             |
| 5     | `b7a1c2d3e4f5` | `versions/b7a1c2d3e4f5_tag_category_management.py`                 | Tag/category metadata, case-insensitive indexes, and tag hierarchy (parent_tag_id)           |             |
| 6     | `c8d9e0f1a2b3` | `versions/c8d9e0f1a2b3_add_undo_operations_table.py`               | Add undo_operations table for persistent, user-scoped undo operations with 30-day expiration |             |

## Maintenance Notes

- **Keep migrations linear.** When adding a new revision, always set its `down_revision`
  to the latest head so clean installs can run `alembic upgrade head` without needing
  merge revisions.
- **Document intent.** Update the table above when introducing a migration so other
  developers can understand ordering requirements.
- **Resetting local DBs.** If you adjust the revision chain (for example, by changing
  `down_revision` relationships), drop and recreate local databases or run
  `alembic downgrade base` before applying the new sequence to avoid version conflicts.

Last updated: 2026-01-22
