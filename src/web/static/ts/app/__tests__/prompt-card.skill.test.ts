/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({ default: { t: vi.fn((key: string) => `tr:${key}`), language: 'en' } }));

import { createPromptElement, setPromptElementHandlers } from '../prompt-card';
import type { PromptResponse, SkillSummary } from '@/types';

const XSS = '<img src=x onerror=alert(1)>';

function skill(overrides: Partial<SkillSummary> = {}): SkillSummary {
  return {
    id: 7,
    item_type: 'skill',
    title: 'pdf-tools',
    skill_identifier: 'pdf-tools',
    description: 'Fill PDF forms.',
    category: 'Docs',
    tags: ['pdf'],
    favorite: false,
    file_count: 3,
    total_bytes: 2048,
    format_warnings: [],
    user_id: 'u1',
    created_at: null,
    updated_at: null,
    ...overrides,
  };
}

function prompt(): PromptResponse {
  return {
    id: 1,
    item_type: 'prompt',
    title: 'A prompt',
    prompt: 'Body text',
    category: 'General',
    tags: [],
    note: '',
    favorite: false,
    user_id: 'u1',
    created_at: null,
    updated_at: null,
  };
}

const handlers = {
  onCopy: vi.fn(),
  onEdit: vi.fn(),
  onDelete: vi.fn(),
  onToggleFavorite: vi.fn(),
  onShowHistory: vi.fn(),
  onCopyWithVersion: vi.fn(),
  onShare: vi.fn(),
  onOpenSkill: vi.fn(),
};

beforeEach(() => {
  document.body.innerHTML = '';
  Object.values(handlers).forEach((fn) => fn.mockReset());
  setPromptElementHandlers(handlers);
});

describe('type badge', () => {
  it('marks a skill with a labelled Skill badge', () => {
    const card = createPromptElement('7', skill());
    const badge = card.querySelector<HTMLElement>('.type-badge');
    expect(badge?.dataset['itemType']).toBe('skill');
    expect(badge?.textContent).toBe('tr:skills.badge.skill');
    expect(badge?.getAttribute('aria-label')).toBe('tr:skills.badge.skill');
  });

  it('marks a prompt with a labelled Prompt badge', () => {
    const card = createPromptElement('1', prompt());
    const badge = card.querySelector<HTMLElement>('.type-badge');
    expect(badge?.dataset['itemType']).toBe('prompt');
    expect(badge?.getAttribute('aria-label')).toBe('tr:skills.badge.prompt');
    expect(card.querySelector('.copy-btn')).not.toBeNull(); // prompt actions untouched
  });
});

describe('skill card content', () => {
  it('shows the description, file count and size instead of a prompt body', () => {
    const card = createPromptElement('7', skill());
    expect(card.querySelector('.skill-description')?.textContent).toBe('Fill PDF forms.');
    expect(card.querySelector('.prompt-body-text')).toBeNull();
    expect(card.querySelector('.skill-meta')?.textContent).toContain('tr:skills.detail.files');
    expect(card.querySelector('.skill-meta')?.textContent).toContain('2 KB');
  });

  it('renders hostile values as text, never as elements', () => {
    const card = createPromptElement(
      '7',
      skill({ title: XSS, description: XSS, category: XSS, tags: [XSS] })
    );
    expect(card.querySelector('img')).toBeNull();
    expect(card.querySelector('[onerror]')).toBeNull();
    expect(card.textContent).toContain(XSS);
  });

  it('highlights a search snippet without trusting it as HTML', () => {
    const card = createPromptElement(
      '7',
      skill({ match_context: `before [[MATCH]]${XSS}[[/MATCH]] after` })
    );
    const snippet = card.querySelector('.prompt-match-context');
    expect(snippet?.querySelector('mark')?.textContent).toBe(XSS);
    expect(snippet?.querySelector('img')).toBeNull();
    expect(snippet?.textContent).not.toContain('[[MATCH]]');
  });

  it('flags format warnings', () => {
    const card = createPromptElement('7', skill({ format_warnings: ['name_missing'] }));
    expect(card.querySelector('.skill-warning-flag')).not.toBeNull();
    expect(card.querySelector<HTMLElement>('.skill-warning-flag')?.title).toContain(
      'skills.warnings.name_missing'
    );
  });

  it('falls back to a placeholder when there is no description', () => {
    const card = createPromptElement('7', skill({ description: null }));
    expect(card.querySelector('.skill-description')?.textContent).toBe(
      'tr:skills.detail.noDescription'
    );
  });
});

describe('prompt-only actions are hidden on skills', () => {
  it('has no copy, copy-with-version, history, share or edit buttons', () => {
    const card = createPromptElement('7', skill());
    for (const selector of [
      '.copy-btn',
      '.copy-with-version-btn',
      '.history-btn',
      '.share-btn',
      '.edit-btn',
      '.read-more-btn',
    ]) {
      expect(card.querySelector(selector), selector).toBeNull();
    }
    expect(card.querySelector('.skill-open-btn')).not.toBeNull();
    expect(card.querySelector('.delete-btn')).not.toBeNull();
    expect(card.querySelector('.favorite-btn')).not.toBeNull();
  });

  it('hides favorite and delete for a viewer who is not the owner', () => {
    const card = createPromptElement('7', skill({ permission: 'read' }));
    expect(card.querySelector('.favorite-btn')).toBeNull();
    expect(card.querySelector('.delete-btn')).toBeNull();
    expect(card.querySelector('.skill-open-btn')).not.toBeNull();
  });
});

describe('opening a skill', () => {
  it('opens the detail view from the Open button', () => {
    const card = createPromptElement('7', skill());
    card.querySelector<HTMLButtonElement>('.skill-open-btn')?.click();
    expect(handlers.onOpenSkill).toHaveBeenCalledWith(7);
    expect(handlers.onEdit).not.toHaveBeenCalled();
  });

  it('opens the detail view when the card is clicked, never the prompt editor', () => {
    const card = createPromptElement('7', skill());
    card.click();
    card.querySelector('h4')?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(handlers.onOpenSkill).toHaveBeenCalledTimes(2);
    expect(handlers.onEdit).not.toHaveBeenCalled();
    expect(handlers.onCopy).not.toHaveBeenCalled();
  });

  it('does not open when a checkbox or button inside the card is used', () => {
    const card = createPromptElement('7', skill());
    document.body.appendChild(card);
    card.querySelector<HTMLInputElement>('.prompt-checkbox')?.click();
    card.querySelector<HTMLButtonElement>('.favorite-btn')?.click();
    expect(handlers.onOpenSkill).not.toHaveBeenCalled();
  });

  it('routes favorite and delete to the shared handlers by id', () => {
    const card = createPromptElement('7', skill());
    card.querySelector<HTMLButtonElement>('.favorite-btn')?.click();
    card.querySelector<HTMLButtonElement>('.delete-btn')?.click();
    expect(handlers.onToggleFavorite).toHaveBeenCalledWith('7');
    expect(handlers.onDelete).toHaveBeenCalledWith('7');
  });

  it('does nothing when no skill handler is registered', () => {
    const { onOpenSkill: _unused, ...withoutSkill } = handlers;
    setPromptElementHandlers(withoutSkill);
    const card = createPromptElement('7', skill());
    expect(() => card.click()).not.toThrow();
  });
});
