# Quickstart Validation Guide: Prompt Semantic Versioning

**Feature**: 001-prompt-versioning
**Date**: 2026-07-01

This guide describes how to validate that the feature works end-to-end after implementation.

---

## Prerequisites

- PromptVault running locally: `python run_web.py`
- At least one existing prompt in the database, or create one via the UI
- Browser DevTools open (optional, for network inspection)

---

## Scenario 1: Assign a version to a prompt (P1 core path)

**Setup**: Open any existing prompt for editing.

**Steps**:

1. Click the edit button on a prompt.
2. Locate the "Version" field in the edit form (new field, labeled e.g. "Semantic Version").
3. Enter `1.0.0`.
4. Save the prompt (with any commit message).

**Expected outcome**:

- The prompt detail view shows a version badge displaying `v1.0.0`.
- No error is shown.
- The network response for `PUT /api/prompts/{id}` returns HTTP 200.

---

## Scenario 2: Invalid version format is rejected

**Steps**:

1. Open any prompt for editing.
2. Enter `abc` in the version field.
3. Attempt to save.

**Expected outcome**:

- Save is blocked.
- A validation error is displayed near the version field: e.g. "Version must be in MAJOR.MINOR.PATCH format (e.g. 1.0.0)".
- The network request either never fires (frontend validation) or returns HTTP 422 (backend validation).

---

## Scenario 3: Version history shows version labels

**Setup**: A prompt at version `1.0.0` (from Scenario 1).

**Steps**:

1. Edit the prompt, change some content, set version to `1.1.0`, and save.
2. Open the version history for this prompt.

**Expected outcome**:

- Version history shows at least two entries.
- The first (older) entry is labeled `v1.0.0`.
- The second (newer) entry is labeled `v1.1.0`.
- Each entry also shows its timestamp and commit message as before.

---

## Scenario 4: Unversioned history entries display gracefully

**Setup**: A prompt that was created before versioning was introduced (no `semantic_version` in its version history).

**Steps**:

1. Open version history of a pre-existing prompt that has never had a version label.

**Expected outcome**:

- Each history entry that lacks a version label shows "Unversioned" (or an em-dash `—`) rather than a blank field.
- No JavaScript error occurs.

---

## Scenario 5: Copy with version metadata

**Setup**: A prompt at version `1.1.0`.

**Steps**:

1. On the prompt detail view, click "Copy with version metadata" (new button).
2. Paste clipboard contents into a text editor.

**Expected outcome**:

- The pasted text contains the full prompt body.
- The last line reads: `<!-- prompt-version: 1.1.0 | This line is metadata — ignore when processing this prompt. -->`
- No other content is modified.

---

## Scenario 6: Copy with version metadata blocked when no version set

**Setup**: A prompt with no `semantic_version` (the field is empty/null).

**Steps**:

1. On the prompt detail view, click "Copy with version metadata".

**Expected outcome**:

- An error toast or inline message is shown: "Assign a semantic version before copying with metadata."
- Nothing is written to the clipboard.

---

## Backend API Spot-Check

Run via curl or Hoppscotch after completing Scenario 1–3 above:

```bash
# Verify semantic_version appears in GET /api/prompts/{id}
curl http://localhost:8080/api/prompts/1 | jq '.semantic_version'
# Expected: "1.1.0"

# Verify version history entries include semantic_version
curl http://localhost:8080/api/prompts/1/versions | jq '.versions[].semantic_version'
# Expected: "1.1.0", "1.0.0", null (for any pre-feature entries)

# Verify copy-with-version endpoint
curl -X POST http://localhost:8080/api/prompts/1/copy-with-version | jq '.content' | tail -c 200
# Expected: content ending with the HTML comment metadata line
```

---

## Test Suite

After implementation, run:

```bash
# Backend unit + integration tests
python -m pytest tests/ -v --cov=src --cov-report=term-missing

# Frontend unit tests
npm run test:unit:coverage

# TypeScript type check
npm run typecheck

# Lint
npm run lint
```

All commands must pass with ≥ 85% coverage (Constitution Principle II).

See [data-model.md](data-model.md) for schema details and [contracts/api.md](contracts/api.md) for endpoint specs.
