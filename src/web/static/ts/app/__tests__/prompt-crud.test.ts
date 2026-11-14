/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string) => key),
    language: 'en',
  },
}));

const apiFetchMock = vi.fn();
const apiGetMock = vi.fn();
vi.mock('@/utils/api', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  apiGet: (...args: unknown[]) => apiGetMock(...args),
}));

const confirmAsyncMock = vi.fn();
vi.mock('@/utils/dialogs', () => ({
  confirmAsync: (...args: unknown[]) => confirmAsyncMock(...args),
}));

const showNotificationMock = vi.fn();
vi.mock('@/utils/notifications', () => ({
  showNotification: (...args: unknown[]) => showNotificationMock(...args),
}));

vi.mock('@components', () => ({
  createModal: vi.fn(() => ({
    element: document.createElement('div'),
    open: vi.fn(),
    close: vi.fn(),
  })),
}));

import {
  copyPrompt,
  deletePrompt,
  editPrompt,
  setPromptEditorRefreshCallbacks,
  toggleFavorite,
  type PromptEditorRefreshCallbacks,
} from '../prompt-crud';
import { promptCache } from '../prompt-list';
import type { PromptResponse } from '@/types/api/responses';

function makeCallbacks(): PromptEditorRefreshCallbacks {
  return {
    isAnyFilterActive: vi.fn(() => false),
    performSearch: vi.fn(async () => {}),
    loadPrompts: vi.fn(async () => {}),
    loadTags: vi.fn(async () => {}),
    setPaginationControlsVisible: vi.fn(),
  };
}

function makePrompt(overrides: Partial<PromptResponse> = {}): PromptResponse {
  return {
    id: 1,
    title: 'Title',
    prompt: 'Body text',
    category: 'general',
    tags: [],
    note: '',
    favorite: false,
    user_id: 'u1',
    created_at: null,
    updated_at: null,
    ...overrides,
  };
}

describe('copyPrompt', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const key of Object.keys(promptCache)) delete promptCache[key];
    document.body.innerHTML = '<button class="copy-btn" data-id="1">Copy</button>';
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn(() => Promise.resolve()) },
    });
  });

  it('uses the cached prompt body without hitting the API', async () => {
    promptCache['1'] = makePrompt({ prompt: 'cached body' });

    await copyPrompt('1');

    expect(apiGetMock).not.toHaveBeenCalled();
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('cached body');
  });

  it('fetches and caches the prompt when not already cached', async () => {
    apiGetMock.mockResolvedValueOnce(makePrompt({ prompt: 'fetched body' }));

    await copyPrompt('1');

    expect(apiGetMock).toHaveBeenCalledWith('/api/prompts/1');
    expect((promptCache['1'] as PromptResponse | undefined)?.prompt).toBe('fetched body');
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('fetched body');
  });

  it('shows copy-failed feedback when the fetch fails', async () => {
    apiGetMock.mockRejectedValueOnce(new Error('network down'));

    await copyPrompt('1');

    const btn = document.querySelector('.copy-btn[data-id="1"]');
    expect(btn?.textContent).toBe('messages.copyFailed');
  });
});

describe('deletePrompt', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
    setPromptEditorRefreshCallbacks(makeCallbacks());
  });

  it('does nothing when the user cancels the confirmation', async () => {
    confirmAsyncMock.mockResolvedValueOnce(false);

    await deletePrompt('1');

    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it('deletes and refreshes the list when confirmed', async () => {
    confirmAsyncMock.mockResolvedValueOnce(true);
    apiFetchMock.mockResolvedValueOnce(undefined);
    const callbacks = makeCallbacks();
    setPromptEditorRefreshCallbacks(callbacks);

    await deletePrompt('1');

    expect(apiFetchMock).toHaveBeenCalledWith('/api/prompts/1', { method: 'DELETE' });
    expect(callbacks.loadPrompts).toHaveBeenCalled();
    expect(callbacks.loadTags).toHaveBeenCalled();
  });

  it('shows an error notification when the delete call fails', async () => {
    confirmAsyncMock.mockResolvedValueOnce(true);
    apiFetchMock.mockRejectedValueOnce(new Error('boom'));

    await deletePrompt('1');

    expect(showNotificationMock).toHaveBeenCalledWith('messages.error', 'error');
  });
});

describe('editPrompt', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const key of Object.keys(promptCache)) delete promptCache[key];
    setPromptEditorRefreshCallbacks(makeCallbacks());
    document.body.innerHTML = `
      <div id="prompt-editor" class="hidden"></div>
      <div id="prompts-list"></div>
      <div id="pull-refresh-toolbar"></div>
      <input id="prompt-title" />
      <textarea id="prompt-content"></textarea>
      <input id="prompt-category" />
      <input id="commit-message" />
      <input id="semantic-version" />
      <form id="prompt-form"></form>
    `;
  });

  it('populates the form fields from the fetched prompt', async () => {
    apiGetMock.mockResolvedValueOnce(
      makePrompt({ title: 'Loaded title', prompt: 'Loaded body', category: 'writing' })
    );

    await editPrompt('7');

    expect((document.getElementById('prompt-title') as HTMLInputElement).value).toBe(
      'Loaded title'
    );
    expect((document.getElementById('prompt-content') as HTMLTextAreaElement).value).toBe(
      'Loaded body'
    );
    const form = document.getElementById('prompt-form') as HTMLFormElement;
    expect(form.dataset.mode).toBe('edit');
    expect(form.dataset.id).toBe('7');
  });
});

describe('toggleFavorite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const key of Object.keys(promptCache)) delete promptCache[key];
    document.body.innerHTML =
      '<button class="favorite-btn" data-id="1" aria-pressed="false">☆</button>';
  });

  it('optimistically flips the star and persists success', async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);
    promptCache['1'] = makePrompt({ favorite: false });

    await toggleFavorite('1');

    const btn = document.querySelector('.favorite-btn[data-id="1"]');
    expect(btn?.textContent).toBe('★');
    expect(promptCache['1']?.favorite).toBe(true);
  });

  it('reverts the optimistic update when the API call fails', async () => {
    apiFetchMock.mockRejectedValueOnce(new Error('failed'));
    promptCache['1'] = makePrompt({ favorite: false });

    await toggleFavorite('1');

    const btn = document.querySelector('.favorite-btn[data-id="1"]');
    expect(btn?.textContent).toBe('☆');
    expect(promptCache['1']?.favorite).toBe(false);
  });
});
