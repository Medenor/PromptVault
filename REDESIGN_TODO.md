# PromptVault Flat Design System Redesign — Comprehensive Todo List

**Project**: Complete UI redesign of PromptVault frontend using flat design philosophy
**Tech Stack**: TypeScript + Vite + Tailwind CSS
**Scope**: All 8 pages + component system + test suite
**Priority**: Visual polish, consistency, component reusability, modularity

---

## PHASE 1: Foundation & Setup

### 1.1 Tailwind CSS Installation & Configuration

- [X] ~~*Install Tailwind CSS and dependencies (`tailwindcss`, `postcss`, `autoprefixer`)*~~ [2025-12-21]
- [X] ~~*Create `tailwind.config.ts` with custom design tokens:*~~ [2025-12-21]
  - Color palette (Primary Blue, Secondary Emerald, Accent Amber, Neutrals, etc.)
  - Typography (Outfit font family, font weights, sizes, line-heights)
  - Spacing scale (match flat design spec)
  - Border radius (md/lg defaults, pill for tags)
  - Box shadows (set to none explicitly)
  - Transition/animation defaults (duration-200, scale effects)
- [X] ~~*Create `postcss.config.ts` for Tailwind processing*~~ [2025-12-21]
- [X] ~~*Create base CSS file (`/src/web/static/css/tailwind-globals.css`) with:*~~ [2025-12-21]
  - `@tailwind` directives
  - Global typography (Outfit font import)
  - Base element resets
  - CSS custom properties for subtle design elements
- [X] ~~*Update Vite config to process Tailwind CSS*~~ [2025-12-21]
- [X] ~~*Verify Tailwind CSS is being applied in dev mode*~~ [2025-12-21]

### 1.2 TypeScript Path Aliases & Component Module Setup

- [ ] Create `/src/web/static/ts/components/` directory structure:

  ```
  components/
  ├── index.ts              # Central export file
  ├── button.ts             # Button component factory
  ├── card.ts               # Card component factory
  ├── input.ts              # Input component factory
  ├── form.ts               # Form element factories
  ├── modal.ts              # Modal component factory
  ├── layout.ts             # Layout primitives (header, section, container, etc.)
  ├── navigation.ts         # Nav components (breadcrumbs, tabs, etc.)
  ├── __tests__/            # Component tests
  │   ├── button.test.ts
  │   ├── card.test.ts
  │   ├── input.test.ts
  │   └── form.test.ts
  └── types.ts              # Component TypeScript interfaces
  ```

- [ ] Update TypeScript path aliases to include `@components`

---

## PHASE 2: Component System

### 2.1 Component Types & Interfaces

- [ ] Create `/src/web/static/ts/components/types.ts` with interfaces for:
  - `ButtonProps` (variant: primary/secondary/outline, size, disabled, loading, onClick)
  - `CardProps` (variant, padding, clickable, decorative background color)
  - `InputProps` (type, placeholder, value, error, required, disabled)
  - `FormGroupProps` (label, required, error, helpText)
  - `ModalProps` (title, content, actions, size)
  - `LayoutProps` (container, section, header, footer)
  - Document expected class names for styling

### 2.2 Button Component Factory

- [ ] Create `/src/web/static/ts/components/button.ts` with:
  - Function `createButton(label, props: ButtonProps): HTMLButtonElement`
  - Support variants: primary, secondary, outline
  - Support sizes: sm, md, lg
  - Default: `rounded-md`, hover effects (scale-105, color shift)
  - Handle loading state (spinner icon, disabled)
  - Type-safe TypeScript implementation
  - Export helper: `createPrimaryButton()`, `createSecondaryButton()`, `createOutlineButton()`
- [ ] Add proper accessibility attributes (aria-label, aria-busy, etc.)

### 2.3 Card Component Factory

- [ ] Create `/src/web/static/ts/components/card.ts` with:
  - Function `createCard(props: CardProps): HTMLDivElement`
  - Support variants: white, muted, colored (blue-50, green-50, amber-50)
  - Support padding: compact, default, generous
  - Hover effects: `scale-[1.02]`, color intensification
  - Optional clickable state with cursor pointer
  - Optional decorative background shape
  - Export helpers: `createWhiteCard()`, `createColoredCard(color)`

### 2.4 Input Component Factory

- [ ] Create `/src/web/static/ts/components/input.ts` with:
  - Function `createInput(props: InputProps): HTMLInputElement`
  - Support types: text, email, password, number, search, date, file
  - Default styling: `bg-gray-100`, no border normally, `border-2 border-blue-500` on focus
  - Error state: red border + error text below
  - Success state: green border
  - Help text support
  - Required indicator
  - Placeholder styling
- [ ] Create helper functions: `createEmailInput()`, `createPasswordInput()`, `createSearchInput()`

### 2.5 Form Group Component Factory

- [ ] Create `/src/web/static/ts/components/form.ts` with:
  - Function `createFormGroup(label, input, props): HTMLDivElement`
  - Wrapper for label + input + error/help text
  - Label styling: bold (font-medium/600), uppercase for button-like labels
  - Error message styling (red text, small font)
  - Help text styling (gray text, smaller)
  - Required indicator (red asterisk or badge)
  - Export helper: `createLabeledInput()`, `createLabeledSelect()`

### 2.6 Modal/Dialog Component Factory

- [ ] Create `/src/web/static/ts/components/modal.ts` with:
  - Function `createModal(props: ModalProps): HTMLDivElement`
  - Dark overlay (bg-black/50)
  - Centered white card with content
  - Title heading (h2, bold)
  - Content area with padding
  - Action buttons footer (primary/secondary)
  - Close button (X icon, top-right)
  - Keyboard support (ESC to close)
  - Focus trap
  - Export helpers: `createConfirmModal()`, `createAlertModal()`

### 2.7 Layout Primitives

- [ ] Create `/src/web/static/ts/components/layout.ts` with:
  - `createContainer(): HTMLDivElement` — max-w-7xl, mx-auto, px-4
  - `createSection(backgroundColor?): HTMLElement` — full-width section with color
  - `createHeader(props): HTMLElement` — header with logo, nav, user menu
  - `createFooter(props): HTMLElement` — footer with links, copyright
  - `createGrid(cols): HTMLDivElement` — responsive grid (grid-cols-1 md:grid-cols-X)
  - `createFlex(direction, gap): HTMLDivElement` — flex wrapper
  - Export helpers for responsive layouts

### 2.8 Navigation Components

- [ ] Create `/src/web/static/ts/components/navigation.ts` with:
  - `createTabs(tabs: Array<{label, id, active, onClick}>): HTMLDivElement`
  - `createBreadcrumbs(items: Array<{label, href}>): HTMLNav`
  - `createNav(items: Array<{label, href, icon?, active?}>): HTMLNav`
  - Tab styling: underline on active, hover effects
  - Breadcrumb separators and styling
  - Nav item styling with icons

### 2.9 Form Utilities (Extended)

- [ ] Create helper functions in components/form.ts for:
  - `createSelectInput(options, props): HTMLSelectElement`
  - `createTextarea(props): HTMLTextAreaElement`
  - `createCheckbox(label, props): HTMLDivElement` (wrapped checkbox + label)
  - `createRadioGroup(options, props): HTMLDivElement` (radio buttons)
  - `createTagInput(props): HTMLDivElement` (tag input with autocomplete)
  - `createUploadInput(props): HTMLDivElement` (file upload with preview)
- [ ] All with proper validation state styling

### 2.10 Component System Testing

- [ ] Create `/src/web/static/ts/components/__tests__/button.test.ts`
  - Test button creation, variants, sizes, click handlers
  - Test loading state, disabled state
  - Test accessibility attributes
- [ ] Create `/src/web/static/ts/components/__tests__/card.test.ts`
  - Test card variants, padding options
  - Test click handler attachment
- [ ] Create `/src/web/static/ts/components/__tests__/input.test.ts`
  - Test input types, value binding
  - Test error/success states
  - Test placeholder and help text
- [ ] Create `/src/web/static/ts/components/__tests__/form.test.ts`
  - Test form group creation
  - Test label and input association
  - Test validation error display
- [ ] Create `/src/web/static/ts/components/__tests__/layout.test.ts`
  - Test container, section, grid creation
  - Test responsive layout helpers
- [ ] Ensure all tests pass with vitest
- [ ] Target 80%+ coverage for components module

---

## PHASE 3: Page Redesigns (8 pages)

### 3.1 Main App Page (Prompt Listing, CRUD, Versioning)

**Files**: `app.ts`, `index.html`

- [ ] Redesign HTML template (`index.html`):
  - Header: Logo, search bar, user menu, navigation
  - Main layout: Sidebar (optional) or top navigation
  - Prompt list: Cards in grid (responsive 1-3 columns)
  - Each prompt card: Title, description, tags, category, actions (edit/delete/version)
  - Modals for create/edit prompt
  - Version history modal
  - Bulk actions bar (checkbox select, delete, export)
  - Filter panel (categories, tags, favorites, search)

- [ ] Update `app.ts`:
  - Replace DOM creation calls with component utilities
  - Refactor `initializeApp()` to use `createContainer()`, `createGrid()`, etc.
  - Refactor prompt card creation to use `createCard()`
  - Refactor modal dialogs to use `createModal()`
  - Refactor form inputs to use `createInput()`, `createFormGroup()`
  - Update event handlers to work with new component structure
  - Test all CRUD operations work correctly

- [ ] Remove old CSS from `style.css` related to app layout
- [ ] Add Tailwind classes to template where component utilities don't apply
- [ ] Visual testing: Verify layout, spacing, colors, responsiveness

### 3.2 Auth Pages (Login, Register)

**Files**: `auth.ts`, `auth/login.html`, `auth/register.html`

- [ ] Redesign login page template:
  - Centered white card
  - Logo/branding at top
  - Form with email + password inputs
  - "Remember me" checkbox
  - Login button (primary, full-width)
  - "Forgot password?" link
  - "Create account" link at bottom
  - Optional decorative background elements (geometric shapes)

- [ ] Redesign register page template:
  - Similar card layout
  - Name + email + password + confirm password inputs
  - Password strength indicator
  - Terms of service checkbox
  - Register button
  - "Already have account?" link

- [ ] Update `auth.ts`:
  - Refactor form creation to use component utilities
  - Use `createInput()` for all form fields
  - Use `createButton()` for submit buttons
  - Use `createFormGroup()` for labels + error messages
  - Update validation error display
  - Verify password strength indicator works with new styles

- [ ] Remove old CSS from `auth.css`
- [ ] Visual testing: Form styling, error states, responsiveness

### 3.3 User Profile Page

**Files**: `profile.ts`, `auth/profile.html`

- [ ] Redesign profile template:
  - Header with user info (avatar, username, email status)
  - Form sections:
    - Basic info (name, email, email verification status)
    - Language selector
    - Preferences
    - Password change
    - Danger zone (account deletion)
  - Each section in its own card
  - Save/cancel buttons per section

- [ ] Update `profile.ts`:
  - Refactor form sections to use component utilities
  - Use `createCard()` for each section
  - Use `createInput()` and `createButton()` throughout
  - Update form submission and validation
  - Verify email verification status display

- [ ] Remove old CSS
- [ ] Visual testing: Form interactions, validation, responsiveness

### 3.4 Password Reset Pages (Forgot Password, Reset)

**Files**: `password-reset.ts`, `auth/forgot_password.html`, `auth/reset_password.html`

- [ ] Redesign forgot password template:
  - Card with "Forgot Your Password?" title
  - Email input field
  - Submit button
  - Back to login link
  - Success message display

- [ ] Redesign reset password template:
  - Card with "Reset Password" title
  - Password + confirm password inputs
  - Password strength indicator
  - Submit button
  - Success/error messaging

- [ ] Update `password-reset.ts`:
  - Refactor forms to use component utilities
  - Update error/success message styling
  - Verify token validation and flow

- [ ] Remove old CSS
- [ ] Visual testing: Form states, error messages, responsiveness

### 3.5 Admin Users Page

**Files**: `admin-users.ts`, `admin/users.html`

- [ ] Redesign users table/list:
  - Search/filter bar at top
  - Table or card grid layout (responsive)
  - Columns: Username, Email, Role, Status, Actions (edit/deactivate)
  - Pagination (if needed)
  - Create new user button
  - User edit modal with form fields:
    - Username, email, role selector, status toggle

- [ ] Update `admin-users.ts`:
  - Refactor table/list creation
  - Use component utilities for forms and modals
  - Update action handlers (edit, deactivate, delete)
  - Verify bulk operations if present

- [ ] Remove old CSS from `admin.css`
- [ ] Visual testing: Table styling, modal interactions, responsiveness

### 3.6 Admin Sessions Page

**Files**: `admin-sessions.ts`, `admin/sessions.html`

- [ ] Redesign sessions table/list:
  - Search/filter bar at top
  - Table or card layout showing:
    - User, IP address, user agent, login time, last activity, actions (terminate)
  - Pagination
  - Bulk terminate option

- [ ] Update `admin-sessions.ts`:
  - Refactor table creation
  - Use component utilities for layouts and buttons
  - Update terminate handlers
  - Verify refresh/polling if present

- [ ] Remove old CSS from `sessions.css`
- [ ] Visual testing: Layout, action buttons, responsiveness

### 3.7 Import/Export Page

**Files**: `import-export.ts`, `import_export.html`

- [ ] Redesign import/export template:
  - Two main cards/sections:
    1. **Import**: File upload area, format selector (CSV/JSON/MD), import button, progress
    2. **Export**: Format selector, export button, progress display, success message
  - Format info cards (describing each format)
  - Recent imports/exports history (optional)

- [ ] Update `import-export.ts`:
  - Refactor form creation
  - Use component utilities for uploads and buttons
  - Update file upload UX (drag-drop, file preview)
  - Update progress display styling
  - Verify error/success messaging

- [ ] Remove old CSS
- [ ] Visual testing: Upload areas, progress indicators, format selection, responsiveness

### 3.8 Backup Management Page

**Files**: `backup-management.ts`, `backup_management.html`

- [ ] Redesign backup template:
  - Header with backup info/stats (count, last backup, total size)
  - Create backup button (prominent, primary)
  - Backup list/table with:
    - Filename, size, created date, actions (download, restore, delete)
  - Cleanup settings card (auto-cleanup options)
  - Restore from file upload area

- [ ] Update `backup-management.ts`:
  - Refactor list creation
  - Use component utilities for forms, buttons, modals
  - Update action handlers (create, download, restore, delete)
  - Verify cleanup logic

- [ ] Remove old CSS
- [ ] Visual testing: Layout, action buttons, modals, responsiveness

### 3.9 Remove Old CSS Files

- [ ] After all pages are redesigned and tested, remove/clean:
  - `/src/web/static/css/style.css` (or keep only non-component styles)
  - `/src/web/static/css/auth.css`
  - `/src/web/static/css/admin.css`
  - `/src/web/static/css/sessions.css`
  - `/src/web/static/css/validation.css` (validation now handled by Tailwind)
  - Keep only: Tailwind globals, Outfit font import, any custom animations

---

## PHASE 4: Styling & Visual Polish

### 4.1 Tailwind Configuration Fine-Tuning

- [ ] Review all Tailwind color tokens against design spec
- [ ] Fine-tune spacing scale if needed
- [ ] Verify typography sizes and line-heights
- [ ] Test all color combinations for accessibility (contrast ratios)
- [ ] Verify border radius consistency
- [ ] Confirm transition durations are correct (200ms default, 300ms for larger transforms)

### 4.2 Global Base Styles

- [ ] Review and adjust tailwind-globals.css:
  - Form input base styles
  - Typography base styles
  - Link styling (color, underline, hover)
  - Table styling if needed
  - Code block styling (if present)
  - Scrollbar styling (optional for design expression)

### 4.3 Dark Mode Support (Optional)

- [ ] If required, implement Tailwind dark mode:
  - Add `darkMode: 'class'` to tailwind config
  - Create dark mode color tokens
  - Test on all pages
  - Add toggle in user profile or header

### 4.4 Animation & Motion

- [ ] Verify all hover states use scale effects:
  - Buttons: `hover:scale-105 transition-all duration-200`
  - Cards: `hover:scale-[1.02] transition-all duration-200`
  - Icons in cards: `group-hover:scale-110 transition-transform duration-200`
- [ ] Add any decorative animations:
  - Loading spinners
  - Page transitions
  - Entrance animations (optional, subtle)
- [ ] Test animations are smooth and not jarring

### 4.5 Validation & Error Styling

- [ ] Ensure error states are consistent across all inputs:
  - Red border, red error text below input
  - Filled error background optional
- [ ] Warning states (if used): yellow/amber border and text
- [ ] Success states (if used): green border and text
- [ ] Test validation errors display correctly in all forms

---

## PHASE 5: Testing & Quality Assurance

### 5.1 Unit Test Updates

- [ ] Update existing tests in `src/web/static/ts/__tests__/`:
  - `api.test.ts` — no changes needed unless API utils change
  - `dom.test.ts` — may need updates if DOM utilities changed
  - `i18n.test.ts` — no changes needed
  - `notifications.test.ts` — no changes needed
  - `utils-index.test.ts` — update if exports changed

- [ ] Create new tests for component system:
  - `components/__tests__/button.test.ts`
  - `components/__tests__/card.test.ts`
  - `components/__tests__/input.test.ts`
  - `components/__tests__/form.test.ts`
  - `components/__tests__/layout.test.ts`
  - Each test file covers: creation, props, styling classes, event handlers

- [ ] Run `npm run test:unit` — ensure all tests pass
- [ ] Run `npm run test:unit:coverage` — verify coverage meets thresholds (70% lines, 60% branches, 70% functions, 70% statements)
- [ ] Fix any coverage gaps

### 5.2 Build Verification

- [ ] Run `npm run build` — verify TypeScript compilation succeeds
- [ ] Check build output size — ensure CSS bundle is reasonable (~30-50KB)
- [ ] Verify no console errors or warnings in build output
- [ ] Check that all pages build correctly with their entry points

### 5.3 Dev Server Testing

- [ ] Run `npm run dev` — start dev server
- [ ] Test all 8 pages load without errors
- [ ] Verify hot module replacement works (HMR) for CSS and TS
- [ ] Check console for any warnings or errors
- [ ] Test form interactions on each page

### 5.4 Visual Regression Testing (Manual)

- [ ] On each page, verify:
  - Layout is responsive (test at 375px, 768px, 1024px, 1440px)
  - Colors match design spec
  - Typography sizes and weights are correct
  - Spacing/padding/margins are consistent
  - Buttons and interactive elements have hover states
  - Forms display errors correctly
  - Modals center and overlay correctly
  - Navigation works across all pages

### 5.5 Accessibility Audit

- [ ] Run automated accessibility check (axe DevTools or Lighthouse)
- [ ] Manual keyboard navigation testing:
  - Tab through all form inputs and buttons
  - Verify focus indicators are visible (should be default blue outline from Tailwind)
  - Verify modals trap focus
  - ESC key closes modals
- [ ] Check color contrast ratios for all text (WCAG AA minimum)
- [ ] Verify alt text on images
- [ ] Test screen reader compatibility (optional but recommended)

### 5.6 Cross-Browser Testing

- [ ] Test on:
  - Chrome/Chromium (latest)
  - Firefox (latest)
  - Safari (latest)
  - Edge (latest)
  - Mobile Safari (iOS)
  - Chrome Mobile (Android)
- [ ] Check for any layout issues or styling discrepancies
- [ ] Verify all interactive elements work (modals, forms, buttons)

### 5.7 Playwright E2E Tests

- [ ] Update existing Playwright tests in `scripts/playwright_auth_ui_tests.ts`:
  - Verify login flow with new styling
  - Verify register flow with new styling
  - Test password reset flow
- [ ] Consider adding tests for:
  - Main app page (prompt creation, search, delete)
  - Profile page updates
  - Admin pages (if applicable)
- [ ] Run `npm run test:ui:headed` — verify all tests pass

---

## PHASE 6: Polish, Optimization & Cleanup

### 6.1 Tailwind CSS Purging & Optimization

- [ ] Verify Tailwind config has correct content paths for purging
- [ ] Build production bundle and check CSS size
- [ ] Ensure unused CSS is not in production build
- [ ] Consider adding `@apply` for repeated utility patterns if needed (minimal usage)

### 6.2 Code Review & Cleanup

- [ ] Review component system for code quality:
  - Check for consistent naming patterns
  - Verify all components have JSDoc comments
  - Ensure no duplicate utilities
  - Check TypeScript strictness
- [ ] Review page-level TypeScript:
  - Ensure component utilities are used consistently
  - Remove any unused CSS class references
  - Verify error handling is intact
- [ ] Run `npm run lint` — fix any linting issues
- [ ] Run `npm run format` — apply Prettier formatting

### 6.3 Documentation

- [ ] Create `/src/web/static/ts/components/README.md`:
  - Component system overview
  - How to use each component utility
  - Examples for each component type
  - Best practices for component creation
  - Migration guide from old styling approach
- [ ] Document Tailwind config decisions
- [ ] Update any relevant project docs

### 6.4 Type Safety Verification

- [ ] Run `npm run typecheck` — ensure no TypeScript errors
- [ ] Verify all new components have proper TypeScript types
- [ ] Check that all event handlers have correct types

### 6.5 Performance Verification

- [ ] Run Lighthouse on each page (mobile and desktop)
- [ ] Check metrics:
  - First Contentful Paint (FCP)
  - Largest Contentful Paint (LCP)
  - Cumulative Layout Shift (CLS)
  - Total Blocking Time (TBT)
- [ ] Identify any performance regressions vs. old design
- [ ] Optimize if needed (lazy loading, code splitting already in place via Vite)

### 6.6 Final Visual Polish

- [ ] Review all pages for visual consistency:
  - Color usage matches design spec
  - Typography hierarchy is clear
  - Spacing is balanced
  - Icons and interactive elements are polished
  - Hover/focus states work smoothly
- [ ] Test all animated transitions (should be smooth, not janky)
- [ ] Verify decorative elements (geometric shapes, if any) render correctly
- [ ] Check print styling if needed

---

## PHASE 7: Production Deployment

### 7.1 Pre-Deployment Checklist

- [ ] All tests pass (`npm run test:unit`, `npm run test:ui:headed`)
- [ ] Build succeeds (`npm run build`)
- [ ] No console errors or warnings in dev or production mode
- [ ] All pages are visually polished and responsive
- [ ] Accessibility audit passed
- [ ] Cross-browser testing completed
- [ ] Performance metrics are acceptable

### 7.2 Deploy to Production

- [ ] Merge redesign branch to main
- [ ] Build and deploy to production environment
- [ ] Smoke test all pages in production
- [ ] Monitor error logs for any new issues
- [ ] Gather user feedback on new design

### 7.3 Post-Deployment Monitoring

- [ ] Monitor performance metrics (Lighthouse, Web Vitals)
- [ ] Watch for user feedback or bug reports
- [ ] Be ready to hotfix any critical issues
- [ ] Plan any follow-up polish or refinements

---

## SUMMARY OF DELIVERABLES

### Code Artifacts

1. ✅ `tailwind.config.ts` — Complete design token system
2. ✅ `postcss.config.ts` — PostCSS configuration
3. ✅ `/src/web/static/css/tailwind-globals.css` — Global styles
4. ✅ `/src/web/static/ts/components/` — Reusable component system (10+ component utilities)
5. ✅ Updated `/src/web/static/ts/app.ts` — Using component utilities
6. ✅ Updated `/src/web/static/ts/auth.ts` — Using component utilities
7. ✅ Updated `/src/web/static/ts/profile.ts` — Using component utilities
8. ✅ Updated `/src/web/static/ts/password-reset.ts` — Using component utilities
9. ✅ Updated `/src/web/static/ts/admin-users.ts` — Using component utilities
10. ✅ Updated `/src/web/static/ts/admin-sessions.ts` — Using component utilities
11. ✅ Updated `/src/web/static/ts/import-export.ts` — Using component utilities
12. ✅ Updated `/src/web/static/ts/backup-management.ts` — Using component utilities
13. ✅ Updated all HTML templates with new flat design layout
14. ✅ Component system tests (80%+ coverage)
15. ✅ Updated Playwright E2E tests

### Testing Artifacts

1. ✅ Component unit tests (vitest)
2. ✅ All existing unit tests updated/passing
3. ✅ Updated E2E tests (Playwright)
4. ✅ Visual regression testing (manual screenshots)
5. ✅ Accessibility audit results
6. ✅ Cross-browser testing verification

### Documentation

1. ✅ `REDESIGN_TODO.md` (this file) — project plan
2. ✅ `/src/web/static/ts/components/README.md` — component system guide
3. ✅ Inline JSDoc comments in all component utilities
4. ✅ Migration guide for developers

---

## TASK ASSIGNMENT GUIDANCE FOR SUBAGENTS

When delegating items from this todo list to subagents (e.g., `coder`, `tester`), use these groupings:

**Task 1: Tailwind Setup** (Phase 1)

- Tasks 1.1, 1.2

**Task 2: Component System** (Phase 2)

- Tasks 2.1 through 2.10

**Task 3-10: Page Redesigns** (Phase 3)

- Each page gets its own task:
  - Task 3: Main App Page
  - Task 4: Auth Pages
  - Task 5: Profile Page
  - Task 6: Password Reset
  - Task 7: Admin Users
  - Task 8: Admin Sessions
  - Task 9: Import/Export
  - Task 10: Backup Management

**Task 11: Testing & QA** (Phase 4 & 5)

- Tasks 4.1 through 5.7

**Task 12: Final Polish** (Phase 6)

- Tasks 6.1 through 6.6

**Task 13: Production** (Phase 7)

- Tasks 7.1 through 7.3

---

**Document Version**: 1.0
**Last Updated**: 2025-12-21
**Created by**: Orchestrator Agent
