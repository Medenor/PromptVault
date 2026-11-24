/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({ default: { t: vi.fn((key: string) => key), language: 'en' } }));

const apiGet = vi.fn();
vi.mock('@/utils/api', () => ({ apiGet: (...args: unknown[]) => apiGet(...args) }));
vi.mock('../shared', async (orig) => {
  const actual = await orig<typeof import('../shared')>();
  return { ...actual, reportAppIssue: vi.fn() };
});

import { initLoadErrorRetry, loadPrompts, updateLoadMoreControl } from '../prompt-list';

function mount(): void {
  document.body.innerHTML = `
    <div id="prompts-list"><div id="prompts-skeleton" aria-hidden="true"></div></div>
    <div id="prompts-error-state" role="alert" class="hidden">
      <button id="prompts-retry-btn" type="button">retry</button>
    </div>
    <div id="load-more-container"><button id="load-more-btn" type="button"></button></div>
  `;
}

describe('prompt list load failure', () => {
  beforeEach(() => {
    apiGet.mockReset();
    mount();
    initLoadErrorRetry();
  });

  it('replaces the skeleton with the announced error state when the first load fails', async () => {
    apiGet.mockRejectedValueOnce(new Error('network'));
    await loadPrompts();
    expect(document.getElementById('prompts-skeleton')).toBeNull();
    expect(document.getElementById('prompts-error-state')?.classList.contains('hidden')).toBe(
      false
    );
  });

  it('hides the error state and reloads when Try again is pressed', async () => {
    apiGet.mockRejectedValueOnce(new Error('network'));
    await loadPrompts();
    apiGet.mockResolvedValueOnce({ prompts: {}, has_next: false });
    document.getElementById('prompts-retry-btn')?.click();
    expect(document.getElementById('prompts-error-state')?.classList.contains('hidden')).toBe(true);
    expect(apiGet).toHaveBeenCalledTimes(2);
  });

  it('labels Load More through i18n keys instead of hardcoded English', () => {
    updateLoadMoreControl();
    expect(document.getElementById('load-more-btn')?.textContent).toBe('actions.loadMore');
  });
});
