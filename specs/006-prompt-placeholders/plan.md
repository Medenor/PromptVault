# Implementation Plan: Dynamic Prompt Placeholders

**Branch**: `006-prompt-placeholders` | **Date**: 2026-07-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-prompt-placeholders/spec.md`

## Summary

Detect `[NAME]` / `{NAME}` placeholder tokens in a prompt's content on the client, show a small modal form with one input per distinct token before copying, substitute filled values into the copied text, and leave unfilled tokens untouched. Purely a frontend (TypeScript) change: no new API endpoints, no schema changes, no changes to versioning/search/filter/export code paths, since those already operate on the stored prompt content string unmodified.

## Technical Context

**Language/Version**: TypeScript (compiled via Vite), strict mode per existing `tsconfig.json`

**Primary Dependencies**: None new. Reuses existing `createModal` from `@components`, `showNotification` from `@/utils/notifications`, `apiGet`/`promptCache` already used by `copyPrompt` in `src/web/static/ts/app.ts`.

**Storage**: N/A — no persistence of placeholders or filled values; derived on the fly from prompt content already fetched/cached.

**Testing**: Vitest (unit tests for token-detection/substitution logic, colocated per project convention in `src/web/static/ts/utils/__tests__/`), Playwright (existing e2e suite in `tests/e2e/`) for the end-to-end fill-and-copy flow.

**Target Platform**: Browser (existing PromptVault web UI), same support matrix as current clipboard fallback code (modern Clipboard API with `document.execCommand` fallback).

**Project Type**: Web application (existing FastAPI + server-rendered Jinja2 + vanilla TypeScript single-page-ish app) — this feature adds a new frontend utility module plus call-site changes; no backend project touched.

**Performance Goals**: Negligible — regex-based token scan and string replacement on prompt-sized text (typically well under 10 KB); no measurable UI latency impact target beyond "instant" (<50ms).

**Constraints**: Must not alter the raw `content`/`prompt` string returned by existing APIs, cached in `promptCache`, stored in version history, or used by search/filter/export — substitution happens only in the transient string passed to `navigator.clipboard.writeText` / the fallback textarea, never written back to any stored or cached prompt object.

**Scale/Scope**: Single new utility module (~100-150 LOC) + modifications to `copyPrompt` and `copyPromptWithVersion` call sites in `app.ts` + one small modal template. No changes to Python backend, database, migrations, or export services.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

Evaluated against `.specify/memory/constitution.md` v1.0.0:

- **I. Layered Service Architecture**: N/A — this feature touches no backend route, service, or repository code; it is entirely a client-side (frontend) concern operating on data already returned by existing, unmodified endpoints.
- **II. Test Coverage Gate (NON-NEGOTIABLE)**: PASS (planned) — Vitest unit tests for `detectPlaceholders`/`substitutePlaceholders` and a Playwright e2e spec are included in scope; tasks phase MUST order these alongside/before the `app.ts` call-site changes so the ≥85% frontend coverage floor is maintained, not backfilled after merge.
- **III. Security-First Authentication**: N/A — no new endpoints, no data mutation, nothing to authenticate; existing `copyPrompt`/`copyPromptWithVersion` auth behavior is unchanged.
- **IV. TypeScript-Only Frontend**: PASS — all new code lives under `src/web/static/ts/`; the legacy `src/web/static/js/` directory is untouched. New modal field labels MUST use typed `t('key.path')` i18n calls (not raw strings) per this principle — noted as a Phase 2 task requirement, not yet reflected in research.md/data-model.md, which predate this constitution check and only mention field `label` as plain string.
- **V. Database-Backed Persistence**: PASS (N/A) — explicitly no schema changes, no new persisted entities (see data-model.md); placeholders and filled values are transient/in-memory only, consistent with this principle's intent that nothing here needs Alembic migrations.

No violations requiring justification. One follow-up for Phase 2 tasks: ensure the modal template applies the project's i18n (`t()`) convention for field labels per Principle IV, since this constitution predates the earlier passes over this plan.

## Project Structure

### Documentation (this feature)

```text
specs/006-prompt-placeholders/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output (client-side interface contract)
└── tasks.md              # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/web/static/ts/
├── app.ts                          # MODIFIED: copyPrompt() and copyPromptWithVersion()
│                                    #   call the new placeholder flow before clipboard write
├── utils/
│   ├── placeholders.ts             # NEW: detectPlaceholders(), substitutePlaceholders()
│   └── __tests__/
│       └── placeholders.test.ts    # NEW: Vitest unit tests
└── (createModal from @components reused, no new component needed)

tests/e2e/
└── prompt-placeholders.spec.ts     # NEW: Playwright end-to-end fill-and-copy flow
```

**Structure Decision**: Follows the existing single-project web-app layout already in this repo (`src/web/static/ts/` for frontend logic, `src/web/static/ts/utils/__tests__/` for colocated unit tests per `vitest.config.ts`'s `include` glob, `tests/e2e/` for Playwright specs). No new top-level directories or backend changes.

## Complexity Tracking

No constitution violations to justify — table intentionally omitted.
