# Accessibility Landmarks and Live Regions

This document tracks the current landmark structure and live-region usage used for screen-reader navigation and dynamic announcements.

## Landmarks

The main templates now expose explicit landmarks for rapid navigation:

- `role="banner"` on page headers (for example `src/web/templates/index.html`, `src/web/templates/import_export.html`, `src/web/templates/admin/users.html`)
- `role="navigation"` on header action groups and admin/mobile navigation menus
- `role="main"` on the main content container (`#main-content`) on active pages
- `role="complementary"` on index sidebars (desktop and mobile) used for prompt filters and category/tag navigation

The `?` help modal in `src/web/static/ts/app.ts` now includes a "Landmarks on this page" section generated from detected landmarks.

## Live Regions

Live regions are used for non-blocking feedback and validation updates:

- `aria-live="assertive"` for validation errors and critical form feedback
- `aria-live="polite"` for counters and progressive hints (for example password strength and character counters)
- Notification toasts in `src/web/static/ts/utils/notifications.ts` are created with `aria-live="polite"`

Representative locations:

- `src/web/templates/index.html`: prompt editor validation and counters
- `src/web/templates/auth/register.html`: password strength (`polite`) and field errors (`assertive`)
- `src/web/templates/auth/profile.html`: password change form feedback
- `src/web/templates/import_export.html`: import/export validation errors
- `src/web/templates/backup_management.html`: backup form and maintenance validation errors

## Verification Notes

- Heading sequence and `h1` cardinality were re-checked across templates on 2026-02-06.
- Each reviewed template contains exactly one `h1` and no heading-level jumps greater than one level.
