# Frontend Conventions

## TypeScript

The entire frontend is TypeScript (`noImplicitAny: true`). Legacy JavaScript files are preserved but not modified.

- **Explicit types** on function parameters and return types:

  ```typescript
  function getUserSessions(userId: number): Promise<SessionResponse[]> {
    return fetch(`/api/sessions/${userId}`).then((r) => r.json());
  }
  ```

- Use `TranslationKey` for i18n keys (compile-time validation); use `tUnsafe()` only for dynamic keys (e.g. `data-i18n` attributes).
- Union types for state: `type NotificationType = 'info' | 'success' | 'warning' | 'error'`.
- Export interfaces from service modules for reuse:

  ```typescript
  // services/api.ts
  export interface SessionResponse {
    id: string;
    family_id: string;
    user_agent: string;
    ip_address: string;
    is_current: boolean;
    created_at: string;
    last_used_at: string;
    expires_at: string;
  }
  ```

- Async/await with error handling and generics:

  ```typescript
  async function importData<T>(file: File): Promise<ImportResult<T>> {
    try {
      const data = await parseFile(file);
      return { success: true, data };
    } catch (error) {
      reportError('import', 'parse', error);
      throw error;
    }
  }
  ```

- DOM queries with type casting: `document.getElementById('modal') as HTMLDivElement`.
- Every `.ts` file has a corresponding `.test.ts` file (Vitest, `vi.mock()` for external deps, 85%+ coverage per module).
- Translation keys live in `src/web/static/locales/*.json` (TypeScript keys inferred from `en.json`).

## Component System

Located in [`src/web/static/ts/components/`](../../src/web/static/ts/components/): `Button.ts`, `Card.ts`, `Input.ts`, `Form.ts`, `Modal.ts`, `Layout.ts`, `Navigation.ts`.

Pattern for new components:

```typescript
// src/web/static/ts/components/MyComponent.ts

export interface MyComponentProps {
  title: string;
  onClick?: (event: MouseEvent) => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
  className?: string;
}

export function MyComponent(props: MyComponentProps): HTMLElement {
  const container = document.createElement('div');
  container.className = `
    flex items-center justify-between
    bg-white p-4 rounded-lg shadow-md
    ${props.disabled ? 'opacity-50 cursor-not-allowed' : ''}
    ${props.className || ''}
  `
    .trim()
    .replace(/\s+/g, ' ');

  const title = document.createElement('h3');
  title.className = 'text-lg font-semibold text-gray-900';
  title.textContent = props.title;

  if (props.onClick) {
    container.addEventListener('click', props.onClick);
  }

  container.appendChild(title);
  return container;
}
```

Rules:

1. Always export both the Props interface and the component function.
2. Tailwind utilities only — no custom CSS.
3. Callbacks as optional typed props (`onClick?: (event: MouseEvent) => void`), attached via `addEventListener()`.
4. Include ARIA attributes where appropriate (`setAttribute('aria-label', ...)`, `setAttribute('role', 'button')`).
5. Design for testability — simple, separated logic, predictable class names, exported interfaces.

Usage:

```typescript
import { Button, type ButtonProps } from '@/components/Button';

const button = Button({
  title: 'Submit',
  onClick: (e) => console.log('Clicked'),
  variant: 'primary',
  className: 'mt-4',
});

document.body.appendChild(button);
```

Test pattern (`src/web/static/ts/components/__tests__/MyComponent.test.ts`):

```typescript
import { describe, it, expect, vi } from 'vitest';
import { MyComponent, type MyComponentProps } from '@/components/MyComponent';

describe('MyComponent', () => {
  it('renders with provided title', () => {
    const element = MyComponent({ title: 'Test Title' });
    expect(element.textContent).toContain('Test Title');
  });

  it('calls onClick handler when clicked', () => {
    const onClick = vi.fn();
    const element = MyComponent({ title: 'Test', onClick });
    element.click();
    expect(onClick).toHaveBeenCalled();
  });

  it('applies Tailwind classes correctly', () => {
    const element = MyComponent({ title: 'Test' });
    expect(element.className).toContain('flex');
    expect(element.className).toContain('bg-white');
  });
});
```

Avoid: `innerHTML` (XSS), custom CSS classes, untyped props, hardcoded UI strings (use i18n).

## HTML/Jinja2

- Semantic HTML5 elements, ARIA labels, proper form structure.
- Use Jinja2 template inheritance for consistency.
- `{{ variable }}` for safe HTML escaping.

## CSS — Tailwind v4

Tailwind utility classes only; no custom CSS unless truly unavoidable (animation `@keyframes`, or a layout that can't be done in flexbox/grid — document why if you add any).

```html
<!-- Good -->
<div class="flex items-center justify-between bg-white p-4 rounded-lg shadow-md">
  <h2 class="text-lg font-semibold text-gray-900">Title</h2>
  <button class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded">Action</button>
</div>
```

- Mobile-first breakpoints: `sm`, `md`, `lg`, `xl`, `2xl`.
- Design tokens in [`tailwind.config.ts`](../../tailwind.config.ts) (colors, spacing, fonts as CSS variables).
- Global styles in [`tailwind-globals.css`](../../src/web/static/css/tailwind-globals.css) — base element defaults, utility extensions, shared component base classes only. Don't use `@layer components` for one-off styles.
- Semantic colors (`blue`, `red`, `gray`, `green`, `yellow`) plus custom palette in `tailwind.config.ts` if needed; `dark:` prefix for dark mode.
- State variants: `hover:`, `focus-visible:` (keyboard-only focus), `active:`, `disabled:`, `group-hover:`.
- Reuse components in [`static/ts/components/`](../../src/web/static/ts/components/) before writing new markup.
- Never use inline `style="..."` or custom classes for simple styling.

## Internationalization

- All UI strings use i18next translation keys.
- Languages: English (en), French (fr), Spanish (es), German (de).
- Files: JSON in [`src/web/static/locales/`](../../src/web/static/locales/).
- Users can switch language without restarting.

## Service Worker cache versioning

- [`src/web/static/ts/sw.ts`](../../src/web/static/ts/sw.ts) caches everything under `/static/`
  (including locale files) cache-first, keyed only by the `CACHE_VERSION` constant. A browser with
  an already-installed Service Worker keeps serving old cached assets indefinitely until that
  constant changes — there is no other invalidation signal.
- Any change under `src/web/static/` (locales, CSS, JS, images) must bump `CACHE_VERSION` in the
  same change. `make lint` / CI enforce this via the `check-sw-cache-version` target (Codeberg #74).
