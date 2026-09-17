# Quickstart: Documentation Portal with Multilingual Support

Validates the feature end-to-end once implemented. See [data-model.md](./data-model.md) for entity definitions and [contracts/i18n-parity-check.md](./contracts/i18n-parity-check.md) for the parity checker's contract.

## Prerequisites

- Node.js ≥ 18 (repo CI pins Node 20; matches Docusaurus 3.x's minimum).
- Repo checked out on branch `010-docs-portal-i18n`, `docs-portal/` implemented per [plan.md](./plan.md)'s Project Structure.

## Setup

```bash
cd docs-portal
npm install
```

## Scenario 1 — Reading the portal in each locale (User Story 1, SC-001, SC-002)

```bash
npm run start
```

- Open the portal in a browser (default `http://localhost:3000`).
- Confirm the English installation, configuration, user guide, and troubleshooting sections render with real content (not placeholders).
- Switch locale to French, German, and Spanish via the portal's locale switcher.
- **Expected**: each locale shows fully translated content for the same page set; switching locale while on a specific page lands on that page's equivalent in the new locale, not the home page (FR-005).
- Navigate to a page that has not yet been translated (if any exist during incremental rollout) in a non-English locale.
- **Expected**: the English version renders with a visible "translation not yet available" notice (FR-006), not a 404.

## Scenario 2 — Catching translation drift (User Story 2, SC-003)

```bash
npm run docs:check-parity
```

- **Expected on a clean tree**: exits `0`, prints a passing summary (per the CLI contract).

Now intentionally break parity to prove the check actually catches it:

```bash
# Simulate a missing translation
mv docs-portal/i18n/fr/docusaurus-plugin-content-docs/current/troubleshooting/common-errors.md /tmp/tmp-removed.md
npm run docs:check-parity   # expect exit 1, MISSING finding for fr

# restore
mv /tmp/tmp-removed.md docs-portal/i18n/fr/docusaurus-plugin-content-docs/current/troubleshooting/common-errors.md

# Simulate a structural drift (delete a heading from a translated page)
# (manually remove one "## " line from a docs-portal/i18n/de/.../backups.md heading)
npm run docs:check-parity   # expect exit 1, HEADING_MISMATCH finding for de
# (restore the heading)
```

- **Expected**: both failure modes are caught with a specific page path, locale, and mismatch detail — this reproduces the exact regression class documented from the prior project (missing pages and silently-shrunk translated content).

## Scenario 3 — Build isolation from the main app (User Story 3, SC-004)

```bash
# From repo root — confirm app CI paths are untouched by portal-only changes
git diff --stat main -- docs-portal/   # should show only docs-portal/ files changed
make test     # app test suite — should not build or reference docs-portal/
make lint     # app lint — should not touch docs-portal/
```

```bash
# Confirm the portal builds standalone with no external dependency
cd docs-portal
npm run build
```

- **Expected**: `npm run build` produces a static `build/` directory with no network calls required (verify by running with network disabled, e.g. `--offline` npm flag on a warm cache, or by inspecting build logs for any external fetch).
- **Expected**: `.forgejo/workflows/docs-portal.yml` is a workflow separate from `.forgejo/workflows/ci.yml`, scoped with a `paths: ['docs-portal/**']` trigger — confirm by inspecting the workflow file and confirming a commit touching only `src/` does not trigger it in CI history.

## Scenario 4 — Release notes reflect real releases (FR-015)

- Open `docs-portal/docs/release-notes/index.md` (English) and its `fr`/`de`/`es` counterparts.
- **Expected**: content is derived from `docs/CHANGELOG.md`'s `[Unreleased]`/versioned entries, translated in all four locales, with the same entries present in each (subject to the same parity check as any other page, unless marked exempt).

## Done

All four scenarios passing means the feature satisfies spec.md's Success Criteria SC-001 through SC-005.
