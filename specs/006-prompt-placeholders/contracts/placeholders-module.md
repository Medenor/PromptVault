# Contract: `utils/placeholders.ts` module interface

This feature has no network/API contract (no backend involved). The "contract" below is the public TypeScript interface that `app.ts` call sites depend on, kept stable so unit tests and call sites can be written against it independently.

## `detectPlaceholders(content: string): PlaceholderToken[]`

- **Input**: raw prompt content string (may be empty, may contain zero, one, or many placeholder-like spans).
- **Output**: array of `PlaceholderToken` (see data-model.md), one per **distinct** `raw` value, in first-seen order. Empty array if none found.
- **Guarantees**:
  - Never throws — malformed/unmatched brackets (e.g. `"array[0]"`, `"[unterminated"`, `"[]"`) and non-conforming names (lowercase, too short, containing hyphens/slashes/punctuation) are simply not included in the result.
  - Only names matching `[A-Z0-9_ ]{2,}` (2+ uppercase ASCII letters, digits, underscores, or spaces) are recognized as placeholders.
  - Pure function: does not mutate `content`, no side effects.

## `substitutePlaceholders(content: string, values: Map<string, string>): string`

- **Input**: raw prompt content string, plus a map of `PlaceholderToken.raw` → user-provided value (only filled placeholders present as keys).
- **Output**: new string with every occurrence of each key in `values` replaced by its corresponding value; any placeholder-looking span not present as a key in `values` is left byte-for-byte unchanged.
- **Guarantees**:
  - Single pass — a substituted value is never re-scanned for further placeholder tokens (FR-013), even if it contains bracket/brace-like text.
  - Pure function: does not mutate `content` or `values`, no side effects, no network/DOM access.

## Call-site contract: `app.ts`

`copyPrompt(id)` and `copyPromptWithVersion(id)` change from "fetch content → write to clipboard" to:

1. Fetch/obtain content exactly as today (no change to fetch logic or `promptCache` semantics).
2. Call `detectPlaceholders(content)`.
3. If the result is empty → copy `content` unchanged, exactly as today (FR-004).
4. If non-empty → open a `createModal`-based form with one input per token; on confirm, call `substitutePlaceholders(content, filledValuesMap)` and copy the result; on cancel, abort the copy entirely (no clipboard write).

This preserves the existing function signatures (`(id: PromptId): Promise<void>`) so no other call sites need to change.
