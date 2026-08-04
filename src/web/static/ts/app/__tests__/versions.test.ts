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

const apiGetMock = vi.fn();
const apiPostFormMock = vi.fn();
vi.mock('@/utils/api', () => ({
  apiGet: (...args: unknown[]) => apiGetMock(...args),
  apiPostForm: (...args: unknown[]) => apiPostFormMock(...args),
}));

const showNotificationMock = vi.fn();
vi.mock('@/utils/notifications', () => ({
  showNotification: (...args: unknown[]) => showNotificationMock(...args),
}));

import {
  clearVersionCache,
  hideVersionHistoryModal,
  selectVersionForComparison,
  setVersionRefreshCallbacks,
  showDiffModal,
  showRevertConfirmation,
  showVersionHistoryModal,
  type VersionRefreshCallbacks,
} from '../versions';
import type { VersionHistoryResponse, VersionSummary } from '../types';

function makeVersion(overrides: Partial<VersionSummary> = {}): VersionSummary {
  return {
    version_id: 'v1',
    version_number: 1,
    timestamp: '2026-01-01T00:00:00.000Z',
    author: 'tester',
    message: 'Initial version',
    parents: [],
    semantic_version: null,
    ...overrides,
  };
}

function baseDom(): void {
  // jsdom doesn't implement matchMedia; versions.ts uses it to detect
  // desktop vs. mobile carousel mode. Report "desktop" so the vertical list
  // path (not the carousel) renders, matching how these tests assert on
  // .version-item elements directly in version-list.
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: true,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })) as unknown as typeof window.matchMedia;

  document.body.innerHTML = `
    <div id="version-history-modal" class="hidden"></div>
    <div id="version-list"></div>
    <input id="version-search" />
    <div id="version-carousel-nav" class="hidden"></div>
    <button id="compare-versions-btn" class="hidden"></button>
    <div id="diff-modal" class="hidden"></div>
    <select id="diff-v1-selector"></select>
    <select id="diff-v2-selector"></select>
    <div id="diff-view"></div>
    <div id="revert-confirmation-modal" class="hidden"></div>
    <button id="confirm-revert-btn"></button>
    <input id="revert-commit-message" />
  `;
}

function makeCallbacks(): VersionRefreshCallbacks {
  return {
    loadPrompts: vi.fn(async () => {}),
    loadAvailableTags: vi.fn(async () => {}),
    loadTags: vi.fn(async () => {}),
  };
}

// showVersionHistoryModal/showRevertConfirmation/showDiffModal read the
// ambient global `event` (set by the browser during real event dispatch) to
// remember which element to return focus to. Simulate that by invoking them
// from inside an actual click handler instead of calling them directly.
function invokeFromClick(trigger: HTMLElement, fn: () => void): void {
  trigger.addEventListener('click', fn);
  trigger.dispatchEvent(new MouseEvent('click', { bubbles: true }));
}

describe('showVersionHistoryModal / hideVersionHistoryModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    baseDom();
  });

  it('shows the modal and loads version history for the prompt', async () => {
    const response: VersionHistoryResponse = { versions: [makeVersion()] };
    apiGetMock.mockResolvedValueOnce(response);

    invokeFromClick(document.body, () => showVersionHistoryModal(5));
    await Promise.resolve();
    await Promise.resolve();

    expect(document.getElementById('version-history-modal')?.classList.contains('hidden')).toBe(
      false
    );
    expect(apiGetMock).toHaveBeenCalledWith('/api/prompts/5/versions');
    expect(document.querySelectorAll('.version-item').length).toBe(1);
  });

  it('hides the modal on hideVersionHistoryModal', () => {
    invokeFromClick(document.body, () => showVersionHistoryModal(5));
    hideVersionHistoryModal();
    expect(document.getElementById('version-history-modal')?.classList.contains('hidden')).toBe(
      true
    );
  });

  it('renders the empty state when there are no versions', async () => {
    apiGetMock.mockResolvedValueOnce({ versions: [] });

    // Distinct prompt id: versions.ts caches history per-prompt in module
    // state, so reusing id 5 here would hit the previous test's cache entry.
    invokeFromClick(document.body, () => showVersionHistoryModal(6));
    await Promise.resolve();
    await Promise.resolve();

    expect(document.getElementById('version-list')?.textContent).toContain('version.noVersions');
  });
});

describe('selectVersionForComparison', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    baseDom();
  });

  it('toggles selection styling and reveals the compare button once two are selected', async () => {
    apiGetMock.mockResolvedValueOnce({
      versions: [makeVersion({ version_id: 'a' }), makeVersion({ version_id: 'b' })],
    });
    // Distinct prompt id per test — versions.ts caches history by prompt id
    // in module state, shared across all tests in this file.
    invokeFromClick(document.body, () => showVersionHistoryModal(7));
    await Promise.resolve();
    await Promise.resolve();

    selectVersionForComparison('a');
    expect(document.getElementById('compare-versions-btn')?.classList.contains('hidden')).toBe(
      true
    );

    selectVersionForComparison('b');
    expect(document.getElementById('compare-versions-btn')?.classList.contains('hidden')).toBe(
      false
    );
  });
});

describe('showRevertConfirmation / performRevert', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    baseDom();
  });

  it('wires the confirm button to call the revert API and refresh callbacks', async () => {
    const callbacks = makeCallbacks();
    setVersionRefreshCallbacks(callbacks);
    apiGetMock.mockResolvedValueOnce({ versions: [makeVersion()] });
    invokeFromClick(document.body, () => showVersionHistoryModal(5));
    await Promise.resolve();
    await Promise.resolve();

    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
    apiPostFormMock.mockResolvedValueOnce(undefined);
    apiGetMock.mockResolvedValueOnce({ versions: [makeVersion()] });

    invokeFromClick(document.body, () => showRevertConfirmation('v1'));
    expect(document.getElementById('revert-confirmation-modal')?.classList.contains('hidden')).toBe(
      false
    );

    (document.getElementById('confirm-revert-btn') as HTMLButtonElement).click();
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();

    expect(apiPostFormMock).toHaveBeenCalled();
    expect(callbacks.loadPrompts).toHaveBeenCalled();
    expect(callbacks.loadTags).toHaveBeenCalled();
  });
});

describe('showDiffModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    baseDom();
  });

  it('shows an error notification when fewer than two versions are selected', async () => {
    await showDiffModal();
    expect(showNotificationMock).toHaveBeenCalledWith('messages.selectTwoVersions', 'error');
  });
});

describe('clearVersionCache', () => {
  it('does nothing when promptId is null or undefined', () => {
    expect(() => clearVersionCache(null)).not.toThrow();
    expect(() => clearVersionCache(undefined)).not.toThrow();
  });
});
