# Quickstart: Validating Dynamic Prompt Placeholders

## Prerequisites

- Repo checked out on branch `006-prompt-placeholders`.
- Node dependencies installed (`npm install`) and Python env set up per repo `README.md`/`Makefile` if running the full app.

## Unit-level validation (fast, no server needed)

```bash
npx vitest run src/web/static/ts/utils/__tests__/placeholders.test.ts
```

**Expected outcome**: All tests pass, covering:
- Detecting distinct `[NAME]` and `{NAME}` tokens, including repeated occurrences of the same token collapsing to one entry.
- Treating `[DURATION]` and `{DURATION}` as distinct entries.
- Ignoring malformed spans (`[]`, unmatched `[abc`, nested `[[X]]`, multi-line spans).
- Substituting only filled tokens, leaving unfilled ones as the original literal text.
- Not re-expanding a substituted value that itself looks like a placeholder.

## End-to-end validation (full app, Playwright)

1. Start the app per the project's normal dev workflow (see `Makefile` / `run_web.py`).
2. Run the new e2e spec:

```bash
npx playwright test tests/e2e/prompt-placeholders.spec.ts
```

**Expected outcome / manual walkthrough this spec automates**:
1. Create or open a prompt whose content includes `Your task is to create a [DURATION] [TYPE OF PRESENTATION] titled "[INSERT PRESENTATION TITLE]".`
2. Click "Copy" — a modal appears with three labeled fields: `DURATION`, `TYPE OF PRESENTATION`, `INSERT PRESENTATION TITLE`.
3. Fill in `1 hour`, `Sales`, `How to build an app`; confirm.
4. Read the clipboard (or an on-page echo used for test purposes) and assert it equals:
   `Your task is to create a 1 hour Sales presentation titled "How to build an app".`
5. Repeat with all fields left blank and confirm — clipboard content equals the original raw prompt text unchanged.
6. Open a prompt with no placeholders — confirm no modal appears and "Copy" behaves exactly as before.

## Regression checks (should require no code changes — validates non-breakage)

- Existing Python test suite for versioning/search/export continues to pass unmodified: `pytest tests/test_prompt_versioning_service.py tests/test_prompt_import_export_service.py`.
- Existing `test_copy_with_version.py` backend test continues to pass unmodified, since `/api/prompts/{id}/copy-with-version` itself is untouched by this feature.
