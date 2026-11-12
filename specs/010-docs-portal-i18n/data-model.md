# Phase 1 Data Model: Documentation Portal with Multilingual Support

There is no database or persisted application data for this feature — content is version-controlled Markdown compiled at build time. This document models the content entities and the parity-check's in-memory representation, per spec.md's Key Entities section.

## Documentation Page

A single Markdown file representing one topic, existing once per locale it has been translated into.

| Field | Type | Notes |
|---|---|---|
| `path` | string | Relative path under `docs/` (English) or the mirrored path under `i18n/<locale>/docusaurus-plugin-content-docs/current/` |
| `category` | enum | `installation` \| `configuration` \| `user-guide` \| `troubleshooting` \| `release-notes` |
| `title` | string | Page `<h1>` / frontmatter `title` |
| `headings` | list of string | All `##`/`###` section headings in document order — this is what the parity check compares by *count*, not by text (headings are translated, so string-matching across locales isn't meaningful) |
| `locale` | enum | `en` \| `fr` \| `de` \| `es` |
| `translationExempt` | boolean | Set via a frontmatter flag (see Translation Exemption below); defaults to `false` |

**Validation rules**:
- Every English page (`translationExempt: false`) MUST have a corresponding page at the same relative path in each of `fr`, `de`, `es` (FR-007).
- A translated page's `headings.length` MUST equal its English counterpart's `headings.length` (FR-008); a mismatch in either direction (fewer or more) is a failure (per spec.md Edge Cases — over-translation is flagged too, not just deficits).

## Locale Content Tree

The complete set of Documentation Pages for one language.

| Field | Type | Notes |
|---|---|---|
| `locale` | enum | `en` \| `fr` \| `de` \| `es` |
| `rootPath` | string | `docs/` for `en`; `i18n/<locale>/docusaurus-plugin-content-docs/current/` otherwise |
| `pages` | list of Documentation Page | All pages discovered under `rootPath` |
| `isAuthoritative` | boolean | `true` only for `en` — defines the expected page set all other trees are diffed against |

**Relationships**: Exactly one `en` tree (authoritative) and three non-English trees (`fr`, `de`, `es`), each diffed against `en`.

## Parity Report

The output of the automated structural check (FR-007, FR-008, FR-009).

| Field | Type | Notes |
|---|---|---|
| `locale` | enum | Which non-English locale this finding is for |
| `kind` | enum | `missing-page` \| `heading-count-mismatch` |
| `pagePath` | string | The English page path this finding refers to |
| `expectedHeadingCount` | integer \| null | English page's heading count (null for `missing-page`) |
| `actualHeadingCount` | integer \| null | Translated page's heading count (null for `missing-page`) |

**Validation rules**: A report with zero findings across all three non-English locales is a passing run (FR-010's CI gate passes); any finding fails the check and must print `locale`, `pagePath`, `kind`, and the counts when applicable (FR-009's "enough detail to act on immediately").

## Translation Exemption

A marker on an English page excluding it from the parity check (FR-011).

| Field | Type | Notes |
|---|---|---|
| `pagePath` | string | The exempted English page |
| `frontmatterFlag` | boolean | e.g. `translation_exempt: true` in the page's YAML frontmatter — the mechanism is a frontmatter field on the page itself, not a separate exemption list, so the exemption travels with the file and is visible to anyone editing it |

**Validation rules**: When `translationExempt: true` is set on an English page, the parity check MUST skip both the file-existence and heading-count checks for that page across all three non-English locales.

## State / Lifecycle

Content has no runtime state machine — a page simply exists or doesn't, per locale, at any point in the git history. The Parity Report is regenerated fresh on every CI run (FR-010) rather than persisted between runs.
