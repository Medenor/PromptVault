# Feature Specification: Dynamic Prompt Placeholders

**Feature Branch**: `006-prompt-placeholders`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "Add dynamic placeholder support to prompts. Users can write placeholders in prompt content using square-bracket syntax like [DURATION] or [TYPE OF PRESENTATION] (curly-brace {DURATION} syntax also supported). When viewing/using a prompt containing placeholders, PromptVault auto-detects them and shows a form with an input field per unique placeholder. The user fills in values, and when copying the prompt, all placeholder tokens are replaced with the user-provided values in the copied text, preserving the rest of the prompt formatting. Placeholders must integrate with existing prompt versioning, search, filtering, and export features without breaking them."

**Related**: Codeberg issue [#42](https://codeberg.org/medenor/promptvault/issues/42) ("feat: Use placeholders to dynamically module prompt content").

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fill in placeholders and copy a ready-to-use prompt (Priority: P1)

A user opens a prompt whose content contains bracketed tokens such as `[DURATION]`, `[TYPE OF PRESENTATION]`, and `[INSERT PRESENTATION TITLE]`. Instead of manually editing the text before pasting it elsewhere, they see a form with one input per distinct placeholder, fill in values, and copy the fully substituted text.

**Why this priority**: This is the entire value proposition of the ticket — turning static prompt text into a reusable template. Without this, nothing else in the feature matters.

**Independent Test**: Can be fully tested by opening a prompt containing one or more bracketed placeholders, confirming a form field appears for each distinct placeholder, entering values, and confirming the copied text has every occurrence of each placeholder replaced with the corresponding value while all other text is unchanged.

**Acceptance Scenarios**:

1. **Given** a prompt whose content contains `[DURATION]`, `[TYPE OF PRESENTATION]`, and `[INSERT PRESENTATION TITLE]`, **When** the user opens the prompt for use, **Then** the system displays exactly one input field per distinct placeholder (3 fields), labeled with the placeholder name.
2. **Given** the placeholder form is displayed, **When** the user fills in a value for each field and copies the prompt, **Then** the copied text has every occurrence of each placeholder token replaced with its corresponding value, and all non-placeholder text is preserved exactly as written.
3. **Given** a placeholder appears more than once in the same prompt (e.g., `[TITLE]` used twice), **When** the user fills in a single value for it, **Then** every occurrence of that placeholder is replaced with the same value on copy.
4. **Given** a prompt contains no placeholders, **When** the user opens it for use, **Then** no placeholder form is shown and copying behaves exactly as it does today.

---

### User Story 2 - Copy a prompt with placeholders left unfilled (Priority: P2)

A user opens a prompt with placeholders but decides to copy it without filling in some or all of the fields — for example, to paste it into another tool for later editing, or because they only care about certain placeholders right now.

**Why this priority**: Users must not be blocked from using the existing "just copy the prompt" workflow; forcing every field to be filled would be a regression for anyone who wants the raw template.

**Independent Test**: Can be fully tested by opening a prompt with placeholders, leaving one or more fields blank, and confirming the copy action still succeeds, with unfilled placeholders left as their original bracketed/braced token in the copied text.

**Acceptance Scenarios**:

1. **Given** a prompt with multiple placeholders, **When** the user leaves one field blank and fills in the others, **Then** copying produces text where filled placeholders are substituted and the blank one remains as its original token.
2. **Given** a prompt with placeholders, **When** the user copies without opening or touching the placeholder form at all, **Then** the copied text is identical to the raw prompt content (all tokens unchanged), matching current behavior.

---

### User Story 3 - Placeholders survive editing, versioning, search, filtering, and export (Priority: P2)

A user edits a prompt's content (adding, removing, or renaming placeholders), views its version history, searches or filters the prompt library, or exports prompts — and expects placeholder tokens to be treated as ordinary text by every one of these existing features, with the placeholder form correctly reflecting whatever placeholders exist in the currently viewed version.

**Why this priority**: This is an integration/non-regression requirement rather than new user-facing value, but the ticket explicitly calls it out and a break here would silently corrupt saved history or search results.

**Independent Test**: Can be fully tested by creating a prompt with placeholders, editing it to change the set of placeholders, confirming version history stores each version's raw content unchanged (tokens included), confirming search/filter matches placeholder text like any other prompt text, and confirming exported content (CSV/Markdown/JSON) contains the raw, unsubstituted placeholder tokens.

**Acceptance Scenarios**:

1. **Given** a prompt with placeholders is edited to add a new placeholder or remove an existing one, **When** the user next opens it for use, **Then** the placeholder form reflects exactly the placeholders present in the current content.
2. **Given** a prompt has multiple saved versions with different placeholders in each, **When** the user views an older version, **Then** the placeholder form (if shown for that version) reflects that version's placeholders, not the current version's.
3. **Given** a prompt's content contains a placeholder token, **When** the user searches for text that matches part of that token, **Then** the prompt is returned by search like any other text match.
4. **Given** a prompt with placeholders, **When** the user exports it (CSV, Markdown, or JSON), **Then** the exported content contains the original, unsubstituted placeholder tokens exactly as stored.

---

### Edge Cases

- What happens when a prompt mixes both syntaxes, e.g., `[DURATION]` and `{DURATION}` in the same content? Treated as two distinct placeholders (different tokens), each getting its own field, since the two syntaxes are not declared equivalent to each other.
- What happens when brackets/braces appear in the content but don't look like a placeholder (e.g., empty `[]`, unmatched `[abc`, or a code sample containing literal brackets like `array[0]`)? Only well-formed tokens (non-empty, matching opening/closing pair, no nested brackets/braces, no internal newline) are treated as placeholders; anything else is left as plain text.
- What happens when a placeholder name contains unusual characters (punctuation, numbers, mixed case)? The full text between the delimiters is used as the placeholder's identity and display label as-is; matching is exact and case-sensitive.
- What happens when the user copies a prompt with placeholders where the substituted values would make the text extremely long? No special handling — substitution is a straightforward text replacement with no length limit beyond existing prompt content limits.
- What happens when a placeholder value contains characters that look like another placeholder token (e.g., user enters `[NESTED]` as the value for `[DURATION]`)? The value is inserted as literal text and is not itself re-scanned for placeholders (single-pass substitution, no recursive expansion).
- What happens on a prompt with a very large number of distinct placeholders? All distinct placeholders get a field; no cap is imposed by this feature (existing prompt content size limits still apply).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST recognize placeholder tokens in prompt content written in square-bracket syntax (`[NAME]`) and curly-brace syntax (`{NAME}`), where `NAME` is any non-empty run of characters that does not itself contain a newline or a nested opening/closing delimiter of the same kind.
- **FR-002**: System MUST treat `[NAME]` and `{NAME}` as two distinct placeholder identities even when `NAME` is identical, and MUST treat placeholder matching as case-sensitive and exact-text.
- **FR-003**: System MUST detect all distinct placeholder tokens present in a prompt's current content and present exactly one input field per distinct token when the user opens that prompt for use.
- **FR-004**: System MUST NOT display a placeholder form for prompts whose content contains no recognized placeholder tokens; copy behavior for such prompts MUST remain unchanged from current behavior.
- **FR-005**: Users MUST be able to enter a text value for each detected placeholder field.
- **FR-006**: System MUST, when the user triggers copy after filling in the placeholder form, replace every occurrence of each filled placeholder token in the prompt content with its corresponding value, leaving all other content unchanged.
- **FR-007**: System MUST leave any placeholder token with no user-provided value unchanged (as its original bracketed/braced token) in the copied text.
- **FR-008**: Users MUST be able to copy a prompt containing placeholders without interacting with the placeholder form at all, producing output identical to the current raw-copy behavior.
- **FR-009**: System MUST re-derive the set of displayed placeholder fields whenever the underlying prompt content changes (including after edits), rather than caching a stale placeholder list.
- **FR-010**: System MUST store prompt content, including placeholder tokens, as plain unmodified text in prompt versioning/history — no substitution is ever persisted into stored prompt content.
- **FR-011**: System MUST NOT alter how search and filtering match prompt text — placeholder tokens are matched as ordinary substrings like any other prompt content.
- **FR-012**: System MUST NOT alter export output (CSV, Markdown, JSON, or any other supported export format) — exported content MUST contain the original, unsubstituted placeholder tokens.
- **FR-013**: System MUST perform placeholder substitution as a single, non-recursive pass — a user-provided value is inserted as literal text and is not itself scanned for further placeholder tokens.

### Key Entities

- **Placeholder Token**: A bracketed (`[NAME]`) or braced (`{NAME}`) span of text found within a prompt's content. Identity is the exact delimiter type plus the exact text between delimiters. Not persisted as a separate record — always derived on the fly from the prompt's current content.
- **Placeholder Value Set**: The transient, per-use collection of user-entered values keyed by placeholder token, scoped to a single viewing/copy session for a prompt. Not persisted with the prompt or its version history.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can go from opening a prompt with placeholders to copying a fully filled-in version in under 30 seconds for a prompt with up to 5 distinct placeholders.
- **SC-002**: 100% of distinct placeholder tokens in a prompt's content are detected and given exactly one corresponding form field, with zero duplicate fields for repeated tokens.
- **SC-003**: 100% of existing search, filter, versioning, and export behaviors continue to return unchanged, correct results for prompts containing placeholder tokens (no regressions introduced).
- **SC-004**: Users can copy a prompt with placeholders left entirely or partially unfilled with zero errors, receiving text with unfilled tokens preserved verbatim.

## Assumptions

- Placeholder values entered by the user are treated as plain text substitutions only; no input type beyond free text (dropdown, checkbox, etc., mentioned as a "could support" in the ticket) is in scope for this spec's initial version — deferred to future work.
- Placeholder "management" as a standalone feature (a dedicated place to create/edit/delete/organize placeholder definitions independent of prompt content) is out of scope; placeholders are derived purely from tokens already present in prompt text, not authored as separate entities.
- The two syntaxes (`[NAME]` and `{NAME}`) are supported as alternatives a user may choose per-prompt; there is no requirement to normalize or convert between them.
- Placeholder detection and substitution are a client-facing/use-time concern only — no schema changes to how prompt content is stored are required, since the raw text (including tokens) is exactly what's already persisted today.
- Nested or nested-looking placeholders (a bracket/brace inside another) are not supported; such content is left untouched as plain text rather than erroring.
- This spec does not require persisting the last-used placeholder values across sessions; each time a user opens a prompt for use, the form starts blank. Persisting recent values per prompt is a reasonable future enhancement but not required here.
