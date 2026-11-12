---

description: "Task list template for feature implementation"
---

# Tasks: Documentation Portal with Multilingual Support

**Input**: Design documents from `/specs/010-docs-portal-i18n/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Not explicitly requested as a separate test suite in spec.md — the parity checker (US2) is itself the feature's automated verification mechanism, and its own correctness is proven via the break/restore drill in quickstart.md Scenario 2 rather than a conventional unit-test file. No `tests/` tasks are included.

**Organization**: Tasks are grouped by user story (US1/US2/US3) to enable independent implementation and testing of each, per spec.md's priorities (P1/P2/P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

All new files live under the new top-level `docs-portal/` directory (isolated from `src/` and the app's own frontend), plus one new CI workflow file at `.forgejo/workflows/docs-portal.yml`, per plan.md's Project Structure.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold the Docusaurus project and its isolated dependency tree, per research.md's decision to keep `docs-portal/` fully separate from the app's own `package.json`.

- [X] T001 Scaffold Docusaurus 3.x TypeScript project at `docs-portal/` (`docusaurus.config.ts`, `sidebars.ts`, `tsconfig.json`) with its own `package.json`/lockfile, independent of the repo root `package.json`
- [X] T002 Configure `docs-portal/docusaurus.config.ts` i18n block: `defaultLocale: 'en'`, `locales: ['en', 'fr', 'de', 'es']`, matching the app's existing locale set (`src/web/static/locales/{en,fr,de,es}.json`)
- [X] T003 [P] Add `docs:*` npm scripts to `docs-portal/package.json` (`docs:start`, `docs:build`, `docs:check-parity`) per quickstart.md's invocation examples
- [X] T004 [P] Add root-level Makefile target `docs` (or equivalent) that shells into `docs-portal/` per FR-014's "one discoverable entry point" requirement, documented in `docs/DEVELOPMENT.md`

**Checkpoint**: `cd docs-portal && npm install && npm run docs:start` runs a blank Docusaurus site with all 4 locales configured

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The frontmatter schema and content-tree layout every user story's content and tooling depend on. Per contracts/page-frontmatter-schema.md, this MUST exist before any real page or the parity checker can be authored meaningfully.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create the English content-tree skeleton in `docs-portal/docs/` per plan.md's Project Structure: `installation/`, `configuration/`, `user-guide/` (with `versioning.md`, `backups.md`, `sharing.md`, `search.md`, `two-factor-auth.md` placeholders), `troubleshooting/`, `release-notes/index.md`
- [X] T006 Create the mirrored empty locale trees at `docs-portal/i18n/{fr,de,es}/docusaurus-plugin-content-docs/current/` matching T005's structure exactly
- [X] T007 Document the frontmatter schema (`title`, `sidebar_position`, `translation_exempt`) from contracts/page-frontmatter-schema.md as a comment template / example page authors copy, e.g. `docs-portal/docs/_template.md` (excluded from the sidebar)
- [X] T008 [P] Configure the "translation not yet available" fallback banner (FR-006) via a swizzled `DocItem/Content` wrapper (`docs-portal/src/theme/DocItem/Content/index.tsx`) — Docusaurus has no built-in config option for this (only a versioned-docs banner exists out of the box), so the banner is rendered client/SSR-side by detecting when `useDoc().metadata.source` still points at the English `docs/` tree while `currentLocale !== defaultLocale`, which only happens on i18n fallback

**Checkpoint**: Foundation ready — content authoring (US1) and the parity checker (US2) can now proceed in parallel

---

## Phase 3: User Story 1 - Find setup and usage guidance in your own language (Priority: P1) 🎯 MVP

**Goal**: A visitor can read complete installation, configuration, user-guide, and troubleshooting content in any of the 4 locales, with correct locale-switching and default-locale behavior.

**Independent Test**: Open the portal in each locale and confirm content is present, navigable, and renders correctly (quickstart.md Scenario 1) — deployable and demonstrable before the parity checker (US2) or CI isolation (US3) exist.

### Implementation for User Story 1

- [X] T009 [P] [US1] Write English installation/deployment content (Docker via `make build`) in `docs-portal/docs/installation/index.md`
- [X] T010 [P] [US1] Write English configuration reference in `docs-portal/docs/configuration/index.md`
- [X] T011 [P] [US1] Write English user-guide page: prompt versioning in `docs-portal/docs/user-guide/versioning.md`
- [X] T012 [P] [US1] Write English user-guide page: backups in `docs-portal/docs/user-guide/backups.md`
- [X] T013 [P] [US1] Write English user-guide page: sharing in `docs-portal/docs/user-guide/sharing.md`
- [X] T014 [P] [US1] Write English user-guide page: search in `docs-portal/docs/user-guide/search.md`
- [X] T015 [P] [US1] Write English user-guide page: two-factor authentication in `docs-portal/docs/user-guide/two-factor-auth.md`
- [X] T016 [P] [US1] Write English troubleshooting content in `docs-portal/docs/troubleshooting/index.md`
- [X] T017 [US1] French translations of T009–T016 at the mirrored paths under `docs-portal/i18n/fr/docusaurus-plugin-content-docs/current/` (depends on T009–T016 for source content)
- [X] T018 [US1] German translations of T009–T016 at the mirrored paths under `docs-portal/i18n/de/docusaurus-plugin-content-docs/current/` (depends on T009–T016)
- [X] T019 [US1] Spanish translations of T009–T016 at the mirrored paths under `docs-portal/i18n/es/docusaurus-plugin-content-docs/current/` (depends on T009–T016)
- [X] T020 [US1] Configure sidebar navigation in `docs-portal/sidebars.ts` grouping pages by category (installation, configuration, user guide, troubleshooting)
- [X] T021 [US1] Verify locale-switcher preserves current page path (not redirecting to home) via manual check against FR-005, using the locale dropdown Docusaurus's classic preset provides

**Checkpoint**: At this point, User Story 1 is fully functional — quickstart.md Scenario 1 passes end-to-end

---

## Phase 3b: Coverage gap — features outside issue #89's list (Priority: P1, added post-launch)

**Why**: The initial content set (T009–T019) deliberately scoped to exactly what Codeberg issue #89 listed (versioning, backups, sharing, search, 2FA), per spec.md FR-002 and its Assumptions. After the first release, manual review found this left real, shipped app features with **zero** documentation coverage: basic prompt CRUD/favoriting, categories, tags, import/export, and dynamic placeholders (spec 006). Pagination (spec 005) was also undocumented. This phase closes that gap as a direct extension of this feature (not a new spec), following the same locale-parity discipline as every other page.

- [X] T036 [P] Write English `docs-portal/docs/user-guide/prompt-management.md` (create/edit/delete/favorite, card-grid UI) grounded in `src/web/routers/prompts_crud_router.py`
- [X] T037 [P] Write English `docs-portal/docs/user-guide/categories.md` (CRUD, merge, bulk-delete, find-replace, undo) grounded in `src/web/routers/categories_router.py`
- [X] T038 [P] Write English `docs-portal/docs/user-guide/tags.md` (CRUD, hierarchy, merge, bulk-delete, find-replace, orphan cleanup, analytics, undo) grounded in `src/web/routers/tags_router.py`
- [X] T039 [P] Write English `docs-portal/docs/user-guide/import-export.md` (CSV/Markdown/JSON export, append/merge/replace import modes) grounded in `src/web/routers/import_export_router.py` and `ImportMode` enum
- [X] T040 [P] Write English `docs-portal/docs/user-guide/placeholders.md` (bracket/brace syntax, Copy-click fill form, non-interaction with versioning/search/export) grounded in `specs/006-prompt-placeholders/spec.md`
- [X] T041 [P] Write English `docs-portal/docs/user-guide/pagination.md` (Load More, page size 25/50/100, default 50/max 100) grounded in `specs/005-pagination-lazy-loading/spec.md` and `src/web/routers/prompts_shared.py`
- [X] T042 French/German/Spanish translations of T036–T041 at the mirrored i18n paths, heading counts matched exactly (verified via `npm run docs:check-parity`)
- [X] T043 Update `docs-portal/sidebars.ts` to include the 6 new pages in the User Guide category, ordered for a new-user reading path
- [X] T044 Verify `npm run docs:check-parity` passes clean (16 pages × 3 locales) and `npm run docs:build` succeeds with no broken links/anchors across all 4 locales

**Checkpoint**: User guide now covers every major shipped feature (prompt CRUD, categories, tags, placeholders, search, pagination, import/export, sharing, versioning, backups, 2FA), not just issue #89's original list

---

## Phase 4: User Story 2 - Catch translation drift before it reaches readers (Priority: P2)

**Goal**: An automated check compares each non-English locale's tree against English and fails with actionable detail on any missing page or heading-count mismatch, per the exact failure mode the prior Clavis rollout hit ([[projects/clavis/concepts/docs-portal-fr-en-drift-detection]]).

**Independent Test**: Intentionally delete a page from one locale tree or remove a heading from a translated page, run the checker, confirm it fails with a specific actionable message (quickstart.md Scenario 2's break/restore drill) — independently testable even if US1's content set is still incomplete.

### Implementation for User Story 2

- [X] T022 [US2] Implement frontmatter/heading parser in `docs-portal/scripts/check-i18n-parity.ts`: read a Markdown file's frontmatter and count `##`/`###` headings, per data-model.md's Documentation Page entity
- [X] T023 [US2] Implement file-existence parity check in `docs-portal/scripts/check-i18n-parity.ts`: for each English page (not `translation_exempt: true`), confirm a file exists at the mirrored path in `fr`, `de`, `es` (FR-007) (depends on T022)
- [X] T024 [US2] Implement heading-count parity check in `docs-portal/scripts/check-i18n-parity.ts`: for each page present in both trees, compare heading counts and flag any mismatch in either direction (FR-008, spec.md Edge Cases) (depends on T022)
- [X] T025 [US2] Implement `translation_exempt` handling in `docs-portal/scripts/check-i18n-parity.ts` per contracts/page-frontmatter-schema.md: skip both checks for exempted English pages across all 3 locales, fail-open with a warning on a non-boolean value (depends on T022)
- [X] T026 [US2] Implement structured finding output and exit codes in `docs-portal/scripts/check-i18n-parity.ts` matching contracts/i18n-parity-check.md's exact output shape (`[locale] MISSING: ...` / `[locale] HEADING_MISMATCH: ...`, summary line, exit 0/1) (depends on T023, T024, T025)
- [X] T027 [US2] Wire `npm run docs:check-parity` (from T003) to invoke `docs-portal/scripts/check-i18n-parity.ts`
- [X] T028 [US2] Run the quickstart.md Scenario 2 break/restore drill manually to prove both failure modes (missing page, heading mismatch) are caught with correct locale/path/count detail

**Checkpoint**: At this point, User Stories 1 AND 2 both work independently — running `npm run docs:check-parity` against the real content from Phase 3 passes clean, and the drill in T028 proves it actually catches regressions

---

## Phase 5: User Story 3 - Build and deploy the portal without touching app runtime code (Priority: P3)

**Goal**: The portal builds, lints, and is CI-gated entirely independently of the main application's build/test/lint pipeline.

**Independent Test**: A change touching only `docs-portal/` doesn't affect `make test`/`make lint`, and a change touching only `src/`/app frontend code doesn't trigger the portal's CI job (quickstart.md Scenario 3).

### Implementation for User Story 3

- [X] T029 [US3] Create `.forgejo/workflows/docs-portal.yml` scoped with `paths: ['docs-portal/**']` on push/PR to `main`, running `npm install`, `tsc --noEmit` + eslint against `docs-portal/`'s own TypeScript sources (`docusaurus.config.ts`, `sidebars.ts`, `scripts/check-i18n-parity.ts`), `npm run docs:check-parity`, then `npm run docs:build` inside `docs-portal/` (per FR-012, constitution.md Development Workflow #5, research.md's separate-workflow decision)
- [X] T029a [US3] Configure `docs-portal.yml`'s job as a required status check on the `main` branch's protection rules (Forgejo repo settings), so FR-010's "run automatically before changes are merged" is enforced as a merge gate, not just a job that runs and can be ignored — this is a one-time repo-admin action outside the codebase; document the setting in `docs/DEVELOPMENT.md` (T034) so it survives a repo migration or re-creation
- [X] T030 [US3] Confirm `.forgejo/workflows/ci.yml` (the app's existing CI) requires no changes — verify by diffing it against its current state and confirming zero edits were needed
- [X] T031 [US3] Verify `make test` and `make lint` (repo root) complete unchanged with `docs-portal/` present, and that `git diff --stat main -- docs-portal/` shows only portal files touched, per quickstart.md Scenario 3's isolation check
- [X] T032 [US3] Verify `docs-portal/` builds offline with zero external network calls during `npm run build` (quickstart.md Scenario 3's network-disabled check), AND inspect the built `docs-portal/build/**/*.html` output for external `<link>`/`<script>` references (e.g. Google Fonts, analytics) that Docusaurus's default theme may include — fail this task if any external asset reference is found in the served output, not just at build time. Confirms FR-013 and the self-hoster "works out of the box, no CDN/telemetry" edge case end-to-end (build-time AND runtime)

**Checkpoint**: All user stories now independently functional — the portal is readable (US1), self-verifying against drift (US2), and fully isolated from the app's build/CI (US3)

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final wiring not owned by any single user story.

- [X] T033 [P] Populate `docs-portal/docs/release-notes/index.md` and its `fr`/`de`/`es` counterparts from `docs/CHANGELOG.md`'s existing entries, per FR-015 and research.md's changelog-sourcing decision
- [X] T034 [P] Add `docs-portal/` build step documentation to `docs/DEVELOPMENT.md` alongside the existing Makefile reference table
- [X] T035 Run the full quickstart.md validation (all 4 scenarios) end-to-end as a final acceptance pass against SC-001 through SC-005

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion. No dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational completion. Independently testable even with partial US1 content — the checker only needs *some* pages to prove it works, but full validation (T028) is stronger against T009–T019's complete content
- **User Story 3 (Phase 5)**: Depends on Foundational completion. Independent of US1/US2 content — CI isolation can be verified with placeholder content alone
- **Polish (Phase 6)**: Depends on US1 (content exists to add release notes to) and US2 (parity checker exists to validate T033's new pages against)

### Within Each User Story

- US1: content pages (T009–T016, parallelizable) before their translations (T017–T019, sequential per locale since each depends on the full English set)
- US2: parser (T022) before the three check implementations (T023–T025, can proceed in parallel once T022 lands) before output wiring (T026) before script hookup (T027) before the verification drill (T028)
- US3: workflow file (T029) before T029a (branch protection references the job T029 creates) before the remaining verification tasks (T030, T031 can run in parallel; T032 independent)

### Parallel Opportunities

- T003, T004 (Setup) can run in parallel
- T005–T008 are mostly sequential (T006 depends on T005's structure; T007/T008 are independent of each other and of T005/T006 — mark T008 [P])
- T009–T016 (all 8 English content pages) can run fully in parallel — different files, no cross-dependencies
- T023, T024, T025 (the three check types) can run in parallel once T022's parser exists — different logical checks in the same file, but independently unit-testable pieces of logic
- T030, T031, T032 (US3's three verification tasks) can run in parallel once T029a is done
- T033, T034 (Polish) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all English content pages together:
Task: "Write English installation/deployment content in docs-portal/docs/installation/index.md"
Task: "Write English configuration reference in docs-portal/docs/configuration/index.md"
Task: "Write English user-guide page: versioning in docs-portal/docs/user-guide/versioning.md"
Task: "Write English user-guide page: backups in docs-portal/docs/user-guide/backups.md"
Task: "Write English user-guide page: sharing in docs-portal/docs/user-guide/sharing.md"
Task: "Write English user-guide page: search in docs-portal/docs/user-guide/search.md"
Task: "Write English user-guide page: two-factor auth in docs-portal/docs/user-guide/two-factor-auth.md"
Task: "Write English troubleshooting content in docs-portal/docs/troubleshooting/index.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (English + 3 translations, full content set)
4. **STOP and VALIDATE**: Run quickstart.md Scenario 1 — portal readable in all 4 locales
5. Deploy/demo — this alone delivers the portal's entire reader-facing value (per spec.md: "This is the entire purpose of the portal")

### Incremental Delivery

1. Setup + Foundational → scaffolded, empty 4-locale site
2. Add User Story 1 → validate Scenario 1 → deploy/demo (MVP!)
3. Add User Story 2 → validate Scenario 2's break/restore drill → merge-time drift protection now active
4. Add User Story 3 → validate Scenario 3 → CI isolation confirmed, safe for ongoing app development
5. Polish → release notes populated, full quickstart validation (Scenario 4 + all others)

### Parallel Team Strategy

With multiple contributors, once Foundational (Phase 2) is done:

- Contributor A: User Story 1 (content authoring + translation)
- Contributor B: User Story 2 (parity checker)
- Contributor C: User Story 3 (CI workflow)

All three integrate independently — US2 and US3 don't require US1's content to be complete, only present in some form.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- No `tests/` tasks — this feature's own automated check (US2) is the verification mechanism; its correctness is proven via the quickstart.md break/restore drill (T028), not a separate unit-test suite
- Translation tasks (T017–T019) depend on their English source (T009–T016) existing first — not parallelizable with the English authoring, though the three locales are parallelizable with each other
- Avoid: adding governance/compliance frontmatter fields (`page_id`, `owner_role`, `review_cadence_days`) — explicitly out of scope per spec.md
