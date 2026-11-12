# Feature Specification: Skill Packages

**Feature Branch**: `011-skill-packages`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User description: "Add Skills as a second, distinct content type in PromptVault: multi-file packages (a `SKILL.md` entry point with frontmatter plus optional scripts, templates, references and assets), imported and exported as `.zip`, stored alongside prompts. First cut: item-type discriminator with prompts unaffected, basic skill CRUD by zip upload, file-tree browsing, zip download. Sharing and versioning of skills are out of scope; executing bundled scripts is a non-goal."

## Context

Today every item in the vault is a prompt: one block of text plus metadata (title, category, tags, note, favorite). Agent tools such as Claude Code, Codex CLI, Gemini CLI and GitHub Copilot now share an open "skill" format. A skill is a folder rather than a single text. It has a `SKILL.md` file (frontmatter with a name and a description, then Markdown instructions) and can bundle helper scripts, reference documents, templates and assets. People pass skills around as `.zip` archives. The format is defined by the open Agent Skills specification (agentskills.io/specification). Its rules include: the archive holds the skill folder as its top-level entry; the folder name equals the `name` field in `SKILL.md`; `name` uses only lowercase letters, digits and hyphens, up to 64 characters; and `description` is at most 1,024 characters.

This feature lets users keep skills in the same vault as their prompts. They upload a skill as a zip, browse its files, organize it with the existing categories and tags, and download it again as a zip. PromptVault only stores skills. It never runs anything bundled inside them.

## Clarifications

### Session 2026-11-12

- Q: When users search the vault, should a skill also match on the text of its `SKILL.md` instructions, or only on its title and description? → A: Title, description and the full `SKILL.md` instructions. Other bundled files are not searched.
- Q: When a user replaces a skill's files with a new zip whose `name` has changed, should the skill's title stay as it is, or follow the new name? → A: Always keep the current title. Only the skill identifier and the description follow the new `SKILL.md`.
- Q: How should the existing bulk prompt import/export treat skills, including its "Replace" mode that clears all existing prompts first? → A: Bulk import/export ignores skills. Exports contain prompts only and Replace clears prompts only, never skills. The bulk export screen tells users that skills are exported one at a time.
- Q: Should importing, replacing and deleting skills, and rejected uploads with their reason, be written to the application's audit log? → A: Yes. Log import, replace and delete, and rejected uploads with the reason. Record user, skill identifier, file count and size, never file contents. Views and downloads are not logged.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import a skill from a zip archive (Priority: P1)

A user has a skill folder they built for an agent tool, zipped as `pdf-tools.zip`. In PromptVault they choose "Import skill", select the archive and confirm. The vault checks the archive and reads the name and description from `SKILL.md`. It then creates a new skill item, and that skill appears in the vault list with a clear "Skill" marker.

**Why this priority**: Nothing else in the feature works without a way to get skills into the vault. Upload is also the only way to create a skill in this first cut.

**Independent Test**: Upload a valid skill zip and confirm that a skill item appears with the name and description taken from its `SKILL.md`, while existing prompts stay unchanged. This proves the vault can hold the new content type.

**Acceptance Scenarios**:

1. **Given** a zip whose root contains `SKILL.md` with `name` and `description` in its frontmatter, **When** the user imports it, **Then** a skill item is created whose title and description match the frontmatter values, and every file in the archive is stored with its relative path.
2. **Given** a zip in the standard layout, whose only top-level entry is a single folder containing `SKILL.md` (for example `my-skill/SKILL.md`), **When** the user imports it, **Then** the vault treats that folder as the skill root, and stored paths do not include the wrapping folder name.
3. **Given** a zip with no `SKILL.md` at the root or inside a single wrapping folder, **When** the user imports it, **Then** the import is rejected with a message saying that `SKILL.md` is missing, and nothing is stored.
4. **Given** a `SKILL.md` that breaks the standard format (frontmatter missing, `name` or `description` missing, `name` not lowercase-hyphenated or over 64 characters, `name` different from the wrapping folder name, or `description` over 1,024 characters), **When** the user imports it, **Then** the skill is created anyway, the title falls back to the archive file name if `name` is missing, and the user sees a warning that lists each rule that was broken.
5. **Given** a successful import, **When** the user opens the vault list, **Then** the new skill appears next to prompts and is visually identified as a skill.

---

### User Story 2 - Browse and read a stored skill (Priority: P1)

The user opens a skill from the vault list. The detail view shows the skill's metadata and its instructions (`SKILL.md` rendered as readable Markdown), along with a file tree of every bundled file. Selecting a text file shows its contents. Selecting a binary file shows its name and size, with a download link.

**Why this priority**: A stored skill is only useful if the user can see what it contains. Together with Story 1, this makes the smallest useful version of the feature.

**Independent Test**: Import a skill that has nested folders, a script, a Markdown reference and an image. Open it, expand the tree, view each text file and confirm the image is listed but not shown as text.

**Acceptance Scenarios**:

1. **Given** a stored skill, **When** the user opens it, **Then** they see the title, description, category, tags, note, total size, file count, and the rendered `SKILL.md` instructions.
2. **Given** a stored skill with nested folders, **When** the user opens the file tree, **Then** folders and files appear in their original hierarchy, sorted with folders first and then alphabetically.
3. **Given** a text file in the tree (for example `.md`, `.py`, `.sh`, `.json`, `.txt`), **When** the user selects it, **Then** its contents are shown as plain, read-only text. Bundled content is never run or rendered as active content.
4. **Given** a binary file in the tree, **When** the user selects it, **Then** its name, size and a download option are shown in place of its contents.

---

### User Story 3 - Download a skill as a zip (Priority: P2)

From the skill detail view, the user selects "Download". They receive a `.zip` that rebuilds the skill folder, with `SKILL.md` and every bundled file at its original relative path. They can drop it straight into another agent tool's skills directory.

**Why this priority**: Export is what makes the vault a real source of truth instead of a dead end. It comes after import and browsing because a user can still copy individual files without it.

**Independent Test**: Import a skill, download it, and compare the downloaded archive with the original. The file paths and file contents must match exactly.

**Acceptance Scenarios**:

1. **Given** a stored skill, **When** the user downloads it, **Then** they receive `<skill-id>.zip`, containing one top-level folder `<skill-id>/` with every stored file at its original relative path and with identical contents. Here `<skill-id>` is the skill identifier (FR-012a), not its editable title.
2. **Given** a skill whose title the user changed after import, **When** they download it, **Then** the folder and archive names still match the `name` in `SKILL.md`, so the archive can still be uploaded to agent tools that require the two to match.
3. **Given** a skill imported and then downloaded with no changes in between, **When** the downloaded zip is imported again, **Then** the import succeeds and produces an equivalent skill.

---

### User Story 4 - Organize, edit, replace and delete skills (Priority: P2)

The user manages skills the way they manage prompts. They assign a category and tags, add a personal note, mark favorites, and find skills through the vault's existing search and filters. They can filter the list to show only prompts or only skills. To update a skill's files, they upload a new zip that replaces the stored contents. They can also delete a skill.

**Why this priority**: Once a vault holds more than a handful of skills, organization matters. It reuses existing features, so it adds little new risk.

**Independent Test**: Tag and categorize an imported skill, filter the list by type, search for it by name, replace its contents with a new zip, and then delete it.

**Acceptance Scenarios**:

1. **Given** a stored skill, **When** the user edits its title, category, tags, note or favorite flag, **Then** the changes are saved and show up in the list and the detail view.
2. **Given** a vault holding both prompts and skills, **When** the user filters by type "Skill", **Then** only skills are listed. Filtering by "Prompt" lists only prompts, and the default view lists both.
3. **Given** a skill whose title, description or `SKILL.md` instructions contain a search term, **When** the user searches for that term, **Then** the skill appears in the results with its skill marker. A term that appears only in another bundled file does not match.
4. **Given** a stored skill, **When** the user uploads a replacement zip that passes validation, **Then** the stored files are replaced in full, the title and the user-edited metadata (category, tags, note, favorite) are kept, and the description and skill identifier are refreshed from the new `SKILL.md`, even when its `name` differs from the current title.
5. **Given** a replacement zip that fails validation, **When** the user uploads it, **Then** the existing skill stays exactly as it was.
6. **Given** a stored skill, **When** the user deletes it and confirms, **Then** the item and all of its files are removed and no longer appear anywhere in the vault.

---

### User Story 5 - Skills survive backup and restore (Priority: P2)

An administrator runs the existing backup feature. The backup includes every skill's metadata and files. Restoring that backup on a fresh instance brings back every skill with byte-identical files.

**Why this priority**: A vault that loses skills on restore cannot be trusted. Backup coverage has to ship in the same release as storage.

**Independent Test**: Import several skills, take a backup, restore it into an empty instance, and download each skill to compare it with the original.

**Acceptance Scenarios**:

1. **Given** a vault with skills, **When** a backup is created, **Then** the backup holds all skill metadata and all skill files.
2. **Given** that backup, **When** it is restored into an empty instance, **Then** every skill is present, and downloading each one gives files identical to the originals.
3. **Given** backups taken before this feature existed, **When** one is restored, **Then** the restore succeeds and every item comes back as a prompt.

---

### Edge Cases

- **Path traversal**: An archive entry whose path is absolute or contains `..` segments that point outside the skill root causes the whole import to be rejected. Nothing is written outside the skill's storage area.
- **Links**: An archive containing symbolic links is rejected. Hard links cannot be represented in a zip archive; they become ordinary files when the archive is created.
- **Oversized or bomb-like archives**: An archive larger than the upload limit, whose total uncompressed size is over the expansion limit, with more files than the file-count limit, or with a suspicious compression ratio is rejected before its contents are written.
- **Corrupt or non-zip files**: A file that is not a valid zip archive, or is a password-protected one, is rejected with a clear message.
- **Several `SKILL.md` files**: If several `SKILL.md` files exist, only the one at the skill root counts as the entry point. Others are stored as ordinary bundled files.
- **Unusual file names**: Duplicate paths, paths that differ only in letter case, and names with characters that are invalid on common operating systems are rejected with a message naming the offending entry.
- **OS clutter**: Typical system junk entries (for example `__MACOSX/` and `.DS_Store`) are skipped silently and are not stored.
- **Empty folders**: Empty folders in the archive are not kept.
- **Name collisions**: Importing a skill whose name matches an existing item creates a separate item. Names do not have to be unique, as with prompts today.
- **Interrupted import**: If an import fails or is interrupted partway through, no partial skill is left behind, either as a visible item or as orphaned files.
- **Large text files**: A text file too large to show in the viewer is shown truncated, with a notice and a download option.
- **Bulk prompt import in Replace mode**: When a vault holds skills and the user runs a bulk prompt import in "Replace" mode, every existing prompt is cleared and every skill stays untouched.
- **Prompt-only actions**: Placeholder filling, version history and sharing do not apply to skills. Those actions are hidden or disabled on skill items rather than failing.

## Requirements *(mandatory)*

### Functional Requirements

**Content type**

- **FR-001**: Every vault item MUST have a type, either "prompt" or "skill". Existing items MUST be treated as prompts without any change to their content or behavior.
- **FR-002**: The vault list, search results and detail views MUST show each item's type clearly, and users MUST be able to filter the list by type (all, prompts only, skills only).
- **FR-003**: Prompt-only capabilities (placeholders, version history, branches, sharing) MUST NOT be offered on skill items.

**Import and validation**

- **FR-004**: Users MUST be able to create a skill by uploading a `.zip` archive. In this release, zip upload is the only way to create a skill.
- **FR-005**: The system MUST find the skill root: either the archive root, or the single top-level folder when the archive contains exactly one. The skill root MUST contain a file named `SKILL.md`. Otherwise the upload MUST be rejected.
- **FR-006**: The system MUST read `name` and `description` from the `SKILL.md` frontmatter and use them as the skill's initial title and description. The system MUST check the frontmatter against the Agent Skills format rules: `name` and `description` are present; `name` uses only lowercase letters, digits and hyphens, up to 64 characters; `name` equals the wrapping folder name when there is one; `description` is at most 1,024 characters. A skill that breaks any of these rules, or has missing or malformed frontmatter, MUST still be accepted. The title falls back to the archive file name if `name` is missing, and the user sees a non-blocking warning that lists each rule broken.
- **FR-007**: The system MUST reject, without storing anything, any archive that contains: entries resolving outside the skill root; absolute paths; symbolic links (hard links cannot be represented in a zip archive, so they need no separate check); duplicate paths, including paths that differ only by letter case; or entries with names that are invalid on common operating systems.
- **FR-008**: The system MUST enforce configurable limits on compressed upload size, total uncompressed size, number of files, folder nesting depth and size of any single file, with defaults of 10 MB, 50 MB, 500 files, 10 levels and 10 MB. `SKILL.md` itself has a separate configurable limit, 1 MB by default. It MUST check these limits before or during extraction, so that a malicious archive never uses more than the configured allowance.
- **FR-009**: The system MUST skip common operating-system clutter entries (`__MACOSX/`, `.DS_Store`, `Thumbs.db`) and MUST NOT store empty folders.
- **FR-010**: Import MUST be all-or-nothing. A failed or interrupted import MUST leave no item and no stored files behind.
- **FR-011**: Every rejection MUST give the user a specific reason (for example "SKILL.md not found", "archive exceeds 50 MB uncompressed", or "entry `../x` escapes the skill folder").

**Storage**

- **FR-012**: The system MUST store every accepted file of a skill with its relative path and exact contents, so that a later export reproduces the original files byte for byte.
- **FR-012a**: Each skill MUST have a skill identifier, kept separate from its editable title. The identifier is the frontmatter `name` when it follows the format rules. Otherwise it is a lowercase-hyphenated slug of up to 64 characters, derived from `name` or the archive file name. The identifier is refreshed whenever the files are replaced, and it is what export uses for naming.
- **FR-012b**: The system MUST store `SKILL.md` exactly as uploaded, including frontmatter fields it does not interpret (for example `license`, `allowed-tools`, `metadata`) and tool-specific placeholders in the instructions (for example `${CLAUDE_SKILL_DIR}`). These placeholders MUST NOT be treated as PromptVault prompt placeholders.
- **FR-013**: The system MUST record, for each skill, its total size and its file count, and show both in the detail view.
- **FR-014**: Skill files MUST be readable only through the same access rules that apply to the owning item. One user's skill files MUST NOT be reachable by another user.

**Browsing**

- **FR-015**: The skill detail view MUST show the skill's metadata, render the `SKILL.md` instructions as formatted Markdown, and present every bundled file in a tree that mirrors its folder structure.
- **FR-016**: Selecting a text file MUST show its contents as read-only plain text. Selecting a binary file MUST show its name and size with a download option. Text files over 1 MB MUST be shown truncated, with a notice.
- **FR-017**: Bundled content MUST never be executed, interpreted or rendered as active content (no scripts, no embedded HTML behavior). Rendered `SKILL.md` Markdown MUST be sanitized.
- **FR-018**: Users MUST be able to download any single bundled file.

**Export**

- **FR-019**: Users MUST be able to download a skill as `<skill-id>.zip`. The archive MUST contain exactly one top-level folder `<skill-id>/`, holding every stored file at its original relative path. This matches the layout agent tools expect on upload, where `SKILL.md` directly at the archive root is not recognized.
- **FR-020**: The export archive MUST be built from the stored files each time it is requested. The system MUST NOT keep a separate stored copy of the archive.

**Management**

- **FR-021**: Users MUST be able to edit a skill's title, category, tags, note and favorite flag through the same controls used for prompts.
- **FR-022**: Users MUST be able to replace a skill's files by uploading a new zip. The replacement MUST pass the same validation as an import (FR-005 to FR-011). It MUST swap the files completely or not at all, MUST keep the current title and the user-edited metadata (category, tags, note, favorite) unchanged, and MUST refresh the description and the skill identifier from the new `SKILL.md`. The title is set from `SKILL.md` only on the first import.
- **FR-023**: Users MUST be able to delete a skill after a confirmation step that states deletion is permanent and cannot be undone. Deleting a skill MUST remove all of its stored files.
- **FR-024**: Skills MUST be findable by the existing vault search through their title, description and full `SKILL.md` instructions. Replacing a skill's files MUST update what search finds for it. Searching the contents of other bundled files is out of scope for this release.

- **FR-024a**: The existing bulk prompt import/export MUST ignore skills. Bulk exports MUST contain prompts only. Bulk imports in every mode, including "Replace", MUST create, merge or clear prompts only and MUST NOT change or delete any skill. The bulk export screen MUST tell users that skills are not included and are exported one at a time from each skill's detail view.

**Authorization**

- **FR-025**: Importing, editing, replacing and deleting skills MUST follow the same authentication and ownership rules as the matching prompt actions. When authentication is enabled, only the owner can see or change a skill, except administrators, who can see and delete every skill, as they can every prompt. Other non-owners get a "not found" response, so they cannot tell that the skill exists. When authentication is disabled, the endpoints that import, replace and delete skills MUST be protected by the same configuration-level guard as the matching prompt endpoints (Constitution III).

**Audit**

- **FR-025a**: The system MUST write an audit event for every successful skill import, replacement and deletion. Each event MUST record the acting user, the skill identifier, the file count and the total size.
- **FR-025b**: The system MUST write an audit event for every rejected upload (import or replacement). The event MUST record the acting user, the archive file name and the specific rejection reason from FR-011.
- **FR-025c**: Audit events MUST NOT contain file contents or the list of bundled file names, except the single offending entry named in a rejection reason. Viewing and downloading skills or files are not audited.

**Backup and restore**

- **FR-026**: Backups MUST include all skill metadata and skill files. Restoring a backup MUST bring back every skill with byte-identical files.
- **FR-027**: Backups created before this feature MUST remain restorable, and all of their items MUST come back as prompts.

### Key Entities

- **Vault item**: Anything the vault stores, now with a type of either prompt or skill. It keeps the shared metadata used today: title, category, tags, note, favorite flag, owner, and created and updated timestamps.
- **Skill**: A vault item of type skill. Beyond the shared metadata, it has a skill identifier (the format-compliant name used for export), a description (from the `SKILL.md` frontmatter), the instructions body (the `SKILL.md` content), a total size, a file count, and the list of format warnings recorded at import (empty when the skill fully follows the standard format).
- **Skill file**: One file inside a skill. It has a relative path inside the skill root, a size, a text-or-binary classification, and its exact contents. Each file belongs to exactly one skill, and paths are unique within a skill.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can import a typical skill (under 1 MB, under 20 files) and see it in their vault in under 30 seconds from opening the import dialog.
- **SC-002**: For 100% of accepted skills, a download followed by a byte-for-byte comparison with the original files shows no difference in paths or contents.
- **SC-003**: 100% of archives in a malicious-archive test set are rejected with nothing written: path traversal, absolute paths, symbolic links, zip bombs, over-limit file counts and corrupt files.
- **SC-004**: Every skill in Anthropic's public example collection (the `anthropics/skills` repository) imports without errors, and at least 95% of them import without format warnings.
- **SC-008**: For any imported skill with no format warnings, the downloaded archive passes the reference Agent Skills validator unchanged and keeps the layout agent tools accept for upload.
- **SC-005**: After the feature ships, every existing prompt behaves exactly as before. The full existing prompt test suite passes unchanged.
- **SC-006**: A backup taken from a vault holding skills, restored into an empty instance, brings back 100% of skills with identical files.
- **SC-007**: A skill detail view with up to 500 files opens and shows its file tree in under 2 seconds.

## Assumptions

- **Single-user ownership in v1**: Skills belong to the user who imported them. Sharing skills with other users is out of scope and will be a separate follow-up feature once prompt sharing (007) is stable.
- **No versioning in v1**: Replacing a skill's contents overwrites the previous files. Keeping a version history of skills is a follow-up feature.
- **Deletion cannot be undone in v1**: Unlike prompts, a deleted skill cannot be restored with the undo action. Because of this, the confirmation step in FR-023 is mandatory, and the confirmation message says that deletion is permanent. Backups remain the way to recover a deleted skill.
- **`SKILL.md` size**: The instructions file is not held to the prompt text limit (50,000 characters). It is capped at 1 MB, so that search indexing and rendering stay fast. Other bundled files follow the general per-file limit.
- **Zip upload only**: Creating a skill from scratch or editing its files in the browser is out of scope. Users edit skills in their own tools and upload them again.
- **Lenient validation**: The only hard requirement is a `SKILL.md` at the skill root. A root-level `SKILL.md` with no wrapping folder is accepted on import even though the standard requires the folder, and export always produces the standard layout. Frontmatter problems produce warnings rather than rejections, so that "skill-like" packages from other tools can still be stored. Strict conformance checks and tool-specific import adapters are out of scope.
- **Storage only, never a runtime**: PromptVault never runs, interprets or installs bundled scripts or assets.
- **Default limits**: The default limits in FR-008 cover typical skills. Self-hosting administrators can change them through configuration.
- **Text detection**: A file counts as text when its contents are valid UTF-8 with no null bytes. Every other file counts as binary.
- **Storage location is a planning decision**: Where skill file contents are kept is left to planning. The constitution (Principle V) says new features must keep data in the database rather than in ad-hoc files, so storing skill file contents in the database is the expected default. Any other approach needs an explicit justification and a constitution check during planning, and must still meet FR-010, FR-014 and FR-026.
- **Existing features reused**: Categories, tags, search, favorites, authentication and backup/restore are extended rather than duplicated.
- **Interface languages**: All new interface text is provided in every language the interface already supports.
