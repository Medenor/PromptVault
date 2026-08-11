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
- Q: Today any user (even unauthenticated) can view any prompt. Does this feature change default visibility so prompts are private to their owner unless explicitly shared, or does it layer sharing on top of the existing global-read model? → A: Private by default — prompts created after this feature ships are visible only to their owner (and admins) unless explicitly shared.
- Q: What happens to prompts that already exist today (currently globally visible)? → A: Grandfathered as public — prompts that exist at the time this feature ships keep their current visibility to all authenticated users; only prompts created after the change default to private.
- Q: For grandfathered "public" prompts, what can any authenticated user do with them? → A: View only, equivalent to an implicit "read" share to everyone; editing a grandfathered public prompt still requires an explicit "edit" grant like any other prompt.
- Q: Can a grandfathered public prompt be converted to private, share-controlled visibility? → A: Yes — the owner (or an admin) can flip a grandfathered prompt from public to private at any time; once flipped, it follows the same private-plus-explicit-grants model as new prompts and this action cannot be undone by the grantee (only the owner/admin can re-share it explicitly).

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

- **Default visibility change**: prompts created after this feature ships are visible only to their owner and admins unless explicitly shared (no more implicit global read access for new prompts).
- **Existing prompts grandfathered**: prompts that already exist when this feature ships remain visible to all authenticated users (view only — editing still requires an explicit "edit" grant or ownership). This grandfathered visibility is a migration aid, not a permanent second visibility tier.
- **Un-grandfathering**: the owner (or an admin) can convert a grandfathered public prompt to private at any time; once converted, it follows the same private-plus-explicit-grants model as any other prompt and is not automatically shared with anyone who previously had implicit view access.
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
- **FR-016**: Prompts created after this feature ships MUST default to private visibility: viewable only by their owner and admins, plus any user explicitly granted "read" or "edit" access. Unauthenticated access to prompt listing/detail endpoints MUST no longer return prompts belonging to another user by default.
- **FR-017**: Prompts that already exist at the time this feature ships MUST be marked as grandfathered-public and remain viewable by all authenticated users (view only), without requiring an explicit share grant; this grandfathered status does not grant edit access.
- **FR-018**: The owner of a grandfathered-public prompt (or an admin) MUST be able to convert it to private visibility; once converted, the prompt follows the same default-private, explicit-grant model as any other prompt, and the conversion MUST NOT itself create any share grants.

### Key Entities

- **Share grant**: The permission a prompt's owner (or an admin) extends to one other user for one prompt. Attributes: the prompt concerned, the grantee, the permission level (read or edit), who granted it, and when. Uniquely identified by the (prompt, grantee) pair.
- **Prompt** *(existing)*: Gains a set of zero or more share grants, a visibility state (private-by-default, or grandfathered-public for pre-existing prompts until converted), and, from a viewer's perspective, a derived "shared with me" status.
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
- **Sharing is user-to-user**: No group/team/role-based grants and no new public or link-based sharing mechanism in v1; the only "public" visibility is the one-time grandfathering of pre-existing prompts described below, not a feature owners can newly opt into.
- **Existing accounts, authentication, and RBAC are reused**: Recipients must already have an account; the feature does not include inviting new users.
- **Default visibility flips from global-read to private-by-default**: today, prompt listing/detail endpoints have no owner filter at all (verified in code) — any authenticated or even unauthenticated caller can view any prompt. This feature changes that baseline: prompts created after it ships are visible only to their owner, admins, and explicit grantees. Prompts that already exist are grandfathered to remain publicly viewable (not editable) until their owner or an admin converts them to private, which is a one-time transition aid rather than a permanent parallel visibility model.
- **Single-instance scope**: Sharing operates within one PromptVault deployment; cross-instance sharing is out of scope.
- **Version history remains unified**: Edits by grantees enter the prompt's existing single version history with author attribution, per current versioning behavior.
- **Typeahead user lookup is acceptable for authenticated users**: Any authenticated user may typeahead-search the directory while sharing (usernames only, active accounts only) — the deployment model is team-internal, like sharing in office suites; only *failure responses* must avoid confirming account existence (mirroring the existing password-reset behavior).
- **No notifications in v1**: Recipients discover new shares passively via the "shared with me" filter and "Shared" badges; no in-app or email notification is sent when a grant is created.
- **Export/import and backup flows are unchanged**: full database backup/restore preserves grants and `legacy_public` in full fidelity (whole-DB dump). CSV/Markdown/JSON export is, and remains, grant-blind by design: exported prompt files never carry `prompt_shares` grants or `legacy_public` (a `grantee_user_id` reference would be meaningless across instances/restores). REPLACE-mode import deletes existing prompts before loading the new file, which cascade-deletes any active grants on those prompts as a side effect; the operator is warned (active share count + confirmation) and a dedicated audit event is recorded before this proceeds, but the grants themselves are not preserved or reconstructed from the import file.
