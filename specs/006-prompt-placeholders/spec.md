# Feature Specification: Dynamic Prompt Placeholders

**Feature Branch**: `006-prompt-placeholders`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "Add dynamic placeholder support to prompts. Users can write placeholders in prompt content using square-bracket syntax like [DURATION] or [TYPE OF PRESENTATION] (curly-brace {DURATION} syntax also supported). When viewing/using a prompt containing placeholders, PromptVault auto-detects them and shows a form with an input field per unique placeholder. The user fills in values, and when copying the prompt, all placeholder tokens are replaced with the user-provided values in the copied text, preserving the rest of the prompt formatting. Placeholders must integrate with existing prompt versioning, search, filtering, and export features without breaking them."

**Related**: Codeberg issue [#42](https://codeberg.org/medenor/promptvault/issues/42) ("feat: Use placeholders to dynamically module prompt content").

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Fill in placeholders and copy a ready-to-use prompt (Priority: P1)

A user clicks the Copy button on a prompt card whose content contains bracketed tokens such as `[DURATION]`, `[TYPE OF PRESENTATION]`, and `[INSERT PRESENTATION TITLE]`. Instead of manually editing the text before pasting it elsewhere, the Copy click opens a form with one input per distinct placeholder; the user fills in values and confirms to copy the fully substituted text to the clipboard.

**Why this priority**: This is the entire value proposition of the ticket — turning static prompt text into a reusable template. Without this, nothing else in the feature matters.

**Independent Test**: Can be fully tested by opening a prompt containing one or more bracketed placeholders, confirming a form field appears for each distinct placeholder, entering values, and confirming the copied text has every occurrence of each placeholder replaced with the corresponding value while all other text is unchanged.

**Acceptance Scenarios**:

1. **Given** a prompt whose content contains `[DURATION]`, `[TYPE OF PRESENTATION]`, and `[INSERT PRESENTATION TITLE]`, **When** the user clicks Copy on that prompt's card, **Then** the system opens a form displaying exactly one input field per distinct placeholder (3 fields), labeled with the placeholder name, instead of copying immediately.
2. **Given** the placeholder form is displayed, **When** the user fills in a value for each field and confirms, **Then** the copied text has every occurrence of each placeholder token replaced with its corresponding value, and all non-placeholder text is preserved exactly as written.
3. **Given** a placeholder appears more than once in the same prompt (e.g., `[TITLE]` used twice), **When** the user fills in a single value for it, **Then** every occurrence of that placeholder is replaced with the same value on copy.
4. **Given** a prompt contains no placeholders, **When** the user clicks Copy on that prompt's card, **Then** no placeholder form is shown and copying happens immediately, behaving exactly as it does today.

---

### User Story 2 - Copy a prompt with placeholders left unfilled (Priority: P2)

A user clicks Copy on a prompt with placeholders but decides to copy it without filling in some or all of the fields — for example, to paste it into another tool for later editing, or because they only care about certain placeholders right now.

**Why this priority**: Users must not be blocked from using the existing "just copy the prompt" workflow; forcing every field to be filled would be a regression for anyone who wants the raw template.

**Independent Test**: Can be fully tested by clicking Copy on a prompt with placeholders, leaving one or more fields blank (including the case of leaving all fields blank), and confirming the copy action still succeeds, with unfilled placeholders left as their original bracketed/braced token in the copied text.

**Acceptance Scenarios**:

1. **Given** a prompt with multiple placeholders, **When** the user leaves one field blank and fills in the others, **Then** copying produces text where filled placeholders are substituted and the blank one remains as its original token.
2. **Given** a prompt with placeholders, **When** the placeholder form opens on Copy-click and the user confirms without entering any values, **Then** the copied text is identical to the raw prompt content (all tokens unchanged).

---

### User Story 3 - Placeholders survive editing, versioning, search, filtering, and export (Priority: P2)

A user edits a prompt's content (adding, removing, or renaming placeholders), views its version history, searches or filters the prompt library, or exports prompts — and expects placeholder tokens to be treated as ordinary text by every one of these existing features, with the placeholder form (shown only on Copy-click, per Clarifications) correctly reflecting whatever placeholders exist in the prompt's current content.

**Why this priority**: This is an integration/non-regression requirement rather than new user-facing value, but the ticket explicitly calls it out and a break here would silently corrupt saved history or search results.

**Independent Test**: Can be fully tested by creating a prompt with placeholders, editing it to change the set of placeholders, confirming version history stores each version's raw content unchanged (tokens included) and that the version-history/diff view shows no placeholder form, confirming search/filter matches placeholder text like any other prompt text, and confirming exported content (CSV/Markdown/JSON) contains the raw, unsubstituted placeholder tokens.

**Acceptance Scenarios**:

1. **Given** a prompt with placeholders is edited to add a new placeholder or remove an existing one, **When** the user next clicks Copy on that prompt's card, **Then** the placeholder form reflects exactly the placeholders present in the current content.
2. **Given** a prompt has multiple saved versions with different placeholders in each, **When** the user opens the version-history or diff view, **Then** no placeholder form is shown there (it remains read-only/text-only); the user must Revert to an older version to make it current before the Copy-click placeholder flow applies to it.
3. **Given** a prompt's content contains a placeholder token, **When** the user searches for text that matches part of that token, **Then** the prompt is returned by search like any other text match.
4. **Given** a prompt with placeholders, **When** the user exports it (CSV, Markdown, or JSON), **Then** the exported content contains the original, unsubstituted placeholder tokens exactly as stored.

---

### Edge Cases

- What happens when a prompt mixes both syntaxes, e.g., `[DURATION]` and `{DURATION}` in the same content? Treated as two distinct placeholders (different tokens), each getting its own field, since the two syntaxes are not declared equivalent to each other.
- What happens when brackets/braces appear in the content but don't look like a placeholder (e.g., empty `[]`, unmatched `[abc`, `[point]`, `[YYYY-MM-DD]`, `[P]`, or a code sample containing literal brackets like `array[0]`)? Only well-formed tokens (matching opening/closing pair, name is 2+ characters of uppercase ASCII letters/digits/underscores/spaces) are treated as placeholders; anything else is left as plain text.
- What happens when a placeholder name contains unusual characters (punctuation, numbers, mixed case)? Only names matching `[A-Z0-9_ ]{2,}` are recognized. Mixed case like `[Duration]` or names with hyphens like `[YYYY-MM-DD]` are NOT placeholders.
- What happens when the user copies a prompt with placeholders where the substituted values would make the text extremely long? No special handling — substitution is a straightforward text replacement with no length limit beyond existing prompt content limits.
- What happens when a placeholder value contains characters that look like another placeholder token (e.g., user enters `[NESTED]` as the value for `[DURATION]`)? The value is inserted as literal text and is not itself re-scanned for placeholders (single-pass substitution, no recursive expansion).
- What happens on a prompt with a very large number of distinct placeholders? All distinct placeholders get a field; no cap is imposed by this feature (existing prompt content size limits still apply).

## Clarifications

### Session 2026-07-15

- Q: PromptVault's current UI is a single-page card grid, with each prompt card having an inline Copy button that copies immediately with no intermediate dialog. Where should the placeholder-fill form appear when a prompt has placeholders? → A: Intercept the Copy click — clicking Copy on a card with placeholders opens a modal/inline form first (fill in values, then a second confirming action copies); prompts with no placeholders keep today's instant one-click copy unchanged.
- Q: The version-history modal today only offers "Revert" and "Select for diff" per version, with no copy action tied to viewing an older version's raw text (to copy an old version, a user must revert to it first, then use the regular Copy button). Should the placeholder feature add a new copy-with-placeholders affordance inside version history/diff, or stay out of it? → A: Stay out of it — no placeholder form appears in the version-history or diff view; those remain read-only/text-only as today. To copy an older version with placeholders filled in, the user reverts first (making it current), then uses the regular Copy-click flow from User Story 1/2.
- Q: Since Copy now always opens the placeholder form when a prompt has placeholders, how does a user get raw/unsubstituted output "without touching the form" (User Story 2 scenario 2)? → A: There is no separate bypass action — the form opens with all fields blank, and clicking the same confirm/copy action with nothing entered in any field copies the raw content with every token left unchanged. This is the same single confirm action as the fill-in case, just invoked with empty inputs.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST recognize placeholder tokens in prompt content written in square-bracket syntax (`[NAME]`) and curly-brace syntax (`{NAME}`), where `NAME` consists of 2 or more characters drawn exclusively from uppercase ASCII letters (`A–Z`), digits (`0–9`), underscores (`_`), and spaces (` `).
- **FR-002**: System MUST treat `[NAME]` and `{NAME}` as two distinct placeholder identities even when `NAME` is identical, and MUST treat placeholder matching as case-sensitive and exact-text. Lowercase letters, hyphens, slashes, and other punctuation inside delimiters MUST NOT be recognized as placeholders.
- **FR-003**: System MUST detect all distinct placeholder tokens present in a prompt's current content and present exactly one input field per distinct token when the user clicks Copy on that prompt's card.
- **FR-004**: System MUST NOT display a placeholder form for prompts whose content contains no recognized placeholder tokens; copy behavior for such prompts MUST remain unchanged from current behavior (immediate one-click copy).
- **FR-004a**: System MUST NOT display a placeholder form within the version-history or diff view; those views remain read-only/text-only as today. The placeholder-fill flow applies only to the Copy-click action on a prompt's current content.
- **FR-005**: Users MUST be able to enter a text value for each detected placeholder field.
- **FR-006**: System MUST, when the user triggers copy after filling in the placeholder form, replace every occurrence of each filled placeholder token in the prompt content with its corresponding value, leaving all other content unchanged.
- **FR-007**: System MUST leave any placeholder token with no user-provided value unchanged (as its original bracketed/braced token) in the copied text.
- **FR-008**: Users MUST be able to confirm the placeholder form with every field left blank, producing output identical to the current raw-copy behavior (all tokens unchanged); no separate bypass action is required.
- **FR-009**: System MUST re-derive the set of displayed placeholder fields whenever the underlying prompt content changes (including after edits), rather than caching a stale placeholder list.
- **FR-010**: System MUST store prompt content, including placeholder tokens, as plain unmodified text in prompt versioning/history — no substitution is ever persisted into stored prompt content.
- **FR-011**: System MUST NOT alter how search and filtering match prompt text — placeholder tokens are matched as ordinary substrings like any other prompt content.
- **FR-012**: System MUST NOT alter export output (CSV, Markdown, JSON, or any other supported export format) — exported content MUST contain the original, unsubstituted placeholder tokens.
- **FR-013**: System MUST perform placeholder substitution as a single, non-recursive pass — a user-provided value is inserted as literal text and is not itself scanned for further placeholder tokens.

### Key Entities

- **Placeholder Token**: A bracketed (`[NAME]`) or braced (`{NAME}`) span of text found within a prompt's content, where `NAME` is 2+ characters of uppercase ASCII letters, digits, underscores, or spaces (`[A-Z0-9_ ]{2,}`). Identity is the exact delimiter type plus the exact text between delimiters. Not persisted as a separate record — always derived on the fly from the prompt's current content.
- **Placeholder Value Set**: The transient, per-use collection of user-entered values keyed by placeholder token, scoped to a single viewing/copy session for a prompt. Not persisted with the prompt or its version history.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Users can go from clicking Copy on a prompt with placeholders to copying a fully filled-in version in under 30 seconds for a prompt with up to 5 distinct placeholders.
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
