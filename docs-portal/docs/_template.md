---
title: Page Title Here
sidebar_position: 1
translation_exempt: false
---

<!--
Frontmatter reference (see specs/010-docs-portal-i18n/contracts/page-frontmatter-schema.md):

- title (required): the page <h1> / sidebar label.
- sidebar_position (optional): controls ordering within its category.
- translation_exempt (optional, English pages only, default false): set to
  true only for pages that are intentionally never translated (e.g. a
  contributor-only technical note). Skips this page in all three
  non-English locales for the i18n parity check.

This file is prefixed with an underscore so Docusaurus excludes it from the
sidebar and build. Copy it as a starting point for a new page, then delete
this comment block.
-->

Page content starts here. Use `##`/`###` headings for sections — the i18n
parity checker (`npm run docs:check-parity`) compares heading counts between
this page and its `fr`/`de`/`es` translations, so keep sections 1:1 across
locales.

## Example Section

Body text.
