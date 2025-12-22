# PromptVault Component Library

This directory contains the TypeScript component library for PromptVault, built with Tailwind CSS and vanilla DOM APIs.

## Overview

The component library provides factory functions for creating reusable UI components with consistent styling based on the PromptVault design system.

## Usage

```typescript
import { createButton, createCard, createInput } from '@components';

// Create a button
const button = createButton('Click me', {
  variant: 'primary',
  size: 'md',
  onClick: () => console.log('Clicked!'),
});

// Create a card
const card = createCard('Content goes here', {
  title: 'Card Title',
  variant: 'bordered',
});

// Create an input
const input = createInput({
  type: 'text',
  placeholder: 'Enter text...',
  required: true,
});
```

## Components

### Button (`button.ts`)
- Factory: `createButton(label, props?)`
- Variants: primary, secondary, accent, ghost, danger
- Sizes: sm, md, lg

### Card (`card.ts`)
- Factory: `createCard(content, props?)`
- Variants: default, bordered, elevated
- Supports title, description, and footer

### Input (`input.ts`)
- Factory: `createInput(props?)`, `createTextarea(props?)`
- Supports all standard HTML input types

### Form (`form.ts`)
- Factory: `createFormGroup(child, props)`, `createSelect(props)`
- Form groups with labels, validation, and help text

### Modal (`modal.ts`)
- Factory: `createModal(content, props?)`
- Utilities: `openModal(modal)`, `closeModal(modal)`
- Sizes: sm, md, lg, xl, full

### Layout (`layout.ts`)
- Factory: `createContainer(content, props?)`, `createFlex(children, props?)`, `createGrid(children, props?)`
- Responsive containers, flexbox, and grid layouts

### Navigation (`navigation.ts`)
- Factory: `createNavbar(props?)`, `createSidebar(props?)`
- Navigation bars and sidebars with item lists

## TypeScript Types

All component props are fully typed. Import types from `@components`:

```typescript
import type { ButtonProps, CardProps, InputProps } from '@components';
```

## Testing

Unit tests are located in `__tests__/`. Run tests with:

```bash
npm run test:unit
```

## Development Status

**Phase 1 (Current)**: Stub implementations with basic Tailwind styling
**Phase 2 (Next)**: Full implementations with complete design system integration
**Phase 3+**: Advanced features, animations, accessibility enhancements

## Design System

Components follow the PromptVault design system:
- **Colors**: Primary (Blue), Secondary (Emerald), Accent (Amber)
- **Typography**: Outfit font family
- **Spacing**: Standard Tailwind scale
- **Design Philosophy**: Flat design (no shadows)

See `tailwind.config.ts` for the complete design token configuration.
