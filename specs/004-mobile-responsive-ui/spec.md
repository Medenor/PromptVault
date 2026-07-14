# Feature Specification: Mobile-Responsive UI Enhancements

**Feature Branch**: `004-mobile-responsive-ui`

**Created**: 2026-07-09

**Status**: Draft

**Input**: User description: "Mobile-Responsive UI Enhancements (Codeberg #20): Improve mobile user experience with touch-optimized controls, responsive layouts for small screens, mobile-specific navigation (hamburger menu, bottom nav), offline support via Service Workers, and mobile-friendly gestures (swipe actions, pull-to-refresh)."

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Navigate and manage prompts on a phone (Priority: P1)

A user opens PromptVault on their phone during a commute to find, read, and edit a saved prompt. They need a navigation and layout experience built for touch and small screens rather than a shrunk-down desktop layout.

**Why this priority**: This is the core value of the feature — without a usable mobile layout and navigation, none of the other mobile capabilities matter. It is the MVP slice that makes the app usable on a phone at all.

**Independent Test**: Load the app on a 375px-wide viewport, open the slide-out navigation drawer via a hamburger control, tap into a prompt, and edit it — all without horizontal scrolling or accidental mis-taps.

**Acceptance Scenarios**:

1. **Given** the app is loaded on a viewport narrower than 768px, **When** the user taps the hamburger icon, **Then** a slide-out navigation drawer opens showing the same navigation options available on desktop.
2. **Given** the navigation drawer is open on mobile, **When** the user taps outside the drawer or selects a destination, **Then** the drawer closes and the app does not retain any horizontally-scrolling layout on the main content.
3. **Given** a user is viewing the prompt list on a small screen, **When** they tap any interactive control (button, icon, menu item), **Then** the control responds correctly on the first tap because its touch target is at least 44x44px.
4. **Given** a user opens a prompt for editing on mobile, **When** the on-screen keyboard appears, **Then** the input field being edited remains visible and is not obscured by the keyboard.

---

### User Story 2 - Work with prompts offline and get back online seamlessly (Priority: P2)

A user loses connectivity (e.g., in transit) while using PromptVault. They expect to still view previously loaded prompts, and any edits they make should sync automatically once connectivity returns.

**Why this priority**: Offline resilience is a major differentiator called out in the ticket and materially expands where/when the app is usable, but it depends on the mobile layout (P1) already being in place to be worth using on a phone.

**Independent Test**: Load the app while online, switch the device/browser to offline mode, confirm previously-viewed prompts remain visible with an offline indicator, make an edit, then restore connectivity and confirm the edit syncs without user intervention.

**Acceptance Scenarios**:

1. **Given** the user has previously loaded the app while online, **When** connectivity is lost, **Then** an offline indicator appears and previously-viewed prompts remain accessible from cache.
2. **Given** the app is offline, **When** the user edits or creates a prompt, **Then** the change is queued locally and the user is informed the change will sync later.
3. **Given** queued offline changes exist, **When** connectivity is restored, **Then** the queued changes sync automatically without requiring the user to manually retry.
4. **Given** the user is offline and requests data that was never cached, **When** they attempt to load it, **Then** the app shows a clear "unavailable offline" message rather than a generic error or blank screen.

---

### User Story 3 - Use touch gestures and an installable app shortcut (Priority: P3)

A frequent mobile user wants faster interactions than desktop-style menus allow: swiping a prompt card to edit or delete it, pulling down to refresh the list, and adding PromptVault to their home screen like a native app.

**Why this priority**: These are efficiency and delight enhancements on top of a working, installable mobile experience (P1/P2). The app is fully usable without them, but they reduce friction for repeat mobile users.

**Independent Test**: On a touch device, swipe a prompt card left to reveal a delete action and right to reveal an edit action, pull down on the prompt list to trigger a refresh, and use the browser's "Add to Home Screen" affordance to install the app with a proper icon and name.

**Acceptance Scenarios**:

1. **Given** a user is viewing the prompt list on a touch device, **When** they swipe a prompt card left, **Then** a delete action is revealed and requires a confirming tap before deleting.
2. **Given** a user is viewing the prompt list on a touch device, **When** they swipe a prompt card right, **Then** an edit action is revealed that opens the prompt editor.
3. **Given** a user is at the top of the prompt list on mobile, **When** they pull down and release, **Then** the list refreshes with the latest data and a loading affordance is shown during the refresh.
4. **Given** a user visits PromptVault on a supported mobile browser, **When** they use "Add to Home Screen," **Then** the app installs with its own name and icon and launches without browser chrome.

---

### Edge Cases

- What happens when a user rotates their device mid-interaction (e.g., mid-swipe-gesture or with the navigation drawer open)? Layout must adapt without losing the open/interaction state unexpectedly.
- How does the system handle a swipe gesture that starts on a scrollable element (e.g., a long prompt body) — does it conflict with vertical scroll?
- What happens when the user is offline, has queued multiple conflicting edits to the same prompt (e.g., edited on two devices), and then comes back online? The most recent queued edit wins; the user is notified if a queued change was superseded.
- What happens when Service Worker registration fails (e.g., unsupported browser, storage quota exceeded)? The app must continue to function online-only with no offline features, without breaking the base experience.
- What happens on tablets in landscape mode — should the layout use the mobile drawer/bottom-nav pattern or the desktop sidebar? Landscape tablets above the 768px breakpoint use the desktop-style layout.
- What happens when a user with a screen reader navigates the mobile drawer or swipe-gesture controls? All gesture-based actions must have an equivalent accessible control (e.g., a visible button) reachable without performing the gesture.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST present a slide-out navigation drawer, triggered by a hamburger control, on viewports narrower than 768px, replacing the desktop sidebar.
- **FR-002**: System MUST ensure all interactive elements (buttons, links, form controls, menu items) have a minimum touch target size of 44x44px on mobile viewports.
- **FR-003**: System MUST present modals as full-screen layouts on mobile viewports and as centered dialogs on desktop viewports.
- **FR-004**: System MUST support responsive layout breakpoints at minimum for 320px, 375px, 425px, and 768px viewport widths, with no horizontal scrolling of primary content at any of these widths.
- **FR-005**: System MUST keep the actively-focused input field visible on screen when the on-screen virtual keyboard is shown.
- **FR-006**: System MUST provide a floating action button on mobile for creating a new prompt, reachable from the main prompt list view.
- **FR-007**: System MUST support swipe-left on a prompt card to reveal a delete action, and swipe-right to reveal an edit action, each also reachable via a visible on-screen control for accessibility.
- **FR-008**: System MUST support a pull-to-refresh gesture on the main prompts list that reloads current data, with an equivalent visible refresh control available for non-touch input.
- **FR-009**: System MUST cache static assets and previously-viewed prompt data via a Service Worker so that previously-viewed content remains accessible while offline.
- **FR-010**: System MUST display a persistent, visible indicator when the app detects it is offline.
- **FR-011**: System MUST queue prompt create/edit changes made while offline and automatically sync them to the server once connectivity is restored, without requiring manual user action.
- **FR-012**: System MUST notify the user when a queued offline change could not be applied on sync (e.g., due to a conflicting server-side update).
- **FR-013**: System MUST provide a web app manifest enabling "Add to Home Screen" installation, including app name and icons at multiple sizes for different device resolutions.
- **FR-014**: System MUST support pinch-to-zoom and horizontal-scroll-based viewing for long prompt content and diff views on mobile, without breaking the surrounding page layout.
- **FR-015**: System MUST truncate long prompt text on mobile list/card views with a "Read More" control to expand the full content.
- **FR-016**: System MUST provide a full-screen search overlay on mobile viewports, replacing the desktop inline search bar.
- **FR-017**: System MUST support a dark color theme that follows the operating system's `prefers-color-scheme` setting.
- **FR-018**: System MUST provide a touch-friendly, swipeable interface for browsing prompt version history on mobile.
- **FR-019**: System MUST optimize initial and subsequent page loads on mobile through lazy-loading of non-critical images/assets.
- **FR-020**: System MUST provide mobile-specific accessibility support (e.g., ARIA roles/labels for the drawer, FAB, swipe actions, and search overlay) so the mobile experience remains usable with screen readers.
- **FR-021**: System MUST adapt tablet layouts based on orientation: landscape tablets at or above 768px width use the existing desktop-style layout, while portrait/narrower tablet views use the mobile layout patterns.

_Out of scope for this feature_ (explicitly deferred, tracked separately if pursued): haptic feedback, voice input for prompt creation, biometric authentication, native share-sheet integrations (SMS/WhatsApp/email), camera-based file upload, mobile-specific analytics tracking, a dedicated mobile QA test checklist artifact, and any native app wrapper (React Native/Capacitor).

### Key Entities

- **Offline Change Queue Entry**: Represents a pending create/edit action made while offline; includes the target prompt, the change payload, a timestamp, and a sync status (pending, synced, failed/conflict).
- **App Manifest**: Represents the installable app's metadata — name, icons at various resolutions, theme color, and start URL — used for "Add to Home Screen."

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: On viewports from 320px to 768px wide, users can view, create, and edit prompts without any horizontal scrolling of primary content.
- **SC-002**: 95% of interactive elements on mobile views measure at least 44x44px, verified by an automated or manual audit of primary screens.
- **SC-003**: Users can access every primary navigation destination within 2 taps on mobile (open drawer, tap destination).
- **SC-004**: Previously-viewed prompts remain viewable within 1 second of going offline, with no error state shown for cached content.
- **SC-005**: 100% of prompt edits made while offline sync successfully within 10 seconds of connectivity being restored, absent a genuine conflict.
- **SC-006**: Users can install PromptVault to their home screen in 2 steps or fewer on supported mobile browsers (iOS Safari, Android Chrome).
- **SC-007**: On a mid-tier mobile device, the prompt list view becomes interactive within 3 seconds on a simulated 4G connection.
- **SC-008**: Users successfully complete a swipe-to-delete or swipe-to-edit action on the first attempt at least 90% of the time in usability testing.

## Assumptions

- "Mobile" refers to touch-primary devices with viewport widths from 320px up to 768px; tablets in landscape at or above 768px use the existing desktop-style layout (see FR-021).
- Target mobile browsers are current-version iOS Safari and Android Chrome, consistent with the ticket's stated test targets.
- The existing authentication, prompt storage, and versioning backend APIs are reused as-is; this feature is UI/client-layer only and does not require new backend endpoints beyond what's needed to support offline sync queuing.
- Offline conflict resolution uses a "last synced write wins" strategy with user notification, since the ticket does not specify a conflict-resolution policy and this is the simplest default that avoids silent data loss.
- Dark mode via `prefers-color-scheme` is treated as in-scope because it's part of the ticket's preferred solution list and is a standard, low-risk responsive-design addition; a manual in-app toggle is not required unless a future ticket asks for one.
- Performance optimizations (lazy loading, code splitting) apply to the mobile experience introduced here; broader site-wide performance work is out of scope.
- Feature #12 (accessibility) is a soft dependency: this feature should not regress accessibility, but does not require #12 to be completed first.
