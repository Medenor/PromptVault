---
name: PromptVault
description: A calm, flat, self-hosted library for prompts and skills.
colors:
  action-blue: '#1d4ed8'
  action-blue-deep: '#1e40af'
  link-navy: '#1e3a8a'
  tint-blue: '#eff6ff'
  focus-blue: '#4a90e2'
  skill-green: '#10b981'
  amber-action: '#b45309'
  amber-action-deep: '#92400e'
  danger-red: '#b91c1c'
  paper: '#ffffff'
  ink: '#111827'
  mist: '#f3f4f6'
  hairline: '#e5e7eb'
  stone: '#6b7280'
  night-page: '#111827'
  night-surface: '#1f2937'
  night-field: '#374151'
typography:
  display:
    fontFamily: 'Outfit, sans-serif'
    fontSize: '2rem'
    fontWeight: 700
    lineHeight: 1.25
  headline:
    fontFamily: 'Outfit, sans-serif'
    fontSize: '1.5rem'
    fontWeight: 600
    lineHeight: 1.3
  title:
    fontFamily: 'Outfit, sans-serif'
    fontSize: '1.125rem'
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: 'Outfit, sans-serif'
    fontSize: '1rem'
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: 'Outfit, sans-serif'
    fontSize: '0.875rem'
    fontWeight: 500
    lineHeight: 1.5
rounded:
  md: '6px'
  lg: '8px'
  full: '999px'
spacing:
  sm: '8px'
  md: '16px'
  lg: '24px'
components:
  button-primary:
    backgroundColor: '{colors.action-blue}'
    textColor: '{colors.paper}'
    rounded: '{rounded.md}'
    padding: '8px 16px'
    typography: '{typography.label}'
  button-primary-hover:
    backgroundColor: '{colors.action-blue-deep}'
  button-secondary:
    backgroundColor: '{colors.hairline}'
    textColor: '{colors.ink}'
    rounded: '{rounded.md}'
    padding: '8px 16px'
  button-danger:
    backgroundColor: '{colors.danger-red}'
    textColor: '{colors.paper}'
    rounded: '{rounded.md}'
    padding: '8px 16px'
  input-field:
    backgroundColor: '{colors.mist}'
    textColor: '{colors.ink}'
    rounded: '{rounded.md}'
    padding: '8px 12px'
  card-bordered:
    backgroundColor: '{colors.paper}'
    textColor: '{colors.ink}'
    rounded: '{rounded.lg}'
    padding: '16px'
---

# Design System: PromptVault

## Overview

**Creative North Star: "The Quiet Archive"**

PromptVault looks like a well-kept library: flat, legible, and unhurried. Content leads. Chrome recedes. One blue marks what you can act on, and everything else stays in gray and white (or their night equivalents). It is an Operate surface, used daily by people who may not be technical, so scanability and predictability beat expression.

The system is Tailwind v4 utilities over a small set of tokens: one humanist sans (Outfit), two corner radii, hairline borders, tonal fills. Surfaces are flat. Depth is reserved for things that float above the page. Dark mode follows the OS preference and swaps surfaces for a gray-900/800/700 stack without changing the structure.

**Key Characteristics:**

- Flat surfaces separated by hairline borders and tonal fills, not shadows.
- One action color (blue); green marks skills and success, amber marks secondary emphasis and warnings.
- One typeface in five weights; hierarchy comes from size and weight.
- Visible, high-contrast keyboard focus everywhere.
- Light and dark parity, driven by `prefers-color-scheme` and a `.dark` class.

## Colors

A restrained blue-on-neutral palette. Blue is rare and means "act here"; the rest is a cool gray ladder.

### Primary

- **Action Blue** (#1d4ed8, Tailwind blue-700): primary buttons, active nav items, selected states. The accessible step, chosen over the config's brighter primary-500 (#3b82f6) for white-text contrast.
- **Deep Action Blue** (#1e40af): hover for Action Blue.
- **Link Navy** (#1e3a8a): default link and skip-link color; darkens to #1e40af on hover.
- **Tint Blue** (#eff6ff): the "colored" card background and light selected rows.
- **Focus Blue** (#4a90e2): the 3px keyboard focus outline on all interactive elements.

### Secondary

- **Skill Green** (#10b981 with #059669 and #047857 steps): success states (`secondary-*` tokens).
- **Skill Purple** (purple-100/800, purple-900/100 at night): the identity of skills, used only on the type badge.

### Tertiary

- **Amber Action** (#b45309, hover #92400e): the accent button and warning text; warning text is forced to #854d0e (light) or #fcd34d (dark) for contrast.
- **Danger Red** (#b91c1c in light, #fca5a5 in dark for text; red-500/600 fills for danger buttons): destructive actions and errors.

### Neutral

- **Paper** (#ffffff): page and card background in light mode.
- **Ink** (#111827): body text.
- **Mist** (#f3f4f6): input fills, muted surfaces, secondary hover.
- **Hairline** (#e5e7eb): borders, dividers, secondary button fill.
- **Stone** (#6b7280): secondary and helper text.
- **Night Page** (#111827), **Night Surface** (#1f2937), **Night Field** (#374151): the dark-mode page, card/modal, and input steps (Tailwind `dark:bg-gray-900/800/700`).

### Named Rules

**The One Voice Rule.** Blue means action. Do not use blue as decoration, as a section color, or for large fills outside primary buttons and active states.

**The Contrast Floor Rule.** Text and interactive boundaries meet WCAG 2.1 AA (4.5:1 text, 3:1 UI). Reach for the 700 step on light backgrounds, not the 500 step.

## Typography

**Display Font:** Outfit (with sans-serif fallback)
**Body Font:** Outfit
**Label/Mono Font:** Outfit; code and skill file contents use the browser monospace stack.

**Character:** A rounded geometric sans that stays friendly without being playful. One family keeps the interface quiet; weight and size do the work.

### Hierarchy

- **Display** (700, 32px / 2rem, 1.25): page titles.
- **Headline** (600, 24px / 1.5rem, 1.3): section headings and modal titles.
- **Title** (600, fluid 17 to 18px, 1.4): prompt-card titles (`.text-prompt-title`).
- **Body** (400, 16px, 1.5): descriptions, form text, prompt content. Prompt-card body runs fluid 15 to 14px.
- **Label** (500, 14px, 1.5): buttons, nav items, field labels, chips.

### Named Rules

**The Single Family Rule.** Outfit only. Never introduce a second typeface for emphasis.

**The 16px Input Rule.** Form controls stay at 16px so mobile browsers do not zoom on focus.

## Layout

A mobile-first responsive layout on Tailwind's default breakpoints (`sm` 640, `md` 768, `lg` 1024, `xl` 1280). The main view is a filter sidebar beside a responsive card grid of prompts and skills, collapsing to a single column on small screens. Spacing is the 4px Tailwind scale; components use 8, 12, 16 and 24px steps. Tables and list pages are dense and left-aligned; modals are centered with a capped height (`max-h-[90vh]`) and scrolling body.

## Elevation & Depth

Flat by default. Cards, inputs and panels are separated by hairline borders and tonal fills (white on mist, or gray-800 on gray-900 at night). The theme config sets `shadow` to none, and flat is the baseline. Shadows appear only on overlays that float above the page: modals (`shadow-lg`), menus and popovers (`shadow-xl`/`shadow-lg`). A scrim (`bg-black/50`) sits behind modals. The "elevated" card variant exists but is the exception.

### Named Rules

**The Overlay-Only Shadow Rule.** A shadow means "this sits above the page." Do not put shadows on resting cards, inputs, or buttons.

## Shapes

Gently rounded, never pill-shaped except for status chips. Controls (buttons, inputs, tabs, menu items) use 6px (`rounded-md`); containers (cards, modals, panels) use 8px (`rounded-lg`); chips and avatars use full rounding (999px). Borders are 1px hairline on containers and 2px on text fields, which also carry the validation color.

## Components

Quiet and predictable: each control looks the same wherever it appears.

### Buttons

- **Shape:** gently rounded (6px).
- **Primary:** Action Blue fill, white text, 8px by 16px padding (md), medium weight.
- **Secondary:** Hairline-gray fill with Ink text; outline variant is transparent with a gray-300 border.
- **Accent / Danger:** Amber Action and Danger Red fills with white text.
- **Hover / Focus:** a darker fill on hover and a slight scale-up (105%); keyboard focus shows a 2px ring with a 2px offset (blue-700, red for danger). Disabled drops to 50% opacity with no hover effect.

### Chips

- **Style:** small, fully rounded tag chips for prompt tags and categories; selected chips take the Tint Blue fill.

### Cards / Containers

- **Corner Style:** 8px.
- **Background:** Paper (light) or Night Surface (dark).
- **Shadow Strategy:** none at rest; see Elevation.
- **Border:** 1px Hairline on the bordered variant, which is the default for lists.
- **Internal Padding:** 16px.

### Inputs / Fields

- **Style:** Mist fill, 2px border in the same color, 6px radius, 8px by 12px padding, 16px text.
- **Focus:** the fill turns to white, the border to blue-500, and a 2px ring appears, with the 3px Focus Blue outline for keyboard focus.
- **Error / Disabled:** error fields use a red-50 fill and red-500 border; valid fields use green. Read-only fields use gray-50 and a default cursor. Never rely on color alone: errors also carry text.

### Header

- **Style:** neutral band (Paper, or Night Surface at night) with a hairline bottom border. Blue appears only on the primary "New" button. Secondary links, Profile and Logout are gray secondary buttons. The logo carries no shadow.

### Navigation

- **Style:** tabs use a 2px bottom border: blue-500 with blue-600 text when active, transparent with gray-600 text otherwise (gray-300 border on hover). Side and menu items use 6px radius, Action Blue fill with white text when active, gray-100 on hover.
- **Mobile:** the filter sidebar collapses; the header nav collapses to a "More" menu.

### Modal

- **Style:** centered 8px-radius panel on a 50% black scrim, shadow-lg, close control top right with a visible focus ring.

## Do's and Don'ts

### Do:

- **Do** use Action Blue (#1d4ed8) for the single primary action in a view.
- **Do** keep surfaces flat; separate them with hairline borders and tonal fills.
- **Do** use `focus-visible` styling and the 3px Focus Blue outline on every interactive element.
- **Do** ship every new UI string through i18n and check it in light and dark mode.
- **Do** reuse the components in `src/web/static/ts/components/` before writing new markup.

### Don't:

- **Don't** add shadows to resting cards, inputs or buttons.
- **Don't** use primary-500 blue (#3b82f6) for white-on-blue text; it misses contrast.
- **Don't** introduce a second typeface or a new accent hue.
- **Don't** use custom CSS where a Tailwind utility exists.
- **Don't** signal state with color alone.
