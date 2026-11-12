# Contract: Documentation Page Frontmatter Schema

This is the second interface this feature exposes — not to CI, but to anyone (or any tool) authoring a page: the YAML frontmatter block every `docs-portal/**/*.md` file must carry. It is the schema the [i18n parity checker](./i18n-parity-check.md) reads (per its Inputs section) and the shape a translator or a future automation must produce to be recognized as a valid page. Docusaurus itself also reads a subset of these fields (`title`, `sidebar_position`) for its own navigation — this contract is the intersection PromptVault requires on top of what Docusaurus already parses.

## Schema

```yaml
---
title: string                 # required, all locales — page <h1> / nav label
sidebar_position: number      # optional — controls ordering within its category; Docusaurus-native field
translation_exempt: boolean   # optional, EN pages only, default false — see below
---
```

No other custom frontmatter fields are required. This is a deliberately minimal schema — spec.md's Assumptions and the research.md `page_id`/`last_reviewed` decision both note that the prior project's governance-oriented fields (owner role, review cadence, `page_id`) are out of scope here.

**Note on `category`**: [data-model.md](../data-model.md)'s Documentation Page entity lists `category` (`installation` \| `configuration` \| `user-guide` \| `troubleshooting` \| `release-notes`) as a page attribute, but it is **not** a frontmatter field. It is derived structurally from the page's directory path under `docs-portal/docs/<category>/...` (per [plan.md](../plan.md)'s Project Structure) — the same path segment that determines a page's mirrored location under each `i18n/<locale>/.../current/<category>/...` tree. No author ever sets `category` directly; it falls out of where the file lives.

## Field contract

| Field | Required | Locales | Type | Rule |
|---|---|---|---|---|
| `title` | Yes | all | string | Must be non-empty. Not compared across locales (translated text is expected to differ) — only used for the portal's own nav rendering, not by the parity check. |
| `sidebar_position` | No | all | number | Docusaurus-native; not read or validated by the parity checker. Free for content authors. |
| `translation_exempt` | No | **English only** | boolean | Default `false` when absent. See below. |

## `translation_exempt` contract

- **Where it lives**: only on the **English** page's frontmatter. Setting it on a `fr`/`de`/`es` page has no effect — the parity checker (per [data-model.md](../data-model.md)'s Translation Exemption entity) only ever reads this flag from the authoritative English tree, and applies the exemption to that page's path across all three non-English locales.
- **Effect when `true`**: the parity checker's file-existence and heading-count checks are both skipped for that page path, in every locale, per the [i18n-parity-check.md](./i18n-parity-check.md) contract's "Exemption-aware" guarantee. The page is excluded from the check's totals entirely — it will not appear as a false failure, and it will not silently count as "passed" either.
- **Effect when absent or `false`** (default): the page is subject to full parity enforcement — a missing or heading-count-mismatched translation is a build-blocking finding (FR-007, FR-008).
- **Who sets it**: a human author, at page-creation time, when a page is intentionally not meant to be translated (spec.md's Edge Cases example: a contributor-only technical note). This is a deliberate, visible, per-file decision — not a separate exemption list a maintainer could forget to update, and not something the parity checker itself infers.

## Validation the parity checker performs against this schema

1. A frontmatter block that fails to parse as valid YAML is a **build-blocking error**, not a parity finding — Docusaurus's own build step will already reject a malformed page before the parity checker runs.
2. A page missing `title` is a **build-blocking error** at the Docusaurus level (required for nav rendering), not something the parity checker separately re-validates.
3. `translation_exempt` present with a non-boolean value (e.g. a string) is treated as `false` with a printed warning — the checker does not fail the build over a malformed exemption flag, since fail-open on an ambiguous flag is safer than silently over-exempting pages (fail-closed here would risk quietly widening what's excluded from parity enforcement).

## Non-goals

- No `page_id`, `owner_role`, `review_cadence_days`, or `last_reviewed` fields — this is the governance/compliance metadata schema from the prior-project rollout referenced in research.md, explicitly out of scope per issue #89.
- No per-locale frontmatter divergence is validated beyond `title`'s presence — translated frontmatter values (e.g. a translated `title`) are never compared for equality or format against English, only structural heading counts are (see [i18n-parity-check.md](./i18n-parity-check.md)).
