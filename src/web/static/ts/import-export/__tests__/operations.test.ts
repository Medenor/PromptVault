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

import { loadStatistics, normalizeExportFilename, showProgress, showStatus } from '../operations';

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

  it('leaves an already-extensioned filename untouched', () => {
    expect(normalizeExportFilename('my-export.json', 'csv')).toBe('my-export.json');
  });

  it('appends the format extension when missing', () => {
    expect(normalizeExportFilename('my-export', 'md')).toBe('my-export.md');
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
