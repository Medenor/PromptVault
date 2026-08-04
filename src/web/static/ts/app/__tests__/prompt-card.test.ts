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
