# Feature Specification: Full-Text Search

**Feature Branch**: `008-full-text-search`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "Replace `ilike '%term%'` scans with real full-text search — relevance ranking and result snippets/highlighting; keep substring matching as a fallback. Native full-text search in both backends means zero new dependencies. Carried from ROADMAP 2026 #3 (issue #15)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ranked, relevant search results (Priority: P1)

A user with a growing vault types one or more words into the search box. Instead of results appearing in an arbitrary or purely chronological order, the most relevant prompts — those where the search words appear in the title or appear frequently — rise to the top of the list. The user finds what they were looking for in the first few results rather than scrolling.

**Why this priority**: This is the core value of the feature. Substring matching returns every prompt that contains the term with no notion of which is the best match, forcing users to scan the whole result set. Ranking is what turns "a list of matches" into "an answer". It also unblocks the performance goal, since ranked search uses an index that substring scans cannot.

**Independent Test**: Seed a vault with prompts where a term appears in the title of one prompt and buried once in the body of another. Search for that term and confirm the title match is ordered above the body match, and that both appear. Delivers value on its own even without snippets.

**Acceptance Scenarios**:

1. **Given** a vault where the word "python" appears in one prompt's title and once in another prompt's long body, **When** the user searches "python", **Then** both prompts appear and the title match is ranked higher.
2. **Given** a multi-word query "code review", **When** the user searches, **Then** prompts containing both words rank above prompts containing only one of them.
3. **Given** an existing sort option (e.g. "newest first") is selected, **When** the user searches, **Then** the chosen sort order is honored and ranking applies as the default only when no explicit sort is chosen.

---

### User Story 2 - Result snippets with highlighted matches (Priority: P2)

When results are shown, each result card displays a short excerpt of the matching content with the search terms visually highlighted, so the user can judge relevance at a glance without opening each prompt.

**Why this priority**: Snippets dramatically reduce the number of prompts a user must open to find the right one, but ranked results (P1) already deliver the primary benefit. Snippets are a strong enhancement layered on top.

**Independent Test**: Search a term that appears in the middle of a long prompt body. Confirm the result card shows an excerpt centered on the match with the term highlighted, and that the excerpt is safely rendered (no raw markup leaks, no script execution).

**Acceptance Scenarios**:

1. **Given** a prompt whose body contains the search term deep in a long text, **When** the user searches that term, **Then** the result card shows a short excerpt around the match with the term highlighted.
2. **Given** a search term that includes characters that look like markup or formatting, **When** results render, **Then** the excerpt is displayed as plain text with only the intended highlight, and no markup is interpreted.
3. **Given** a prompt that matches on title only, **When** results render, **Then** a sensible excerpt (or no excerpt) is shown without error.

---

### User Story 3 - Fast search on large vaults (Priority: P2)

A user with thousands of prompts searches and gets results back quickly, with response time staying roughly flat as the vault grows rather than getting noticeably slower with each added prompt.

**Why this priority**: Performance is a primary motivation for the feature, but it is only observable at scale and is delivered by the same mechanism as P1. It is called out separately so it is explicitly measured and tested.

**Independent Test**: Load a benchmark vault of several thousand prompts, run a representative query, and confirm results return within the target time and are correct, and that the ranked path outperforms the substring-scan baseline on the same data set.

**Acceptance Scenarios**:

1. **Given** a vault of at least 5,000 prompts, **When** the user searches a common term, **Then** results return within the performance target.
2. **Given** the same vault and query, **When** measured against the previous substring-scan behavior, **Then** the new search returns results faster while producing correct matches.

---

### User Story 4 - Reliable fallback and exact/case-sensitive matching (Priority: P3)

Certain searches — case-sensitive matching, or queries the full-text engine cannot interpret — continue to work exactly as they do today by falling back to substring matching, so no existing search behavior is lost.

**Why this priority**: This is a safety net that preserves existing functionality and prevents regressions. It is essential for correctness but is not itself new user-facing value.

**Independent Test**: Enable case-sensitive search and confirm results respect case exactly as before. Submit a query containing only special/operator characters and confirm it returns sensible results (or a clean empty result) rather than an error.

**Acceptance Scenarios**:

1. **Given** case-sensitive search is enabled, **When** the user searches "API" vs "api", **Then** results respect case exactly as they did before this feature.
2. **Given** a query composed entirely of special characters the ranking engine cannot parse, **When** the user searches, **Then** the system returns results via the fallback path without surfacing an error.
3. **Given** a query wrapped in quotes as a phrase, **When** the user searches, **Then** results match the phrase as a unit.

### Edge Cases

- **Empty or whitespace-only query**: returns the standard unfiltered/empty-search behavior, not an error.
- **Query of only operator/punctuation characters**: sanitized so it never produces a search-engine syntax error; falls back to substring matching if needed.
- **Very large existing vault upgrading to this feature**: the one-time index build during upgrade may take several seconds; the system remains usable and the delay is communicated in release notes.
- **Prompt with empty title, body, or note**: indexing and searching handle missing fields without error.
- **Highlighted excerpt containing markup-like characters**: rendered safely as text; only the intended highlight is applied.
- **Result count**: the number reported for a search matches the number of results actually returned by the ranked query (count and list stay consistent).
- **Prompts created, edited, or deleted after the index exists**: newly written content becomes searchable and deleted content stops appearing, with no manual reindex step.
- **Pagination**: ranked results paginate consistently so a prompt never appears on two pages or is skipped between pages.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST rank search results by relevance, with matches in a prompt's title weighted more heavily than matches in its body, and body matches weighted more heavily than matches in its note.
- **FR-002**: System MUST return the same set of matching prompts that a user would reasonably expect from the search term, and MUST NOT drop matches that the previous substring behavior would have found for ordinary word queries.
- **FR-003**: System MUST rank prompts matching all words of a multi-word query above prompts matching only some of the words.
- **FR-004**: Users MUST be able to request ranked search as the default behavior, while still being able to apply existing explicit sort options, which take precedence over relevance ordering when chosen.
- **FR-005**: System MUST return a short contextual excerpt ("snippet") for each result, centered on the matched terms where the match occurs in body content.
- **FR-006**: System MUST highlight the matched terms within each excerpt.
- **FR-007**: System MUST render excerpts and highlights safely as text, so that content resembling markup or scripts is never interpreted or executed.
- **FR-008**: System MUST report a result count that is consistent with the ranked result list for the same query.
- **FR-009**: System MUST preserve existing case-sensitive search behavior by using substring matching for case-sensitive queries.
- **FR-010**: System MUST fall back to substring matching, without surfacing an error to the user, whenever the query cannot be interpreted by the ranking engine.
- **FR-011**: System MUST sanitize user input so that queries containing special or operator characters never cause a search failure.
- **FR-012**: System MUST support quoted phrases as an explicit way to match a sequence of words as a unit.
- **FR-013**: System MUST keep search results current as prompts are created, edited, or deleted, with no manual reindexing step required by the user.
- **FR-014**: System MUST paginate ranked results consistently, so no result is duplicated across pages or skipped between pages.
- **FR-015**: System MUST perform a one-time index preparation when upgrading an existing vault, after which existing prompts are fully searchable.
- **FR-016**: Search results MUST return within the performance target on a vault of at least 5,000 prompts, and response time MUST NOT degrade linearly with vault size the way substring scanning does.
- **FR-017**: System MUST behave consistently across both supported storage backends, producing equivalent ranking and snippet behavior for the same data and query.

### Key Entities *(include if feature involves data)*

- **Prompt**: The searchable item. Relevant attributes for this feature are its title, its body/prompt text, and its note. Each contributes to relevance with a different weight (title highest, then body, then note).
- **Search Query**: The user-supplied text, optionally including quoted phrases, plus flags such as case-sensitive mode and whether ranked ordering is requested.
- **Search Result**: A matched prompt augmented with a relevance rank and a contextual excerpt ("match context") containing highlighted terms.
- **Search Index**: A derived, automatically maintained representation of prompt content that enables fast ranked lookup. It is kept in sync with prompts and is rebuilt once on upgrade.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a vault of at least 5,000 prompts, a typical single-word search returns results in under 1 second.
- **SC-002**: Ranked search returns results measurably faster than the previous substring-scan behavior on the same 5,000-prompt data set, verified by a repeatable benchmark.
- **SC-003**: For queries where a term appears in a title, the title match appears within the top results ahead of body-only matches in 100% of tested cases.
- **SC-004**: 100% of previously-supported searches (including case-sensitive and special-character queries) continue to return without error after the change.
- **SC-005**: Search behavior — matches, ranking order, and snippet presence — is equivalent across both supported storage backends for the same seeded data set, verified by the test matrix.
- **SC-006**: No search excerpt or highlight results in interpreted markup or executed script for any tested input, including inputs crafted to resemble markup.
- **SC-007**: After creating, editing, or deleting a prompt, the change is reflected in search results without any manual reindex action.

## Assumptions

- The two supported storage backends are the project's existing lightweight/embedded store (used for local and test environments) and its production database; both provide native full-text capabilities, so no new external search service or dependency is introduced.
- Ranked search is the default ordering for a search with no explicit sort selected; existing sort options remain available and override ranking when chosen.
- The performance target for search response is "under 1 second" for typical queries at the 5,000-prompt scale, consistent with standard web-app expectations, since no stricter target was specified.
- The one-time index build on upgrade is acceptable to run as part of the normal upgrade/migration step, and a brief delay on very large vaults is acceptable if communicated in release notes.
- The set of searchable fields is exactly title, body/prompt text, and note — the same fields searched today.
- Quoted-phrase support is limited to matching a contiguous sequence of words; advanced boolean operators (AND/OR/NOT syntax) are out of scope for this feature.
- Highlighting is applied through the existing safe text-rendering path so that snippet output cannot introduce unsafe content.
- Stemming/language-specific behavior follows each backend's default full-text configuration; no custom multilingual tuning is in scope for this version.
