# Research: Dynamic Prompt Placeholders

No open `NEEDS CLARIFICATION` markers remain from the spec — all ambiguities were resolved with documented defaults in the spec's Assumptions section. This document records the technical decisions made to satisfy those defaults.

## Decision: Placeholder detection via regex, not a parser

**Decision**: Use two regular expressions — one for `\[([^\[\]\n]+)\]` and one for `\{([^{}\n]+)\}` — scanned against the prompt content string to extract distinct tokens, preserving first-seen order for stable field ordering.

**Rationale**: Per FR-001/FR-002 and the Edge Cases section, placeholders are simple non-nested, single-line bracket/brace spans. A regex satisfies this exactly without the complexity of a real parser, and matches the "no nested brackets" and "no internal newline" rules by construction (the character classes exclude the delimiters and `\n`).

**Alternatives considered**:

- A hand-written character-by-character scanner — rejected as unnecessary complexity for a non-nested, single-line grammar that a character class already expresses.
- Treating `[` and `{` as interchangeable (normalizing to one internal representation) — rejected because FR-002 explicitly requires the two syntaxes to be distinct identities.

## Decision: Distinct identity = delimiter type + exact inner text

**Decision**: A placeholder's identity/key is the tuple (delimiter kind, exact inner string), compared case-sensitively with no trimming or normalization.

**Rationale**: FR-002 requires case-sensitive, exact-text, syntax-distinct matching. Using the raw matched substring (including delimiters, e.g. `"[DURATION]"` and `"{DURATION}"` as separate keys) as a map key is the simplest correct implementation — no separate normalization step needed.

**Alternatives considered**: Case-insensitive matching or trimming whitespace inside delimiters — rejected, not requested by spec and would silently merge fields a user wrote as visually distinct.

## Decision: Substitution is a single non-recursive string-replace pass over the token map

**Decision**: Build a `Map<token, value>` from filled form fields only (unfilled fields are simply absent from the map), then do one pass replacing every literal occurrence of each present token with its value; anything not in the map (unfilled tokens) is left as-is since it was never a candidate for replacement.

**Rationale**: Satisfies FR-006/FR-007/FR-013 directly — a single linear scan replacing exact substrings can't recursively expand a value that happens to contain another token, and omission from the map is naturally "leave unchanged."

**Alternatives considered**: Recursive/iterative expansion until no tokens remain — explicitly rejected by FR-013 and the Edge Cases section (a value containing `[NESTED]` must not be re-expanded).

## Decision: UI surface reuses the existing `createModal` component

**Decision**: When placeholders are detected, open a `createModal` instance (the same helper already used for the keyboard-shortcuts-help modal in `app.ts`) containing one labeled text input per distinct token, with "Copy" and "Cancel" actions; if no placeholders are detected, skip the modal and copy immediately (unchanged current behavior).

**Rationale**: Reuses an existing, already-accessible (ARIA-labeled, focus-managed, Escape/backdrop-closeable) component rather than building a new one, consistent with the Anti-Abstraction principle and this repo's existing conventions.

**Alternatives considered**: A custom inline expandable panel next to the prompt card — rejected as a new UI pattern with no accessibility scaffolding already in place, when a suitable modal helper already exists.

## Decision: "Copy without opening the form" stays a first-class supported path

**Decision**: The modal's own "Cancel" affordance (and simply not invoking the placeholder flow when there are zero detected tokens) is how User Story 2's "copy without touching the form" scenario is satisfied — but note the spec's acceptance scenario 2 for Story 2 describes copying _without opening the form at all_. Given the existing single "Copy" button is the only copy entry point today, the modal is shown automatically whenever placeholders are detected (this is the auto-detect behavior FR-003 requires); a user who wants the raw untouched text can leave all fields blank and confirm, which — per FR-007 — leaves every token unchanged, producing output identical to today's raw copy.

**Rationale**: This reconciles FR-003 (auto-show the form when placeholders exist) with User Story 2 (must still be able to get the raw text) without adding a second copy button: leaving fields blank and confirming is functionally equivalent to bypassing the form.

**Alternatives considered**: Adding a separate "Copy raw" button alongside "Copy" — rejected as unnecessary UI surface; leaving fields blank achieves the same outcome per FR-007.
