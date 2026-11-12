# Implementation Plan: Documentation Portal with Multilingual Support

**Branch**: `010-docs-portal-i18n` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-docs-portal-i18n/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Add a static, self-hosted documentation portal (`docs-portal/`) covering installation, configuration, user guide, troubleshooting, and release notes for PromptVault, published in English (default), French, German, and Spanish. Built with Docusaurus 3.x as a standalone static site kept out of `src/`/`frontend/` and out of the main app's build/CI path. The portal's own CI job runs only on `docs-portal/**` changes and enforces a structural i18n-parity check (file existence + heading-count match per non-English locale against English) modeled directly on a documented prior-project failure mode ([[projects/clavis/concepts/docs-portal-fr-en-drift-detection]]): a metadata checker that validated English frontmatter only and never diffed non-English content, letting 11 French pages silently rot to stub content behind a same-date staleness check that never actually compared structure.

## Technical Context

**Language/Version**: TypeScript/Node.js (Docusaurus 3.x requires Node ≥18; CI already pins Node 20 via `actions/setup-node`)

**Primary Dependencies**: Docusaurus 3.x (`@docusaurus/core`, `@docusaurus/preset-classic`), `@docusaurus/plugin-content-docs` i18n support (built-in, no extra package)

**Storage**: N/A — static Markdown content compiled to static HTML/JS/CSS at build time; no database, no runtime backend

**Testing**: A Node-based structural parity script (file-existence + heading-count check, mirroring `check-metadata.ts`'s approach at the referenced prior project) run via `npm run docs:check-parity` or equivalent, plus Docusaurus's own build as a smoke test (`docusaurus build` fails the job on broken links by default)

**Target Platform**: Static site served alongside/near the existing self-hosted deployment (e.g., served as static files by the same reverse proxy /nginx setup used for `dist/static/`); no external CDN or hosting service dependency

**Project Type**: Static documentation site — new top-level `docs-portal/` directory, structurally independent from `src/` (Python backend) and `frontend/`-style TS app code; this is closest to a standalone "web" content project, not the app's existing web-service/frontend split

**Performance Goals**: N/A beyond ordinary static-site load times — no runtime performance target since there is no backend request path

**Constraints**: Must not require any change to the main app's build/test/lint pipeline; must build offline/statically with zero external network calls at runtime (no telemetry, no CDN fonts/assets by default); i18n parity check must run in CI and be able to run locally as an npm script

**Scale/Scope**: Initial content set only — installation/deployment (Docker via `make build`), configuration reference, core user guide (versioning, backups, sharing, search, TOTP 2FA), troubleshooting, and release notes — in 4 locales (EN default + FR/DE/ES). No multi-version doc branching, no compliance/governance content (explicitly out of scope per issue #89 and confirmed by the prior project's now-abandoned compliance-adjacent governance model, [[projects/clavis/concepts/documentation-portal-governance]], which does not apply here since PromptVault is not a regulated app).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution's five core principles (Layered Service Architecture, Test Coverage Gate, Security-First Authentication, TypeScript-Only Frontend, Database-Backed Persistence) all describe the **application** (`src/`, `frontend/`-equivalent web app, auth, DB). A static docs site with no backend, no auth-mutating endpoints, no database, and no runtime service code does not fall under any of them as written:

- **I. Layered Service Architecture** — N/A. No web/API/service/repository layers exist in a static site.
- **II. Test Coverage Gate** — N/A for coverage-percentage purposes (no `pytest`/Vitest-instrumented runtime code to cover). Interpreted in spirit: the portal's structural i18n-parity check *is* its test gate (FR-007–FR-010), and it MUST run in CI before merge, mirroring the intent of "no feature branch merges below its gate."
- **III. Security-First Authentication** — N/A. The portal has no endpoints that mutate data; it is read-only static content.
- **IV. TypeScript-Only Frontend** — Directly relevant in spirit, not by path: Docusaurus config/plugins/scripts written for this feature MUST be TypeScript, consistent with the project's TS-only stance, even though `docs-portal/` sits outside `src/web/static/ts/`. No JavaScript authored in `docs-portal/` build tooling.
- **V. Database-Backed Persistence** — N/A. Content is Markdown files, not JSON/DB storage; this principle governs *application* data, not documentation content.

**Result**: PASS. No violations to justify — the constitution's gates don't apply to a non-application static site, and this plan adopts the closest applicable principle (TS-only tooling) voluntarily. No entry needed in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/010-docs-portal-i18n/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
docs-portal/                          # New, isolated from src/ and app frontend code
├── docusaurus.config.ts
├── sidebars.ts
├── package.json                      # Own dependency tree, own lockfile
├── tsconfig.json
├── docs/                             # English (default locale) content — authoritative tree
│   ├── installation/
│   ├── configuration/
│   ├── user-guide/
│   │   ├── versioning.md
│   │   ├── backups.md
│   │   ├── sharing.md
│   │   ├── search.md
│   │   └── two-factor-auth.md
│   ├── troubleshooting/
│   └── release-notes/
│       └── index.md                  # Sourced from docs/CHANGELOG.md, translated per locale
├── i18n/
│   ├── fr/docusaurus-plugin-content-docs/current/<mirrors docs/ exactly>
│   ├── de/docusaurus-plugin-content-docs/current/<mirrors docs/ exactly>
│   └── es/docusaurus-plugin-content-docs/current/<mirrors docs/ exactly>
├── scripts/
│   └── check-i18n-parity.ts          # FR-007/FR-008/FR-009: file-existence + heading-count check
└── static/

.forgejo/workflows/
└── docs-portal.yml                   # New, separate workflow — triggers only on `docs-portal/**` (FR-012)
```

**Structure Decision**: New top-level `docs-portal/` directory (Docusaurus 3.x), fully isolated from `src/` (Python backend) and the app's own TypeScript frontend under `src/web/static/ts/`. It has its own `package.json`/lockfile so its dependency tree never touches the app's `npm install`/`make install`. A dedicated Forgejo Actions workflow (`docs-portal.yml`) with a `paths:` filter on `docs-portal/**` builds the portal and runs the parity check — kept separate from `.forgejo/workflows/ci.yml` (the app's existing CI) so neither pipeline triggers or blocks on the other's changes, satisfying FR-012.

## Complexity Tracking

Not applicable — Constitution Check passed with no violations (see above). No entries required.

## Post-Design Constitution Re-Check

Re-evaluated after Phase 1 (data-model.md, contracts/, quickstart.md): the design introduces no database, no auth-mutating endpoints, no new application service/repository layers, and keeps all new tooling in TypeScript. The same PASS result from the initial Constitution Check stands unchanged — Phase 1 design did not introduce anything that would trigger any of the five principles.
