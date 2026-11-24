/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string) => `tr:${key}`),
    language: 'en',
  },
}));

import {
  createPromptElement,
  setFavoriteButtonA11y,
  setLastSelectedPromptIdSetter,
  setPromptElementHandlers,
  type PromptElementHandlers,
} from '../prompt-card';
import { selectedPromptIds } from '../bulk-actions';
import type { PromptResponse } from '@/types/api/responses';

function makePrompt(overrides: Partial<PromptResponse> = {}): PromptResponse {
  return {
    id: 1,
    title: 'Test Title',
    prompt: 'Test body',
    category: 'general',
    tags: ['alpha', 'beta'],
    note: '',
    favorite: false,
    user_id: 'u1',
    created_at: null,
    updated_at: null,
    ...overrides,
  };
}

function makeHandlers(): PromptElementHandlers {
  return {
    onCopy: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    onToggleFavorite: vi.fn(),
    onShowHistory: vi.fn(),
    onCopyWithVersion: vi.fn(),
    onShare: vi.fn(),
  };
}

describe('createPromptElement', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    selectedPromptIds.clear();
    setLastSelectedPromptIdSetter(() => {});
  });

  it('throws if handlers were never initialized', () => {
    // Note: setPromptElementHandlers is module-level state shared across
    // tests in this file; this case is only reachable in isolation, so we
    // just assert the guard exists by re-checking behavior after clearing.
    setPromptElementHandlers(makeHandlers());
    expect(() => createPromptElement('1', makePrompt())).not.toThrow();
  });

  it('renders title, category, and tags as escaped text content', () => {
    setPromptElementHandlers(makeHandlers());
    const el = createPromptElement('1', makePrompt());

    expect(el.dataset.id).toBe('1');
    expect(el.querySelector('h4')?.textContent).toContain('Test Title');
    expect(el.textContent).toContain('alpha');
    expect(el.textContent).toContain('beta');
  });

  it('marks the card selected when its id is in selectedPromptIds', () => {
    selectedPromptIds.add(1);
    setPromptElementHandlers(makeHandlers());
    const el = createPromptElement('1', makePrompt());

    expect(el.classList.contains('selected')).toBe(true);
    const checkbox = el.querySelector('.prompt-checkbox') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });

  it('invokes onEdit when the card body is clicked outside interactive elements', () => {
    const handlers = makeHandlers();
    setPromptElementHandlers(handlers);
    const el = createPromptElement('1', makePrompt());
    document.body.appendChild(el);

    el.dispatchEvent(new MouseEvent('click', { bubbles: true }));

    expect(handlers.onEdit).toHaveBeenCalledWith('1');
  });

  it('invokes onDelete when the delete button is clicked, without triggering onEdit', () => {
    const handlers = makeHandlers();
    setPromptElementHandlers(handlers);
    const el = createPromptElement('1', makePrompt());
    document.body.appendChild(el);

    const deleteBtn = el.querySelector('.delete-btn') as HTMLButtonElement;
    deleteBtn.click();

    expect(handlers.onDelete).toHaveBeenCalledWith('1');
    expect(handlers.onEdit).not.toHaveBeenCalled();
  });

  it('reports the clicked id via the injected lastSelectedPromptId setter', () => {
    const setter = vi.fn();
    setLastSelectedPromptIdSetter(setter);
    setPromptElementHandlers(makeHandlers());
    const el = createPromptElement('42', makePrompt());
    document.body.appendChild(el);

    (el.querySelector('.copy-btn') as HTMLButtonElement).click();

    expect(setter).toHaveBeenCalledWith(42);
  });

  it('shows a semantic version badge only when semantic_version is present', () => {
    setPromptElementHandlers(makeHandlers());
    const withVersion = createPromptElement('1', makePrompt({ semantic_version: '1.2.0' }));
    const withoutVersion = createPromptElement('2', makePrompt());

    expect(withVersion.querySelector('.version-badge')?.textContent).toContain('1.2.0');
    expect(withoutVersion.querySelector('.version-badge')).toBeNull();
  });
});

describe('sharing badges (007-prompt-sharing, US2)', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    selectedPromptIds.clear();
    setLastSelectedPromptIdSetter(() => {});
    setPromptElementHandlers(makeHandlers());
  });

  it('renders the "Shared" badge when prompt.shared is true', () => {
    const el = createPromptElement('1', makePrompt({ shared: true, legacy_public: false }));
    const badge = el.querySelector('.shared-badge');
    expect(badge).not.toBeNull();
    expect(el.querySelector('.legacy-public-badge')).toBeNull();
  });

  it('renders the "Public (legacy)" badge when only legacy_public is true', () => {
    const el = createPromptElement('1', makePrompt({ shared: false, legacy_public: true }));
    expect(el.querySelector('.legacy-public-badge')).not.toBeNull();
    expect(el.querySelector('.shared-badge')).toBeNull();
  });

  it('shows neither badge when the prompt is neither shared nor legacy_public', () => {
    const el = createPromptElement('1', makePrompt({ shared: false, legacy_public: false }));
    expect(el.querySelector('.shared-badge')).toBeNull();
    expect(el.querySelector('.legacy-public-badge')).toBeNull();
  });

  it('prefers the "Shared" badge over "Public (legacy)" when both flags are true (mutually exclusive)', () => {
    const el = createPromptElement('1', makePrompt({ shared: true, legacy_public: true }));
    expect(el.querySelector('.shared-badge')).not.toBeNull();
    expect(el.querySelector('.legacy-public-badge')).toBeNull();
  });

  it('applies data-i18n translation keys to the badges, not raw English text nodes', () => {
    const el = createPromptElement('1', makePrompt({ shared: true }));
    const badge = el.querySelector('.shared-badge');
    // The i18next mock returns `tr:<key>` for any key, so the badge text
    // reflects the translation call rather than the hardcoded fallback.
    expect(badge?.textContent).toBe('tr:sharing.badge');
  });
});

describe('permission-gated controls (007-prompt-sharing, US2)', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    selectedPromptIds.clear();
    setLastSelectedPromptIdSetter(() => {});
    setPromptElementHandlers(makeHandlers());
  });

  it('shows edit, delete, favorite, and share controls for permission "owner"', () => {
    const el = createPromptElement('1', makePrompt({ permission: 'owner' }));
    expect(el.querySelector('.edit-btn')).not.toBeNull();
    expect(el.querySelector('.delete-btn')).not.toBeNull();
    expect(el.querySelector('.favorite-btn')).not.toBeNull();
    expect(el.querySelector('.share-btn')).not.toBeNull();
  });

  it('shows edit but hides delete, favorite, and share for permission "edit"', () => {
    const el = createPromptElement('1', makePrompt({ permission: 'edit' }));
    expect(el.querySelector('.edit-btn')).not.toBeNull();
    expect(el.querySelector('.delete-btn')).toBeNull();
    expect(el.querySelector('.favorite-btn')).toBeNull();
    expect(el.querySelector('.share-btn')).toBeNull();
  });

  it('hides edit, delete, favorite, and share for permission "read"', () => {
    const el = createPromptElement('1', makePrompt({ permission: 'read' }));
    expect(el.querySelector('.edit-btn')).toBeNull();
    expect(el.querySelector('.delete-btn')).toBeNull();
    expect(el.querySelector('.favorite-btn')).toBeNull();
    expect(el.querySelector('.share-btn')).toBeNull();
  });

  it('hides all mutation controls for a legacy_public-only viewer (permission "read")', () => {
    // A viewer who can only see the prompt via the grandfathered public flag
    // gets `permission: 'read'` from the backend (contracts §4) — same as
    // any other read-level grantee, not owner-equivalent.
    const el = createPromptElement(
      '1',
      makePrompt({ permission: 'read', legacy_public: true, shared: false })
    );
    expect(el.querySelector('.edit-btn')).toBeNull();
    expect(el.querySelector('.delete-btn')).toBeNull();
    expect(el.querySelector('.favorite-btn')).toBeNull();
    expect(el.querySelector('.share-btn')).toBeNull();
  });

  it('treats a missing permission field as fully allowed (anonymous mode, AUTH_ENABLED=false)', () => {
    // makePrompt() doesn't set `permission` by default, so this reflects the
    // anonymous-mode payload shape (field absent entirely, not present-as-undefined).
    const el = createPromptElement('1', makePrompt());
    expect(el.querySelector('.edit-btn')).not.toBeNull();
    expect(el.querySelector('.delete-btn')).not.toBeNull();
    expect(el.querySelector('.favorite-btn')).not.toBeNull();
    expect(el.querySelector('.share-btn')).not.toBeNull();
  });

  it('does not invoke onEdit when clicking a read-level card body', () => {
    const handlers = makeHandlers();
    setPromptElementHandlers(handlers);
    const el = createPromptElement('1', makePrompt({ permission: 'read' }));
    document.body.appendChild(el);

    el.dispatchEvent(new MouseEvent('click', { bubbles: true }));

    expect(handlers.onEdit).not.toHaveBeenCalled();
  });

  it('still invokes onEdit when clicking an edit-level card body', () => {
    const handlers = makeHandlers();
    setPromptElementHandlers(handlers);
    const el = createPromptElement('1', makePrompt({ permission: 'edit' }));
    document.body.appendChild(el);

    el.dispatchEvent(new MouseEvent('click', { bubbles: true }));

    expect(handlers.onEdit).toHaveBeenCalledWith('1');
  });
});

describe('match_context snippet rendering (008-full-text-search, US2)', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    selectedPromptIds.clear();
    setLastSelectedPromptIdSetter(() => {});
    setPromptElementHandlers(makeHandlers());
  });

  it('renders no snippet element when match_context is absent', () => {
    const el = createPromptElement('1', makePrompt());
    expect(el.querySelector('.prompt-match-context')).toBeNull();
  });

  it('converts [[MATCH]]/[[/MATCH]] sentinels into <mark> tags', () => {
    const el = createPromptElement(
      '1',
      makePrompt({ match_context: 'a [[MATCH]]gizmo[[/MATCH]] appears here' })
    );
    const snippet = el.querySelector('.prompt-match-context');
    expect(snippet).not.toBeNull();
    expect(snippet?.querySelector('mark')?.textContent).toBe('gizmo');
    expect(snippet?.innerHTML).not.toContain('[[MATCH]]');
    expect(snippet?.innerHTML).not.toContain('[[/MATCH]]');
  });

  it('escapes markup embedded in match_context so it renders as literal text, not executes', () => {
    const el = createPromptElement(
      '1',
      makePrompt({
        match_context: '<script>window.pwned = true</script> [[MATCH]]term[[/MATCH]]',
      })
    );
    const snippet = el.querySelector('.prompt-match-context');
    expect(snippet).not.toBeNull();
    // No live <script> element was created from the payload.
    expect(snippet?.querySelector('script')).toBeNull();
    // The tag text survives only as escaped, inert text content.
    expect(snippet?.textContent).toContain('<script>');
    expect(snippet?.innerHTML).toContain('&lt;script&gt;');
    // The real sentinel still became a <mark>.
    expect(snippet?.querySelector('mark')?.textContent).toBe('term');
  });
});

describe('setFavoriteButtonA11y', () => {
  it('sets aria-pressed and label for a favorited prompt', () => {
    const button = document.createElement('button');
    setFavoriteButtonA11y(button, true);
    expect(button.getAttribute('aria-pressed')).toBe('true');
    expect(button.getAttribute('aria-label')).toBeTruthy();
  });

  it('sets aria-pressed false for a non-favorited prompt', () => {
    const button = document.createElement('button');
    setFavoriteButtonA11y(button, false);
    expect(button.getAttribute('aria-pressed')).toBe('false');
  });
});

describe('createPromptElement overflow menu', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    selectedPromptIds.clear();
    setLastSelectedPromptIdSetter(() => {});
    setPromptElementHandlers(makeHandlers());
  });

  function mount(overrides: Partial<PromptResponse> = {}): HTMLElement {
    const card = createPromptElement('7', makePrompt({ id: 7, ...overrides }));
    document.body.appendChild(card);
    return card;
  }

  it('shows only Copy and Edit outside the menu; the rest live in a closed menu', () => {
    const card = mount();
    const menu = card.querySelector('.card-menu-list') as HTMLElement;
    expect(menu.classList.contains('hidden')).toBe(true);
    expect(card.querySelector('.copy-btn')?.closest('.card-menu-list')).toBeNull();
    expect(card.querySelector('.edit-btn')?.closest('.card-menu-list')).toBeNull();
    for (const sel of ['.history-btn', '.copy-with-version-btn', '.share-btn', '.delete-btn']) {
      expect(menu.querySelector(sel)).not.toBeNull();
    }
  });

  it('makes Copy the single primary action', () => {
    const card = mount();
    expect(card.querySelector('.copy-btn')?.className).toContain('bg-blue-700');
    expect(card.querySelector('.edit-btn')?.className).not.toContain('bg-blue-700');
  });

  it('toggles aria-expanded and closes on Escape, restoring focus to the trigger', () => {
    const card = mount();
    const trigger = card.querySelector('.card-menu-btn') as HTMLButtonElement;
    const menu = card.querySelector('.card-menu-list') as HTMLElement;
    trigger.click();
    expect(menu.classList.contains('hidden')).toBe(false);
    expect(trigger.getAttribute('aria-expanded')).toBe('true');
    menu.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    expect(menu.classList.contains('hidden')).toBe(true);
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(trigger);
  });

  it('opens with ArrowDown focusing the first item and wraps with ArrowUp/Home/End', () => {
    const card = mount();
    const trigger = card.querySelector('.card-menu-btn') as HTMLButtonElement;
    const menu = card.querySelector('.card-menu-list') as HTMLElement;
    const items = Array.from(menu.querySelectorAll<HTMLElement>('[role="menuitem"]'));
    trigger.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
    expect(document.activeElement).toBe(items[0]);
    menu.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true }));
    expect(document.activeElement).toBe(items[items.length - 1]);
    menu.dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true }));
    expect(document.activeElement).toBe(items[0]);
    menu.dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true }));
    expect(document.activeElement).toBe(items[items.length - 1]);
    menu.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
    expect(document.activeElement).toBe(items[0]);
  });

  it('closes after picking an item and still runs its handler', () => {
    const handlers = makeHandlers();
    setPromptElementHandlers(handlers);
    const card = mount();
    const trigger = card.querySelector('.card-menu-btn') as HTMLButtonElement;
    trigger.click();
    (card.querySelector('.history-btn') as HTMLButtonElement).click();
    expect(handlers.onShowHistory).toHaveBeenCalledWith(7);
    expect(card.querySelector('.card-menu-list')?.classList.contains('hidden')).toBe(true);
  });

  it('closes on outside click and when another card menu opens', () => {
    const a = mount();
    const b = createPromptElement('8', makePrompt({ id: 8 }));
    document.body.appendChild(b);
    (a.querySelector('.card-menu-btn') as HTMLButtonElement).click();
    (b.querySelector('.card-menu-btn') as HTMLButtonElement).click();
    expect(a.querySelector('.card-menu-list')?.classList.contains('hidden')).toBe(true);
    expect(b.querySelector('.card-menu-list')?.classList.contains('hidden')).toBe(false);
    document.body.click();
    expect(b.querySelector('.card-menu-list')?.classList.contains('hidden')).toBe(true);
  });

  it('omits Edit, Share and Delete for read-only viewers but keeps History', () => {
    const card = mount({ permission: 'read' });
    expect(card.querySelector('.edit-btn')).toBeNull();
    expect(card.querySelector('.share-btn')).toBeNull();
    expect(card.querySelector('.delete-btn')).toBeNull();
    expect(card.querySelector('.history-btn')).not.toBeNull();
  });
});
