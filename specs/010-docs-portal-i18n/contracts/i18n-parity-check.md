# Contract: `check-i18n-parity` CLI

The only interface this feature exposes to another system (CI) is the i18n structural parity checker. Everything else is static content with no programmatic contract.

## Invocation

```bash
npm run docs:check-parity
# or directly:
node docs-portal/scripts/check-i18n-parity.ts
```

## Inputs

- Reads `docs-portal/docs/**/*.md` (English, authoritative tree).
- Reads `docs-portal/i18n/{fr,de,es}/docusaurus-plugin-content-docs/current/**/*.md` (mirrored trees).
- Reads each Markdown file's frontmatter for `translation_exempt: true`/`false` (default `false`).
- No network access, no environment variables required.

## Output

**On success** (no findings across all three locales):

- Exit code `0`.
- stdout: a one-line summary, e.g. `i18n parity check passed: 42 pages × 3 locales, 0 exemptions skipped`.

**On failure** (one or more findings):

- Exit code `1`.
- stdout/stderr: one line per finding, machine-parseable and human-readable, in this shape:

  ```text
  [fr] MISSING: docs/troubleshooting/common-errors.md has no i18n/fr counterpart
  [de] HEADING_MISMATCH: docs/user-guide/backups.md — en has 5 sections (##/###), de has 3
  [es] HEADING_MISMATCH: docs/user-guide/search.md — en has 4 sections (##/###), es has 6 (extra/untranslated content, not just missing)
  ```

  `HEADING_MISMATCH` fires identically whether the translated page has **fewer** headings (under-translated/stub content — the failure mode a prior project's rollout missed) or **more** headings (over-translation or drift in the other direction, per spec.md's Edge Cases). The message always states both counts so either direction is immediately readable from the line itself.

- A final summary line with total finding count, e.g. `i18n parity check FAILED: 2 findings across 2 locales`.

## Contract guarantees

1. **Deterministic**: given the same file tree, always produces the same findings (no flakiness, no network calls, no timestamps compared).
2. **Complete enumeration**: does not stop at the first failure — reports every missing page and every heading-count mismatch across all three non-English locales in a single run, so a maintainer can fix everything before re-running (this is the direct fix for the prior project's failure mode, where the checker never even opened the non-English tree).
3. **Exemption-aware**: a page with `translation_exempt: true` produces zero findings for that page, in any locale, and is not silently miscounted as "passing" — it's excluded from the denominator entirely.
4. **CI-friendly**: non-zero exit code on any finding, so `docs-portal.yml` can gate merges on this command's result without additional parsing (FR-010).

## Consumers

- `.forgejo/workflows/docs-portal.yml` — runs this as a required step before the Docusaurus build step, blocking merge on failure (once configured as a required status check per tasks.md T029a).
- Local development — a maintainer translating a page runs the same command manually to self-check before opening a PR.
