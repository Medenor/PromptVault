# Feature Specification: Prompt Sharing & Team Collaboration

**Feature Branch**: `007-prompt-sharing`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "Per-prompt sharing grants between users with read/edit permission levels, 'shared with me' listing, and share badges — the middle ground between 'own' and 'admin-sees-all' that RBAC currently lacks. Improvement Plan 2026-08 item #4; carried from ROADMAP 2026 item #1 (Codeberg issues #23, #17)."

## Clarifications

### Session 2026-08-04

- Q: What does "edit" permission cover on prompt metadata (category, tags, favorite)? → A: "Edit" covers content, category, and tags; the favorite flag stays owner-only.
- Q: Does a recipient get notified when a prompt is shared with them? → A: No notification in v1 — recipients discover shares via the "shared with me" filter and badges.
- Q: What happens to shares when a user account is deleted? → A: Sharing rides along with existing deletion behavior. Soft delete (deactivation) changes no data; the deactivated user simply can't use their access. Hard delete removes grants naming the deleted user as grantee; their owned prompts become orphans (existing behavior) and grants they issued survive on those orphans, revocable by admins.
- Q: Who can see the user directory via the share typeahead? → A: Any authenticated user can typeahead-search the full user directory (usernames only, active accounts) when sharing.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Share a prompt with a teammate (Priority: P1)

A prompt owner wants a specific teammate to see (or help maintain) one of their prompts without making that teammate an admin and without giving up ownership. The owner opens the prompt's sharing controls, picks the teammate by name or email, chooses a permission level (read or edit), and confirms. The teammate can now access that prompt according to the granted level; nobody else's access changes.

**Why this priority**: This is the core capability the feature exists for — without granting access, none of the other stories (viewing shared prompts, badges, revocation) have anything to operate on. It closes the biggest gap between the product's "team deployment" positioning and its current owner-or-admin-only access model.

**Independent Test**: Can be fully tested by creating two user accounts, sharing a prompt from user A to user B with each permission level, and verifying user B's resulting access (and that a third user C still has none).

**Acceptance Scenarios**:

1. **Given** a prompt owned by user A and a second user B with no access to it, **When** A grants B "read" access, **Then** B can view the prompt and its version history but cannot modify, delete, or re-share it.
2. **Given** a prompt owned by user A, **When** A grants B "edit" access, **Then** B can view and modify the prompt (creating new versions attributed to B) and revert it to earlier versions, but cannot delete it, re-share it, or change its ownership.
3. **Given** user A is granting a share, **When** A selects the recipient, **Then** A can find the recipient by typing a partial username or email and choosing from matching suggestions.
4. **Given** a prompt already shared with B at "read", **When** A grants B "edit" on the same prompt, **Then** B's existing grant is updated to "edit" rather than a duplicate grant being created.
5. **Given** user A attempts to share a prompt with a recipient identifier that matches no account, **When** the request is submitted, **Then** A receives a generic failure message that does not confirm whether any account exists for that identifier.
6. **Given** a user who is neither the prompt's owner nor an admin, **When** they attempt to grant or revoke shares on that prompt, **Then** the operation is refused.

---

### User Story 2 - Find and work with prompts shared with me (Priority: P2)

A recipient of shares wants to find the prompts colleagues have shared with them, alongside but distinguishable from their own prompts. They can filter their prompt list to "shared with me", see a visible "Shared" indicator on prompts they don't own, and open and use those prompts within their granted permission level. Search and existing filters work across owned and shared prompts together.

**Why this priority**: Grants are useless if recipients can't discover what was shared with them. This story turns the P1 access grant into a usable day-to-day collaboration workflow.

**Independent Test**: With shares already in place (from story 1 or fixtures), log in as the recipient and verify listing, filtering, badges, and search behavior without touching the granting flow.

**Acceptance Scenarios**:

1. **Given** user B has been granted access to some of A's prompts, **When** B views their prompt list, **Then** it contains B's own prompts plus the prompts shared with B, each shared prompt carrying a visible "Shared" indicator, with no duplicates.
2. **Given** B's prompt list contains owned and shared prompts, **When** B applies the "shared with me" filter, **Then** only prompts shared with B are listed.
3. **Given** B searches or filters their prompts (by text, category, or tag), **When** results are returned, **Then** matching shared prompts appear alongside matching owned prompts, and pagination remains correct; the favorites filter is the exception — it returns only B's own prompts, since the favorite flag is the owner's personal preference (see Edge Cases).
4. **Given** a prompt shared with B at "read", **When** B attempts to edit it, **Then** the modification is refused and the interface does not present editing actions as available.
5. **Given** a prompt was shared with B and the grant is later revoked, **When** B next lists or attempts to open that prompt, **Then** it no longer appears in B's listing and direct access is refused.

---

### User Story 3 - Review and revoke access (Priority: P3)

A prompt owner wants to see who currently has access to each of their prompts and take access away when it is no longer appropriate. From the prompt's sharing controls, the owner sees the current list of grantees with their permission levels and can revoke any grant. Every grant and revocation is recorded for audit purposes.

**Why this priority**: Necessary for responsible long-term use (offboarding, mistakes, changing teams), but the feature already delivers collaboration value with stories 1–2 alone.

**Independent Test**: With existing grants, open the sharing controls as the owner, verify the grant list matches reality, revoke one grant, and confirm the recipient's access ends and an audit record exists.

**Acceptance Scenarios**:

1. **Given** a prompt with several grants, **When** the owner opens its sharing controls, **Then** all current grantees and their permission levels are listed.
2. **Given** a listed grant, **When** the owner revokes it, **Then** the grantee immediately loses access and disappears from the grant list.
3. **Given** any grant or revocation occurs, **When** the action completes, **Then** an audit record is produced capturing who acted, who the grantee was, the permission level, and which prompt was affected.
4. **Given** a user with a share on a prompt (read or edit), **When** they attempt to view that prompt's full grant list, **Then** the request is refused — only the owner and admins can enumerate grants.

---

### Edge Cases

- Sharing a prompt with yourself: refused with a clear message.
- Sharing with the same user twice: treated as a permission-level update, never a duplicate grant (scenario 1.4).
- Deleting a prompt that has active grants: all its grants are removed with it; recipients simply no longer see it.
- Deactivating a user account (soft delete): no share data changes; the deactivated user cannot log in, so their grants confer nothing in practice, and access they granted to others remains intact.
- Hard-deleting a user account: grants naming them as grantee are removed; their owned prompts become ownerless per existing behavior, and grants they issued survive on those prompts (admins can revoke them).
- Favorites filter on a combined list: the favorite flag is the owner's personal preference, so the favorites filter matches owned prompts only — shared prompts never appear in a recipient's favorites view (per-user favorites are a possible future enhancement).
- Admin users: retain their existing full visibility and control; sharing neither expands nor restricts admin capability.
- A grantee attempting privileged actions (delete, re-share, transfer ownership) at either permission level: refused.
- Rapid repeated share/revoke requests: throttled like other sensitive account operations to prevent abuse and enumeration.
- Concurrent edits by owner and an edit-grantee: both produce versions in the prompt's single version history, attributed to their respective authors, consistent with existing versioning behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Prompt owners MUST be able to grant another user access to a specific prompt at one of exactly two permission levels: "read" or "edit".
- **FR-002**: Admins MUST be able to manage (grant, revoke, view) shares on any prompt; all other non-owner users MUST NOT be able to manage shares.
- **FR-003**: At most one grant MUST exist per (prompt, grantee) pair; granting again for the same pair MUST update the permission level of the existing grant.
- **FR-004**: A "read" grant MUST allow viewing the prompt and its version history, and MUST NOT allow any modification.
- **FR-005**: An "edit" grant MUST additionally allow modifying the prompt's content (title, text, note), category, and tags (creating versions) and reverting it to earlier versions.
- **FR-006**: No grant level MUST allow the grantee to delete the prompt, share it onward, change its ownership, toggle its favorite flag, or view its full grant list; the favorite flag remains controllable only by the owner (and admins).
- **FR-007**: Owners (and admins) MUST be able to view the current grant list for a prompt and revoke any grant; revocation MUST take effect immediately.
- **FR-008**: Recipients MUST see prompts shared with them in their prompt listing alongside their own, deduplicated, with existing search, filtering, and pagination behavior preserved across the combined set — except the favorites filter, which matches owned prompts only (the favorite flag is the owner's personal preference).
- **FR-009**: Recipients MUST be able to filter their listing to only prompts shared with them, and shared prompts MUST carry a visible "Shared" indicator wherever prompts are displayed.
- **FR-010**: Share recipients MUST be selectable by username or email, with typeahead suggestions available to any authenticated user; suggestions MUST expose usernames only and MUST cover active accounts only. Failed grants MUST NOT reveal whether an account exists for a given identifier.
- **FR-011**: Every grant and revocation MUST produce an audit record including actor, grantee, permission level, prompt affected, and outcome, consistent with the application's existing audit event standards.
- **FR-012**: Share management operations MUST be rate-limited consistently with the application's other sensitive endpoints.
- **FR-013**: Users MUST NOT be able to share a prompt with themselves.
- **FR-014**: Deleting a prompt MUST remove all grants on it. Hard-deleting a user MUST remove all grants naming them as grantee, while grants they issued on their (now ownerless) prompts persist and remain revocable by admins; deactivating a user changes no share data.
- **FR-015**: All sharing-related interface text MUST be available in all four supported languages (English, French, Spanish, German).

### Key Entities

- **Share grant**: The permission a prompt's owner (or an admin) extends to one other user for one prompt. Attributes: the prompt concerned, the grantee, the permission level (read or edit), who granted it, and when. Uniquely identified by the (prompt, grantee) pair.
- **Prompt** *(existing)*: Gains a set of zero or more share grants and, from a viewer's perspective, a derived "shared with me" status.
- **User** *(existing)*: Can act as grantor (for prompts they own), grantee, or admin overseer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A prompt owner can share a prompt with a teammate — from opening the sharing controls to confirmation — in under 30 seconds.
- **SC-002**: 100% of access decisions in the authorization matrix (owner / grantee-read / grantee-edit / stranger / admin, crossed with view / edit / delete / share management) behave as specified, verified by automated tests.
- **SC-003**: A recipient can locate any prompt shared with them via the "shared with me" filter in one interaction, and revoked prompts disappear from their view immediately (next page load at the latest).
- **SC-004**: Listing and searching a combined owned + shared prompt set shows no perceptible slowdown to users compared with owned-only listings at equivalent volumes.
- **SC-005**: 100% of grant and revocation actions produce a complete audit record.
- **SC-006**: Zero pathways allow discovering whether an account exists for an arbitrary identifier through the sharing feature.

## Assumptions

- **Prompt-level sharing only in v1**: The improvement plan mentions per-collection sharing in passing, but its entire scope of work covers per-prompt grants. Sharing whole categories/collections is out of scope for this feature and can build on the same model later.
- **Two permission levels suffice**: "read" and "edit" only; no "comment", "manage", or custom roles in v1.
- **Sharing is user-to-user**: No group/team/role-based grants and no public or link-based sharing in v1.
- **Existing accounts, authentication, and RBAC are reused**: Recipients must already have an account; the feature does not include inviting new users.
- **Single-instance scope**: Sharing operates within one PromptVault deployment; cross-instance sharing is out of scope.
- **Version history remains unified**: Edits by grantees enter the prompt's existing single version history with author attribution, per current versioning behavior.
- **Typeahead user lookup is acceptable for authenticated users**: Any authenticated user may typeahead-search the directory while sharing (usernames only, active accounts only) — the deployment model is team-internal, like sharing in office suites; only *failure responses* must avoid confirming account existence (mirroring the existing password-reset behavior).
- **No notifications in v1**: Recipients discover new shares passively via the "shared with me" filter and "Shared" badges; no in-app or email notification is sent when a grant is created.
- **Export/import and backup flows are unchanged**: Grants follow the fate of prompts in backups/restores; exported prompt files do not carry grants.
