# Feature Specification: Prompt Semantic Versioning

**Feature Branch**: `001-prompt-versioning`

**Created**: 2026-07-01

**Status**: Draft

**Input**: User description: "Add numbered versioning for prompts, ideally using a semantic version format such as MAJOR.MINOR.PATCH. The prompt detail view should clearly display the current version number. Version history should also show previous numbered versions. It should be possible to compare the current PromptVault version with versions stored or referenced elsewhere, making it easy to identify outdated external copies."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assign and Display Version Number (Priority: P1)

A user edits a prompt in PromptVault and assigns it a semantic version number (e.g., `1.1.0`). The version number is prominently visible on the prompt detail view at all times. This makes PromptVault the single source of truth, and the version number is easy to copy and reference externally.

**Why this priority**: Without a visible, authoritative version number, none of the comparison or history workflows are possible. This is the foundational capability.

**Independent Test**: Can be fully tested by creating or editing a prompt, setting a version number, and confirming it appears on the prompt detail view — delivering immediate visibility of the canonical version.

**Acceptance Scenarios**:

1. **Given** a prompt exists without a version, **When** the user edits the prompt and sets version `1.0.0`, **Then** the prompt detail view displays `v1.0.0` clearly.
2. **Given** a prompt with version `1.0.0`, **When** the user updates the prompt content and bumps the version to `1.1.0`, **Then** the detail view shows `v1.1.0` and the previous entry `1.0.0` is preserved in version history.
3. **Given** a user attempts to save version `abc` (invalid format), **When** the form is submitted, **Then** an error is shown explaining that versions must follow the `MAJOR.MINOR.PATCH` format and the save is blocked.

---

### User Story 2 - Version History Shows Numbered Versions (Priority: P2)

A user opens the version history of a prompt and can see each historical version labeled with its semantic version number alongside the timestamp. This allows the user to understand how the prompt evolved and identify when a specific version was introduced.

**Why this priority**: Numbered version history turns an audit log into a navigable changelog, enabling users to understand which changes corresponded to which version bump.

**Independent Test**: Can be fully tested by creating a prompt, saving it multiple times with different version numbers, and opening version history — verifying that each entry shows the correct version label.

**Acceptance Scenarios**:

1. **Given** a prompt has been saved at versions `1.0.0`, `1.1.0`, and `1.2.0`, **When** the user opens version history, **Then** each entry displays its semantic version number next to the save date.
2. **Given** a version history entry labeled `1.1.0`, **When** the user views that entry, **Then** the prompt content from that version is shown along with the version identifier.
3. **Given** a prompt created before versioning was introduced, **When** the user views its version history, **Then** historical entries without a version number are clearly labeled as "unversioned" rather than displaying an empty field.

---

### User Story 3 - Copy Version Metadata for External Comparison (Priority: P3)

A user copies the current prompt content with an embedded version identifier (e.g., a metadata line such as `<!-- prompt-version: 1.2.0 -->` or similar portable marker) and pastes it into an external platform (ChatGPT GPT instructions, Claude Project, Gemini system prompt). Later, by checking the embedded identifier in the external platform against the current PromptVault version, the user can immediately tell whether the external copy is outdated.

**Why this priority**: This is the cross-platform synchronization use case that motivates the whole feature. It is prioritized P3 because it depends on P1 (visible version) and extends the core workflow into external environments.

**Independent Test**: Can be tested by using the "copy with version" action, verifying the copied text includes an identifiable version marker, and confirming the metadata line includes a note instructing LLMs to ignore it.

**Acceptance Scenarios**:

1. **Given** a prompt at version `1.2.0`, **When** the user invokes "Copy with version metadata", **Then** the clipboard contains the prompt content plus a metadata line encoding the version (e.g., `<!-- prompt-version: 1.2.0 | Ignore this line when reading the prompt. -->`).
2. **Given** a user has pasted a `1.1.0` copy into an external platform, **When** they later open PromptVault and see the current version is `1.2.0`, **Then** the version badge makes it immediately obvious the external copy is one minor version behind.
3. **Given** the copied metadata line is included in an active system prompt, **When** an LLM reads the prompt, **Then** the metadata line is self-describing enough that the LLM ignores it without special configuration.

---

### Edge Cases

- What happens when a user saves a prompt without setting any version number? (Version remains unset; no version is shown rather than defaulting to `0.0.0`.)
- What if two users try to save the same version number concurrently? (Last write wins; version history records both saves with a timestamp difference.)
- What happens when the user enters a version lower than the current one (e.g., saving `1.0.0` on a prompt currently at `1.2.0`)? (System warns that the version is lower than the current version but allows the save — no strict enforcement of monotonic versioning.)
- How are prompts without any version history displayed in listings? (No version badge or badge shows "—".)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to set a semantic version number (`MAJOR.MINOR.PATCH`) on any prompt when creating or editing it.
- **FR-002**: System MUST validate that version numbers conform to the `MAJOR.MINOR.PATCH` format (three non-negative integers separated by dots) and reject non-conforming input with a user-friendly error message.
- **FR-003**: The prompt detail view MUST prominently display the current semantic version number of the prompt.
- **FR-004**: Version history MUST display the semantic version number associated with each saved revision alongside existing timestamp and diff information.
- **FR-005**: System MUST preserve version numbers across all historical revisions; removing a version number from a prompt MUST NOT retroactively affect past history entries.
- **FR-006**: System MUST provide a "Copy with version metadata" action on the prompt detail view that places the prompt content plus a portable, self-describing version metadata line on the clipboard.
- **FR-007**: The metadata line appended during copy MUST include an instruction for LLMs to ignore the line when processing the prompt.
- **FR-008**: Prompts created before this feature was introduced MUST display as "unversioned" in history entries rather than showing an empty or null value.
- **FR-009**: Setting a version number MUST be optional; users MUST be able to save prompts without specifying a version.

### Key Entities

- **Prompt**: An existing entity; gains an optional `version` field storing the current semantic version string. Historical versions retain the version string at the time of save.
- **PromptRevision**: An existing entity representing a saved snapshot of a prompt; gains an optional `version` field recording the semantic version at the time of that save.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can set or update a prompt version in under 30 seconds from opening the edit form.
- **SC-002**: The current version number is visible without scrolling on the prompt detail view at all standard desktop viewport widths.
- **SC-003**: 100% of version history entries for versioned prompts display the correct semantic version label — zero entries show a blank or null version field for prompts that have been versioned.
- **SC-004**: The "Copy with version metadata" action produces output that includes both the full prompt content and a parseable version identifier in a single copy operation.
- **SC-005**: Users report being able to identify whether an external prompt copy is outdated by comparing the embedded version string to the PromptVault badge, without any additional tooling.

## Assumptions

- The existing version history mechanism (revisions / audit trail) is already in place and this feature extends it with a version label rather than replacing it.
- Semantic versioning (`MAJOR.MINOR.PATCH`) is the only supported format; short forms like `1.0` or pre-release suffixes like `1.0.0-beta` are out of scope for this iteration.
- The feature is targeted at the web UI; API support for reading/writing version numbers follows the same data model but does not require dedicated new API endpoints beyond what the existing prompt update API already exposes.
- Multi-user concurrent editing conflict resolution follows the existing last-write-wins strategy; no optimistic locking is introduced by this feature.
- The version metadata line format for the "Copy with version metadata" action will use an HTML comment (`<!-- ... -->`) as the default, since it is invisible in most rendered contexts and broadly portable across platforms that accept markdown or plain text system prompts.
