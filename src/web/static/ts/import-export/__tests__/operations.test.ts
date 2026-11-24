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
vi.mock('@/utils/api', () => ({
  apiGet: (...args: unknown[]) => apiGetMock(...args),
  apiPostForm: vi.fn(),
  handleApiError: vi.fn(() => 'error'),
}));

const reportErrorMock = vi.fn();
vi.mock('@/telemetry', () => ({
  reportError: (...args: unknown[]) => reportErrorMock(...args),
}));

import {
  confirmReplaceDestroysShares,
  loadStatistics,
  normalizeExportFilename,
  showProgress,
  showStatus,
} from '../operations';

beforeEach(() => {
  document.body.innerHTML = '';
  apiGetMock.mockReset();
  reportErrorMock.mockClear();
  vi.useRealTimers();
});

describe('normalizeExportFilename', () => {
  it('generates a default filename when none provided', () => {
    expect(normalizeExportFilename('', 'csv')).toBe('promptvault_export.csv');
  });

  it('replaces a mismatched extension with the one matching the format', () => {
    expect(normalizeExportFilename('test.csv', 'json')).toBe('test.json');
  });

  it('keeps a matching extension without duplicating it', () => {
    expect(normalizeExportFilename('my-export.json', 'json')).toBe('my-export.json');
  });

  it('appends the format extension when missing', () => {
    expect(normalizeExportFilename('my-export', 'markdown')).toBe('my-export.md');
  });
});

describe('loadStatistics', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <span id="total-prompts"></span>
      <span id="total-categories"></span>
      <span id="total-tags"></span>
      <span id="favorite-prompts"></span>
      <div id="activity-history"></div>
    `;
  });

  it('populates stat elements from the API response', async () => {
    apiGetMock.mockResolvedValue({
      total_prompts: 5,
      total_categories: 2,
      total_tags: 7,
      favorite_prompts: 1,
    });

    await loadStatistics();

    expect(document.getElementById('total-prompts')?.textContent).toBe('5');
    expect(document.getElementById('total-categories')?.textContent).toBe('2');
    expect(document.getElementById('total-tags')?.textContent).toBe('7');
    expect(document.getElementById('favorite-prompts')?.textContent).toBe('1');
  });

  it('reports errors when the API call fails', async () => {
    apiGetMock.mockRejectedValue(new Error('boom'));
    await loadStatistics();
    expect(reportErrorMock).toHaveBeenCalledWith(
      'importExport',
      'loadStatistics',
      expect.any(Error)
    );
  });
});

describe('confirmReplaceDestroysShares', () => {
  let confirmSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    confirmSpy?.mockRestore();
    confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  it('proceeds without prompting when there are no active shares', async () => {
    apiGetMock.mockResolvedValue({ active_shares_count: 0 });

    const result = await confirmReplaceDestroysShares();

    expect(result).toBe(true);
    expect(confirmSpy).not.toHaveBeenCalled();
  });

  it('prompts with the share count and returns the user choice', async () => {
    apiGetMock.mockResolvedValue({ active_shares_count: 3 });
    confirmSpy.mockReturnValue(true);

    const result = await confirmReplaceDestroysShares();

    expect(result).toBe(true);
    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining('importExport.confirmReplaceWithShares')
    );
  });

  it('returns false when the user declines the confirmation', async () => {
    apiGetMock.mockResolvedValue({ active_shares_count: 2 });
    confirmSpy.mockReturnValue(false);

    const result = await confirmReplaceDestroysShares();

    expect(result).toBe(false);
  });

  it('fails open (returns true) when the stats lookup errors', async () => {
    apiGetMock.mockRejectedValue(new Error('network down'));

    const result = await confirmReplaceDestroysShares();

    expect(result).toBe(true);
    expect(confirmSpy).not.toHaveBeenCalled();
    expect(reportErrorMock).toHaveBeenCalledWith(
      'importExport',
      'confirmReplaceDestroysShares',
      expect.any(Error)
    );
  });
});

describe('showProgress / showStatus', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="export-progress" class="hidden"></div>
      <div id="export-status"></div>
      <div id="export-progress-fill"></div>
    `;
  });

  it('reveals progress and sets width/status text', () => {
    showProgress('export', 'exportProgress');
    expect(document.getElementById('export-progress')?.classList.contains('hidden')).toBe(false);
    expect((document.getElementById('export-progress-fill') as HTMLElement).style.width).toBe(
      '50%'
    );
  });

  it('shows success status and auto-clears after a delay', () => {
    vi.useFakeTimers();
    showStatus('export', 'Done!', 'success');
    const statusEl = document.getElementById('export-status');
    expect(statusEl?.textContent).toBe('Done!');
    expect(statusEl?.className).toContain('text-green-600');

    vi.advanceTimersByTime(3000);
    expect(statusEl?.textContent).toBe('');
    vi.useRealTimers();
  });

  it('shows error status without auto-clearing', () => {
    showStatus('export', 'Failed', 'error');
    const statusEl = document.getElementById('export-status');
    expect(statusEl?.textContent).toBe('Failed');
    expect(statusEl?.className).toContain('text-red-600');
  });
});
