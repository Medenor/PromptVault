# Data Model: Prompt Semantic Versioning

**Feature**: 001-prompt-versioning
**Date**: 2026-07-01

---

## Modified Entities

### Prompt (`prompts` table)

**New column**:

| Column             | Type          | Nullable | Default | Constraint                                            |
| ------------------ | ------------- | -------- | ------- | ----------------------------------------------------- |
| `semantic_version` | `VARCHAR(20)` | Yes      | `NULL`  | Regex `^\d+\.\d+\.\d+$` enforced at application layer |

**No other changes** to the `Prompt` model; existing indices and relationships are unaffected.

**Validation rule**: If non-null, `semantic_version` must match `^\d+\.\d+\.\d+$`. Empty string is normalized to `NULL` before storage.

---

### PromptVersion (`prompt_versions` table)

**New column**:

| Column             | Type          | Nullable | Default | Notes                                              |
| ------------------ | ------------- | -------- | ------- | -------------------------------------------------- |
| `semantic_version` | `VARCHAR(20)` | Yes      | `NULL`  | Snapshot of `Prompt.semantic_version` at save time |

**Denormalization pattern** (existing, extended): `PromptVersion` already stores snapshots of `title`, `note`, `tags`, `favorite`. `semantic_version` follows the same pattern — it records the label that was on the prompt when this revision was created.

**State transitions**:

```
Prompt (no version) → user sets "1.0.0" → save
  Prompt.semantic_version = "1.0.0"
  PromptVersion.semantic_version = "1.0.0"   ← snapshot

Prompt (1.0.0) → user edits content, bumps to "1.1.0" → save
  Prompt.semantic_version = "1.1.0"
  new PromptVersion.semantic_version = "1.1.0"
  old PromptVersion.semantic_version = "1.0.0"  ← preserved

Prompt (1.1.0) → user edits content, leaves version unchanged → save
  Prompt.semantic_version = "1.1.0"
  new PromptVersion.semantic_version = "1.1.0"   ← same label, new revision
```

---

## Alembic Migration

**Migration file**: `alembic/versions/<hash>_add_semantic_version_to_prompts.py`

Operations:

1. `op.add_column('prompts', sa.Column('semantic_version', sa.String(20), nullable=True))`
2. `op.add_column('prompt_versions', sa.Column('semantic_version', sa.String(20), nullable=True))`

Downgrade: drop both columns.

No data backfill — NULL is the correct initial value for pre-existing records.

---

## API Schema Changes

### `PromptResponse` (extended)

Add optional field:

```
semantic_version: Optional[str] = None
```

### `PromptCreateRequest` (extended)

Add optional field with Pydantic validator:

```
semantic_version: Optional[str] = None
# field_validator: strip whitespace, normalize "" → None, validate regex if non-null
```

### `PromptUpdateRequest` (extended)

Same addition as `PromptCreateRequest`.

### `VersionSummary` (TypeScript interface — extended)

```typescript
interface VersionSummary {
  version_id: string;
  version_number: number;
  timestamp: string;
  author: string;
  message: string;
  parents: string[];
  semantic_version: string | null; // NEW
}
```

---

## Entities Not Changed

- `Category`, `Tag`, `User`, `PromptBranch`: unchanged.
- `undo_operations` table: unchanged (version label changes are captured via the existing version snapshot mechanism, not undo).
