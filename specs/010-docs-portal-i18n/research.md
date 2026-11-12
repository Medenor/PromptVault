# Phase 0 Research: Documentation Portal with Multilingual Support

No `NEEDS CLARIFICATION` markers remained in the Technical Context after drafting it directly from Codeberg issue #89 and repo inspection — this file records the decisions and their rationale rather than resolving open unknowns.

## Decision: Docusaurus 3.x as the portal framework

**Rationale**: Named explicitly in issue #89, and it ships first-class i18n support (per-locale content trees under `i18n/<locale>/docusaurus-plugin-content-docs/current/`) as a built-in feature of `@docusaurus/plugin-content-docs`, requiring no additional i18n plugin. It builds to fully static output (`docusaurus build` → static HTML/JS/CSS), satisfying the "no external CDN/telemetry" and "self-hosted" constraints (FR-001, FR-013) with zero custom static-site tooling to build from scratch.

**Alternatives considered**:
- **VitePress**: lighter weight, but its i18n model is config-driven locale prefixes rather than a fully mirrored content-tree-per-locale, making the file-existence parity check (FR-007) less natural to implement — Docusaurus's one-directory-per-locale layout maps directly onto "diff tree A against tree B."
- **Hand-rolled static site generator**: rejected — reinvents i18n routing, sidebar generation, and search for no benefit; the four-locale scale here doesn't justify it.

## Decision: Structural parity check as a standalone TypeScript script, not a Docusaurus plugin

**Rationale**: This is a direct adoption of the fix documented in [[projects/clavis/concepts/docs-portal-fr-en-drift-detection]] (the prior project's `check-metadata.ts`), scoped down to the two checks spec 010 actually requires (FR-007 file-existence, FR-008 heading-count) since PromptVault's spec deliberately excludes the `page_id`/`last_reviewed` governance fields that check depended on (those exist only because the prior project needed per-page ownership/review-cadence tracking — explicitly out of scope here, see [[projects/clavis/concepts/documentation-portal-governance]]). Keeping it a plain Node script (not a Docusaurus plugin) keeps it runnable standalone (`npm run docs:check-parity`) and inside CI without needing a full Docusaurus build first.

**Alternatives considered**:
- **Full governance/ownership metadata model** (owner roles, review cadence, escalation paths) as documented in the prior project's `documentation-portal-governance.md`: explicitly rejected per issue #89's non-goals — that machinery exists only because the prior project was in a regulated context.
- **Only checking `last_reviewed` dates** (the prior project's original, insufficient approach): explicitly rejected — this is the exact failure mode issue #89 flags as the reason 11 French pages silently drifted; a same-date pair can look compliant while content diverges completely.
- **Translation-quality verification (automated)**: rejected — the prior project's own retrospective states this is "not tractable without reading the language" and is a distinct, larger investment; spec 010's Assumptions section documents that structural parity plus human review is the intended split.

## Decision: Separate CI workflow (`docs-portal.yml`) with a path filter, not an addition to `ci.yml`

**Rationale**: The existing `.forgejo/workflows/ci.yml` has no `paths:` filter and runs on every push/PR to `main`. Adding portal steps there would make every unrelated app change wait on a Docusaurus build (violates FR-012). A new workflow scoped with `paths: ['docs-portal/**']` (Forgejo Actions/GitHub Actions syntax is shared) satisfies isolation directly, and mirrors the prior project's `docs-portal.yml` pattern.

**Alternatives considered**:
- **Job-level `if:` condition inside `ci.yml`** checking changed paths: more complex to express correctly than a workflow-level `paths:` trigger filter, and still couples the portal's dependency install into the same job graph as the app.

## Decision: Release notes sourced from `docs/CHANGELOG.md`

**Rationale**: The repo already maintains a structured, dated Keep-a-Changelog-format file at `docs/CHANGELOG.md` for every merged change. FR-015 requires the portal's release-notes section to reflect published releases; reusing this existing source avoids inventing a second changelog process, and keeps a single source of truth (the same principle the prior project's still-open issue #69 recommended but hadn't yet enforced for its own portal-vs-compliance content split).

**Alternatives considered**:
- **New Docusaurus native `@docusaurus/plugin-content-blog`-based release feed**: viable presentation-layer option for the *portal side*, still sourced from `docs/CHANGELOG.md` content — not a competing decision, just an implementation detail for Phase 1/tasks to decide, not blocking here.

## Decision: `docs-portal/` gets its own `package.json` and dependency tree

**Rationale**: Isolates Docusaurus's dependencies from the app's own `npm install`/`package.json` (FR-012's isolation requirement extends naturally to dependencies, not just CI triggers) — a `docusaurus build` failure or a Docusaurus version bump can never break the app's frontend build or vice versa.

**Alternatives considered**:
- **npm workspaces** merging both into one root `package.json`: rejected as unnecessary complexity for a static content site with no shared runtime code with the app frontend.
