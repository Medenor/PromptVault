# Feature Specification: Documentation Portal with Multilingual Support

**Feature Branch**: `010-docs-portal-i18n`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Add a centralized documentation portal for PromptVault, covering installation, usage, and administration of the app for end users and self-hosters. The portal must support English, French, German, and Spanish, matching the four locales already shipped in the app's own UI. It must be static, self-hosted, and kept separate from the app's runtime code. A prior rollout of a similar portal (two locales) suffered from silent translation drift — non-English content fell out of sync with English and went unnoticed because staleness checks only compared review dates, not actual structure or content. With four locales instead of two, this risk is proportionally larger, so drift must be caught before it reaches readers." (Codeberg issue #89)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find setup and usage guidance in your own language (Priority: P1)

A self-hoster or end user visits the documentation portal to learn how to install, configure, or use PromptVault (versioning, backups, sharing, search). They read the portal in their preferred language — English, French, German, or Spanish — and find guidance that is complete and matches what English-speaking readers see.

**Why this priority**: This is the entire purpose of the portal. Without it, there is no documentation product; everything else (parity checks, release notes) exists to protect this experience.

**Independent Test**: Can be fully tested by opening the portal in each of the four locales and confirming that installation, configuration, and core user-guide content is present, navigable, and renders correctly — deployable and demonstrable on its own even before parity tooling exists.

**Acceptance Scenarios**:

1. **Given** the documentation portal is deployed, **When** a visitor selects the French, German, or Spanish locale, **Then** they see a fully translated version of the installation guide, configuration reference, user guide, and troubleshooting sections (not English fallback text or stub pages).
2. **Given** a visitor is reading a page in any supported locale, **When** they switch locales, **Then** they land on the equivalent page in the new locale rather than the portal's home page.
3. **Given** a visitor has no locale preference set, **When** they land on the portal, **Then** they see the English version by default.

---

### User Story 2 - Catch translation drift before it reaches readers (Priority: P2)

A maintainer changes or adds English documentation content. Before the change is merged, an automated check compares each non-English locale's tree against English and flags any page that is missing, or whose structure (section headings) diverges from its English counterpart — rather than relying on a "last reviewed" date that can look current while content has silently rotted.

**Why this priority**: This directly addresses the root cause of the prior rollout's failure (11 stale French pages went unnoticed for an extended period because the checker only validated English frontmatter and compared dates, not structure). Without this, the four-locale portal is at proportionally higher risk of the same silent decay. It's P2, not P1, because the portal still delivers value on day one without it — the check protects value over time.

**Independent Test**: Can be tested independently by intentionally deleting a page from one non-English locale tree or removing a heading from a translated page, then running the parity check and confirming it fails with a specific, actionable message identifying the missing page or heading-count mismatch.

**Acceptance Scenarios**:

1. **Given** an English documentation page exists, **When** the corresponding page is missing from any of the French, German, or Spanish trees, **Then** the parity check fails and identifies the specific missing page and locale.
2. **Given** an English page and its translated counterpart both exist, **When** the translated page has a different number of section headings than the English page, **Then** the parity check fails and identifies the specific page, locale, and heading-count mismatch.
3. **Given** all locale trees have matching pages and matching heading counts, **When** the parity check runs, **Then** it passes without requiring a human to manually diff content.

---

### User Story 3 - Build and deploy the portal without touching app runtime code (Priority: P3)

A maintainer changes or builds the documentation portal (content, structure, or theme) without needing to modify or redeploy the main PromptVault application, and without the portal's build or lint steps running when unrelated app code changes.

**Why this priority**: This is a maintainability and blast-radius concern rather than a reader-facing outcome — the portal already delivers its core value (Stories 1–2) even if build wiring is imperfect at first, but poor isolation would create ongoing friction and risk for every future app change.

**Independent Test**: Can be tested independently by making a change only inside the portal's directory and confirming the app's own build/test/lint commands are unaffected, then making a change only to app code and confirming the portal's build/lint job does not trigger.

**Acceptance Scenarios**:

1. **Given** only portal content changes, **When** the maintainer runs the app's existing build, test, and lint commands, **Then** those commands complete unaffected by the portal's presence.
2. **Given** only app source code changes (no portal files touched), **When** CI runs, **Then** the portal's own build/lint check does not execute.
3. **Given** a maintainer wants to build the portal, **When** they run the designated portal build command, **Then** a static output is produced with no external hosting or CDN dependency required.

---

### Edge Cases

- What happens when a reader requests a portal page/locale combination that doesn't exist yet (e.g., a very new page not yet translated)? Portal falls back to displaying the English version of that page with a visible notice that a translation is not yet available, rather than a broken link or 404.
- How does the parity check handle a page that exists in English but has been intentionally marked as English-only (e.g., a page not relevant to translate, such as a contributor-only technical note)? An explicit exemption mechanism is needed so such pages don't perpetually fail the check.
- What happens if a non-English page has *more* sections than its English counterpart (over-translation or drift in the other direction)? Treated the same as a mismatch — the check flags any heading-count difference, not just deficits.
- How does the portal behave if a self-hoster deploys it without ever configuring anything? It must work out of the box as static content with no required external services (no CDN, no telemetry, no accounts).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The documentation portal MUST be published as a distinct, statically-built site, kept separate from the main application's runtime code and deployment.
- **FR-002**: The portal MUST provide content covering: installation/deployment for self-hosters, configuration reference, core user guide (prompt versioning, backups, sharing, search, two-factor authentication), and troubleshooting.
- **FR-003**: The portal MUST support four languages: English (default), French, German, and Spanish — matching the locales already shipped in the application's own interface.
- **FR-004**: Each non-English locale MUST maintain its own complete content tree mirroring the English content structure (same set of pages, same relative organization).
- **FR-005**: When a reader switches locale while viewing a page, the portal MUST navigate to the equivalent page in the new locale, not the portal's home page.
- **FR-006**: When a page has not yet been translated into the reader's selected locale, the portal MUST display the English version with a visible "translation not yet available" notice, rather than a broken link or missing page.
- **FR-007**: The project MUST provide an automated check that verifies, for each non-English locale, that every English page has a corresponding page (file-existence parity).
- **FR-008**: The project MUST provide an automated check that verifies, for each translated page, that its count of section headings matches its English counterpart (structural parity), flagging both missing and extra headings.
- **FR-009**: The parity check MUST report failures with enough detail to act on immediately: which page, which locale, and what specifically differs (missing page vs. heading-count mismatch, with the actual counts).
- **FR-010**: The parity check MUST run automatically before changes to documentation content are merged, and MUST support being run manually.
- **FR-011**: The project MUST provide a documented exemption mechanism for English-only pages that are not meant to be translated, so those pages do not fail the parity check.
- **FR-012**: The portal's build and lint tooling MUST be triggered only by changes to the portal's own content/directory, not by unrelated application code changes.
- **FR-013**: The portal MUST build to static output requiring no external CDN, hosting service, or telemetry/analytics integration to function.
- **FR-014**: The portal MUST be reachable via the project's existing build workflow (e.g., a dedicated command alongside the app's existing build commands) so maintainers have one discoverable entry point to build it.
- **FR-015**: The portal's release-notes section MUST be able to reflect published application releases, in each of the four locales.

*Explicitly out of scope for this feature (per issue #89):*

- Role-based content branching, compliance/audit-oriented content, or governance metadata (owner roles, review cadence) — not applicable, this application is not used in a regulated environment.
- Offline PDF export bundles.
- Multi-version documentation branching by application release.
- Automated translation-quality verification (only structural parity is automated; prose correctness still requires human review).

### Key Entities

- **Documentation Page**: A single unit of content (e.g., "Installing via Docker") that exists once per locale it has been translated into; has a title, body content organized into headed sections, and belongs to one content category (installation, configuration, user guide, troubleshooting, release notes).
- **Locale Content Tree**: The complete set of Documentation Pages published for one language (English, French, German, or Spanish); the English tree is authoritative and defines which pages and sections are expected to exist in the others.
- **Parity Report**: The output of the automated structural check, listing per non-English locale: pages missing entirely, and pages present but with a heading-count mismatch against their English counterpart.
- **Translation Exemption**: A marker on a specific English page indicating it is intentionally excluded from the parity check and not expected to be translated.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A self-hoster can find and follow installation instructions to a running deployment in their preferred supported language without needing to consult English source material.
- **SC-002**: 100% of published English documentation pages in the initial content set have a corresponding, structurally-matching page in each of the French, German, and Spanish trees at launch (excluding explicitly exempted pages).
- **SC-003**: Any future content change that introduces a missing translation or a structural mismatch between locales is caught by the automated parity check before it reaches readers, with zero reliance on a human noticing by manual inspection.
- **SC-004**: A maintainer can change or add English documentation content without needing to touch the main application's source code, build, or deployment process, and vice versa.
- **SC-005**: The portal is fully usable (all pages readable, navigable, and searchable within the portal) with no external network dependency beyond the initial page load — no CDN, analytics, or third-party accounts required.

## Assumptions

- The initial content set targets the pages explicitly listed in issue #89 (installation/deployment, configuration, user guide covering versioning/backups/sharing/search/2FA, troubleshooting, release notes); additional pages can be added later following the same locale-parity discipline.
- French, German, and Spanish translations for the initial page set are produced through a mix of drafting and review; the parity check validates structure only, so a human reviewer is still assumed for translation accuracy.
- The portal is self-hosted as static files alongside or near the existing application deployment; it does not require its own database, backend service, or user accounts.
- "Section heading" for parity-check purposes means Markdown-style headings within a page's content (matching the granularity used in the prior rollout referenced in issue #89).
- The portal's release-notes section draws from the same information already tracked in the project's existing changelog process, translated into the four supported locales.
- Unlike user guide (5 named sub-pages), the initial troubleshooting scope is a single consolidated page, not a category expected to grow multiple sub-pages at launch; splitting it into topic-specific pages is a future addition subject to the same locale-parity discipline as any other page.
