# Data Model: Dynamic Prompt Placeholders

No new persisted entities or schema changes. Both entities below are transient, in-memory, client-side values derived at use-time — nothing here is written to the database, prompt version history, cache serialization, or export output.

## PlaceholderToken

Represents one distinct placeholder found in a prompt's current content.

| Field       | Type                    | Notes                                                                 |
| ----------- | ----------------------- | ---------------------------------------------------------------------- |
| `raw`       | `string`                 | The full matched text including delimiters, e.g. `"[DURATION]"`. Used as the map key / field identity (FR-002). |
| `delimiter` | `'bracket' \| 'brace'`   | Which syntax it was written in — informational, since `raw` already disambiguates identity. |
| `label`     | `string`                 | Text to show on the form field — the inner text between delimiters, e.g. `"DURATION"`. |

**Derivation**: Computed fresh from `prompt.content` (or `prompt.prompt`, matching the existing field name used by `copyPrompt`) every time the copy flow runs — never cached across edits (FR-009), never persisted (per spec Key Entities: "Not persisted as a separate record").

**Validation rules**: A candidate span qualifies only if non-empty, contains no `\n`, and contains no nested occurrence of its own delimiter type (see research.md regex decision). No other validation (no charset restriction on the inner text).

## PlaceholderValueSet

The transient collection of values a user types into the modal form during one copy interaction.

| Field    | Type                     | Notes                                                                                       |
| -------- | ------------------------ | --------------------------------------------------------------------------------------------- |
| `values` | `Map<string, string>`    | Keyed by `PlaceholderToken.raw`. Only tokens the user actually filled in appear as keys (FR-007 relies on "absent from map" meaning "leave unchanged"). |

**Lifecycle**: Created when the modal opens, discarded when the modal closes (on cancel) or immediately after the copy action completes. Never persisted, never sent to the backend, never attached to `promptCache` (per spec Assumptions: no cross-session persistence of last-used values).

## Relationships

```
Prompt (existing entity, unchanged)
  └─ content: string  ──scan──▶  PlaceholderToken[] (derived, not stored)
                                       │
                                 user fills in
                                       ▼
                              PlaceholderValueSet (transient)
                                       │
                              substitute into content
                                       ▼
                         copiedText: string (never written back to Prompt)
```
