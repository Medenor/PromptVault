# Research: Prompt Semantic Versioning

**Feature**: 001-prompt-versioning
**Date**: 2026-07-01

---

## Decision 1: Where to store the semantic version label

**Decision**: Add an optional `semantic_version` column (`VARCHAR(20)`) to both `Prompt` and `PromptVersion` DB models.

**Rationale**:

- `Prompt.semantic_version` is the authoritative current version, visible on the detail view at a glance.
- `PromptVersion.semantic_version` is a snapshot of whatever label was active at save time, enabling the version history to display "what version was this revision tagged as?"
- This follows the existing denormalized-snapshot pattern already used by `PromptVersion` (which already stores `title`, `note`, `tags`, `favorite` as snapshots).
- No new table or join is needed; the column is nullable so pre-existing rows remain valid.

**Alternatives considered**:

- Separate `semantic_versions` table keyed to `version_id`: rejected — adds join complexity for a single optional field.
- Store only on `PromptVersion` and derive the current version by reading the latest revision: rejected — adds a version query to every prompt detail load; direct column on `Prompt` is simpler and aligned with how `updated_at` works.

---

## Decision 2: Validation format

**Decision**: Validate `MAJOR.MINOR.PATCH` with a strict regex `^\d+\.\d+\.\d+$` at the Pydantic request layer.

**Rationale**:

- The spec explicitly bounds scope to `MAJOR.MINOR.PATCH` only; pre-release labels (`-beta`, `+build`) are out of scope.
- Pydantic `field_validator` is the established validation pattern in this codebase (see `PromptCreateRequest`, `PromptUpdateRequest`).
- The regex is short, readable, and produces deterministic pass/fail for unit tests.

**Alternatives considered**:

- Using a `packaging` or `semver` library: rejected — importing a library for a regex check is disproportionate; the spec explicitly rules out pre-release suffixes.
- Validating only at the frontend: rejected — backend validation is required per Constitution Principle III (validate at API boundary).

---

## Decision 3: "Copy with version metadata" format

**Decision**: The metadata line uses an HTML comment: `<!-- prompt-version: X.Y.Z | This line is metadata — ignore when processing this prompt. -->`, appended as the last line of the copied content.

**Rationale**:

- HTML comments are invisible in Markdown-rendered contexts (GitHub, Notion, most GPT/Claude instruction editors that render markdown).
- They are universally inert across ChatGPT GPT instructions, Claude Projects, and Gemini Gems (none of these render HTML comment tags as functional).
- The inline instruction ("ignore when processing") makes the line self-documenting even in plain-text contexts where the comment is visible.
- Appending last (rather than first) avoids interfering with system prompt preambles that some platforms parse from the first line.

**Alternatives considered**:

- YAML front matter (`---\nprompt-version: X.Y.Z\n---`): rejected — some platforms may parse or strip front matter differently; HTML comments are more universally passive.
- A separate metadata endpoint that returns version alongside copy content: rejected — the user scenario requires a single clipboard action without network round-trips.

---

## Decision 4: Monotonic enforcement

**Decision**: The system warns (non-blocking) when the user sets a version lower than the current one, but does not hard-reject.

**Rationale**:

- The spec documents this explicitly: "System warns that the version is lower… but allows the save."
- Version numbering discipline is a workflow concern, not a data integrity concern; blocking saves would frustrate legitimate use cases (e.g., correcting a mistaken version bump).

**Alternatives considered**:

- Hard-reject lower versions: rejected — overly restrictive; the spec explicitly rules this out.

---

## Decision 5: Migration approach for pre-existing data

**Decision**: Add an Alembic migration adding `semantic_version VARCHAR(20) NULL` to both `prompts` and `prompt_versions` tables. No backfill — existing rows remain NULL and display as "Unversioned" in the UI.

**Rationale**:

- Constitution Principle V mandates all schema changes go through Alembic migrations.
- NULL is semantically correct for pre-existing records (they were never assigned a version).
- No backfill avoids any data-integrity risk on existing production data.

---

## Decision 6: Frontend clipboard API

**Decision**: Use the `navigator.clipboard.writeText()` API (already used in `app.ts` for copying prompt content) to implement "Copy with version metadata". No new dependency needed.

**Rationale**:

- The existing TypeScript codebase already calls `navigator.clipboard.writeText()` for the standard copy-prompt action.
- The new action is a composition: `promptContent + "\n" + metadataLine`.
- Constitution Principle IV: all new frontend logic in TypeScript.
