# Feature Specification: Pagination & Lazy Loading (Core)

**Feature Branch**: `005-pagination-lazy-loading`

**Created**: 2026-07-09

**Status**: Draft

**Input**: User description: "Implement server-side offset pagination for the prompts list. Scope (from Codeberg issue #14, 'Pagination & Lazy Loading System', scoped down from the original ~23-bullet request): Backend: add page/limit query params to GET /api/prompts and GET /api/prompts/search with a standardized pagination response envelope, sensible default and max page size, existing filters continue to work in combination with pagination, changing a filter resets to page 1. Frontend: 'Load More' button pattern on the main prompts list with a loading state indicator, page size selector (25, 50, 100). Out of scope: cursor pagination, infinite scroll, virtual scrolling, scroll restoration, pre-fetching, URL sync, jump-to-page, versions/backups pagination, search analytics, i18n updates."

**Related**: Codeberg issue [#14](https://codeberg.org/medenor/promptvault/issues/14) (scoped down — see Assumptions). Depends on issue #13 (Database Migration, closed).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse a large prompt library without a slow initial load (Priority: P1)

A user with a large prompt collection (hundreds or thousands of prompts) opens the main prompt list. Instead of waiting for every prompt to load at once, they see the first page of results quickly and can request more as needed.

**Why this priority**: This is the core problem statement of the ticket — today the entire dataset loads in a single request, which the test suite already shows takes several seconds at 1,000 prompts. Without this, no other pagination behavior matters.

**Independent Test**: Can be fully tested by loading the main prompt list with a large dataset and confirming only the first page's worth of prompts is returned and rendered, with a way to request the next page.

**Acceptance Scenarios**:

1. **Given** a library with more prompts than the default page size, **When** the user opens the main prompt list, **Then** only the first page of prompts is loaded and displayed, along with an indicator that more results are available.
2. **Given** the user is viewing the first page of results, **When** they trigger "Load More", **Then** the next page of prompts is fetched and appended to the currently displayed list without reloading or losing the prompts already shown.
3. **Given** the user has loaded all pages, **When** they view the list, **Then** the "Load More" control is no longer available or is disabled, and no further requests are made.

---

### User Story 2 - Combine pagination with search and filters (Priority: P1)

A user searches or filters the prompt list (by text, category, tag, or favorite status) and expects pagination to apply to the filtered result set, not the full library.

**Why this priority**: Search/filter is the primary way users narrow large libraries; pagination must not break or bypass existing filtering behavior, or the feature regresses core functionality.

**Independent Test**: Can be fully tested by applying a filter that matches more results than one page, confirming pagination metadata reflects the filtered count (not the total library count), and confirming "Load More" continues to respect the active filter.

**Acceptance Scenarios**:

1. **Given** the user has applied a search term or filter, **When** the filtered result set is larger than one page, **Then** the system returns only the first page of matching prompts along with a total count of matching prompts.
2. **Given** the user is viewing paginated filtered results, **When** they change the search term, category, tag, or favorites filter, **Then** the result set resets to page 1 with the new filter applied.
3. **Given** the user is viewing paginated filtered results, **When** they trigger "Load More", **Then** the next page of the same filtered set is appended.

---

### User Story 3 - Choose how many prompts load per page (Priority: P2)

A user who wants fewer, larger batches (or smaller, faster-loading batches) selects a preferred page size.

**Why this priority**: Useful power-user control, but the library is usable and the core problem (slow full-load) is solved without it — hence lower priority than Stories 1 and 2.

**Independent Test**: Can be fully tested by changing the page size selector and confirming the next fetch (whether a fresh load or "Load More") uses the newly selected size.

**Acceptance Scenarios**:

1. **Given** the user is viewing the prompt list, **When** they select a different page size (25, 50, or 100), **Then** the list reloads from page 1 using the newly selected page size.
2. **Given** the user selects a page size, **When** they subsequently use "Load More", **Then** each additional page fetched uses the selected page size.

---

### Edge Cases

- What happens when the library (or filtered result set) has zero prompts? System returns an empty page with total count of 0, and no "Load More" control is shown.
- What happens when the requested page number is beyond the last available page? System returns an empty result set for that page rather than an error, with `has_next` set to false.
- What happens when a client requests a page size above the configured maximum? System clamps the request down to the maximum allowed page size rather than rejecting it.
- What happens when a client requests an invalid page (zero, negative, non-numeric)? System treats it as page 1 (or the nearest valid value) rather than erroring.
- What happens if new prompts are added or removed while the user is paging through results? Later pages reflect the current state at fetch time; minor shifts (an item appearing twice or being skipped) are acceptable and not required to be prevented in this scope.
- What happens when "Load More" is triggered while a previous page request is still in flight? The system must not allow duplicate concurrent requests for the same next page; the control shows a loading state and is disabled until the in-flight request completes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept page and page-size parameters on the main prompt listing capability and on the prompt search/filter capability.
- **FR-002**: System MUST return, alongside the page of prompt results, the current page number, total page count, total matching count, and whether a next/previous page exists.
- **FR-003**: System MUST apply a default page size when none is specified.
- **FR-004**: System MUST enforce a maximum allowed page size, clamping any request that exceeds it.
- **FR-005**: System MUST continue to support existing filter criteria (search text, category, tag, favorites, case sensitivity) in combination with pagination, returning only matching prompts within the requested page.
- **FR-006**: System MUST report total counts and page counts relative to the currently applied filters, not the unfiltered library.
- **FR-007**: Users MUST be able to request the next page of currently displayed results via a "Load More" action without losing or re-fetching previously displayed prompts.
- **FR-008**: System MUST show a loading indicator while a page request is in flight and MUST prevent duplicate concurrent requests for the same next page.
- **FR-009**: System MUST hide or disable the "Load More" action once no further pages are available.
- **FR-010**: Users MUST be able to select a page size from a defined set of options (25, 50, 100).
- **FR-011**: When the user changes any filter or the page size, the system MUST reset to the first page of the new result set.
- **FR-012**: System MUST handle out-of-range or invalid page/page-size inputs gracefully (see Edge Cases) without returning an error to the user.

### Key Entities

- **Prompt Page Result**: A bounded slice of the prompt collection returned for a single request — includes the list of prompts for that page plus pagination metadata (current page, total pages, total count, has-next, has-previous).
- **Pagination State**: The client-side record of what has been loaded so far for the current filter context — current page size, current page reached, and the accumulated list of prompts displayed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Opening the main prompt list on a library of 1,000+ prompts returns and renders the first page in under 1 second (versus several seconds observed today with full-dataset loads).
- **SC-002**: The payload size of the initial prompt list request is reduced by at least 90% for libraries of 1,000+ prompts, compared to loading the entire dataset.
- **SC-003**: Users can retrieve additional prompts via "Load More" with each subsequent request completing in under 1 second under normal conditions.
- **SC-004**: 100% of existing search/filter behaviors continue to return correct, complete results when combined with pagination (no prompts silently dropped or duplicated across pages under stable data).
- **SC-005**: Users can switch page size and see the effect reflected in the very next page load, with zero errors across the three supported page sizes (25, 50, 100).

## Assumptions

- This spec covers only offset-based pagination (page/limit) for the main prompt list and prompt search endpoints. Cursor-based pagination, infinite scroll, virtual scrolling, scroll-position restoration, smart pre-fetching, URL query-param synchronization, and a "jump to page" control are explicitly deferred to future work, per user decision.
- Pagination for the version-history and backup-list listings (also mentioned in the original ticket) is out of scope for this spec and will be addressed separately.
- Search analytics, search-result CSV export, and i18n string updates related to pagination messaging are out of scope for this spec.
- The default page size is assumed to be 50 and the maximum allowed page size is assumed to be 100, consistent with the page-size selector options (25, 50, 100). This can be adjusted during planning if the team prefers different values.
- The underlying data store already supports efficient counting and bounded retrieval of records (this feature depends on the completed database migration, issue #13).
- "Load More" appends results to the currently rendered list rather than replacing it, matching the ticket's described UI pattern; a full page-by-page navigation control (first/prev/next/last buttons) is not required for this scope.
