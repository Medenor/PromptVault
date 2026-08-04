/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string) => `tr:${key}`),
    language: 'en',
  },
}));

import { renderPrompts } from './prompt-list';
import { setPromptElementHandlers } from './prompt-card';
import type { PromptResponse } from '@/types/api/responses';

const XSS_PAYLOAD = '<img src=x onerror=alert(1)>';

describe('renderPrompts XSS hardening', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="prompts-list"></div>
      <div id="search-results-info"></div>
      <div id="prompts-empty-state"></div>
      <div id="search-empty-state"></div>
    `;

    setPromptElementHandlers({
      onCopy: () => {},
      onEdit: () => {},
      onDelete: () => {},
      onToggleFavorite: () => {},
      onShowHistory: () => {},
      onCopyWithVersion: () => {},
    });

    (window as unknown as { alert?: unknown }).alert = vi.fn();
  });

  it('renders a malicious prompt title without creating an <img> element or executing onerror', () => {
    const prompts: Record<string, PromptResponse> = {
      '1': {
        id: 1,
        title: XSS_PAYLOAD,
        prompt: 'a body',
        category: 'general',
        tags: [XSS_PAYLOAD],
        note: '',
        favorite: false,
        user_id: 'u1',
        created_at: null,
        updated_at: null,
      },
    };

    renderPrompts(prompts);

    const container = document.getElementById('prompts-list');
    expect(container).not.toBeNull();

    // The payload must never materialize as a real <img> element anywhere
    // in the rendered card (title or tag chip) — that would mean the
    // onerror handler executes as soon as the browser tries to load "x".
    expect(container?.querySelector('img')).toBeNull();
    expect((window as unknown as { alert: ReturnType<typeof vi.fn> }).alert).not.toHaveBeenCalled();

    // The escaped text should still be present as literal text content,
    // proving the data made it through — just neutered.
    expect(container?.textContent).toContain(XSS_PAYLOAD);

    // No element anywhere in the card carries an onerror/onload handler,
    // which is what would actually fire the payload.
    expect(container?.querySelector('[onerror], [onload]')).toBeNull();
  });

  it('renders a malicious category without breaking out of its attribute context', () => {
    const prompts: Record<string, PromptResponse> = {
      '1': {
        id: 1,
        title: 'Normal title',
        prompt: 'a body',
        category: `"><img src=x onerror=alert(1)>`,
        tags: [],
        note: '',
        favorite: false,
        user_id: 'u1',
        created_at: null,
        updated_at: null,
      },
    };

    renderPrompts(prompts);

    const container = document.getElementById('prompts-list');
    expect(container?.querySelector('img')).toBeNull();
    expect(container?.querySelector('[onerror], [onload]')).toBeNull();
    // The card must remain a single well-formed element tree: the payload
    // did not close the category <span> early and inject a sibling <img>.
    expect(container?.querySelectorAll('.prompt-item').length).toBe(1);
  });
});
