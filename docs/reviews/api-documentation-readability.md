<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# API documentation: scoped readability diagnostic

Date: 2026-11-16. Scope: the API entry journey being added to the existing portal. This is not a whole-portal editorial audit. English, French, German, and Spanish are present. Existing guides are not rewritten in this change; new API pages and navigation are added.

## Executive findings

1. Each existing home page clearly directs readers to installation, configuration, and everyday use. Keep these paths intact and add a separate API journey for integrators.
2. No existing portal page walks an integrator from their instance address to a successful API call. A short tutorial needs prerequisites, commands, expected results, and a next step.
3. The live reference and the static documentation have different addresses. Explain which host serves `/docs` and `/openapi.json`; a reader must not append these paths to the documentation site's address.
4. Runtime descriptions contain historical claims such as “Anyone can view prompts” that do not explain current visibility scoping. The new guide must state the observable behavior verified in route implementations, without promising new capabilities.

These journey-level gaps affect all four languages. No regulated/standard audience toggle exists in this portal; the skill's Clavis-specific reference does not apply. This diagnostic does not assess metadata or translation parity.

## Existing entry pages

| Page                           | Language | Most affected audience | Severity | Assessment                                                    |
| ------------------------------ | -------- | ---------------------- | -------- | ------------------------------------------------------------- |
| `docs/index.md`                | EN       | Integrator             | Major    | No API journey; existing user/admin introduction is readable. |
| `i18n/fr/.../current/index.md` | FR       | Integrator             | Major    | No API journey; existing user/admin introduction is readable. |
| `i18n/de/.../current/index.md` | DE       | Integrator             | Major    | No API journey; existing user/admin introduction is readable. |
| `i18n/es/.../current/index.md` | ES       | Integrator             | Major    | No API journey; existing user/admin introduction is readable. |

## Details and correction criteria

### Home pages: missing integrator next step

- EN: “install it, configure it, and use its core features day to day.”
- FR: « l'installer, le configurer et utiliser ses fonctionnalités principales au quotidien. »
- DE: „Installation, Konfiguration und täglichen Nutzung der wichtigsten Funktionen“
- ES: « instalarla, configurarla y usar sus funciones principales en el día a día. »

The text serves its existing audience. The obstacle is the absence of a next step for a reader who wants an integration. Apply the writing guide's **Checklist Before Publishing** rule: “Links to related pages (no dead ends).” Add an API link and an audience explanation; do not rewrite the existing introduction.

### New content: acceptance criteria

Apply **Examples → Minimal, Then Complete**: start with a read-only request before creation or version operations. Apply **Examples → Show, Don't Tell**: show actual request encoding and response keys. Apply **Error Messages**: give the status/symptom, cause, and corrective action without pretending all endpoints share one error format. Apply **Address the Reader**, **Code in Prose**, and **Headings → Depth** in each page's own language. Explain API and token terminology before the commands.

## Priority

1. Add the API audience entry and explain application versus documentation addresses.
2. Add the read-first tutorial, authentication/2FA guidance, and expected responses.
3. Add an operation reference with permission, pagination, encoding, and error notes.

No existing-page prose rewrite is proposed. Broader editorial changes remain outside this task and would require review of a full diagnostic before rewriting, as required by the invoked skill.

## Delivery verification

- Added three pages per locale: audience entry, read-first tutorial, and operation reference. Existing page prose is unchanged; each home receives an API entry.
- All 92 method/path mentions across the new pages match the route definitions; Bash code blocks pass syntax validation. These are source-level checks, not live endpoint execution. Backend dependencies are not installed in this worktree.
- Production build succeeds for EN/FR/DE/ES. Separate technical checks pass for language parity, TypeScript, lint, and formatting.
- Browser checks confirm localized API sidebar labels and the overview → tutorial → reference journey in all four languages. French desktop/mobile renderings were inspected; the mobile entry page has no horizontal overflow.
