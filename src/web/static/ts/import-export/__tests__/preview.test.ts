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

import { generateExportPreview, generateImportPreview, hidePreview, showPreview } from '../preview';

describe('generateExportPreview', () => {
  const prompts = { '1': {}, '2': {}, '3': {} };

  it('renders CSV sample rows with remaining count', () => {
    const content = generateExportPreview(prompts, 'csv');
    expect(content).toContain('Title,Prompt,Category,Tags,Favorite');
    expect(content).toContain('and 1 more prompts');
  });

  it('renders markdown sample sections', () => {
    const content = generateExportPreview(prompts, 'markdown');
    expect(content).toContain('# Example Prompt 1');
    expect(content).toContain('and 1 more prompts');
  });

  it('renders JSON sample payload', () => {
    const content = generateExportPreview(prompts, 'json');
    expect(content).toContain('"total_prompts": 3');
    expect(content).toContain('and 1 more prompts');
  });

  it('returns empty string for an unknown format', () => {
    expect(generateExportPreview(prompts, 'xml')).toBe('');
  });
});

describe('generateImportPreview', () => {
  it('produces a CSV-flavored preview for .csv files', async () => {
    const content = await generateImportPreview('data.csv');
    expect(content).toContain('CSV Preview');
  });

  it('produces a JSON-flavored preview for .json files', async () => {
    const content = await generateImportPreview('data.json');
    expect(content).toContain('JSON Preview');
  });

  it('falls back to markdown preview for other extensions', async () => {
    const content = await generateImportPreview('data.md');
    expect(content).toContain('Markdown Preview');
  });
});

describe('showPreview / hidePreview', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="preview-panel" class="hidden"></div>
      <div id="preview-content"></div>
      <button id="confirm-btn"></button>
    `;
  });

  it('reveals the panel, sets content, and labels the confirm button for export', () => {
    showPreview('export', 'preview text');
    expect(document.getElementById('preview-panel')?.classList.contains('hidden')).toBe(false);
    expect(document.getElementById('preview-content')?.textContent).toBe('preview text');
    expect(document.getElementById('confirm-btn')?.textContent).toBe('importExport.exportBtn');
  });

  it('labels the confirm button for import', () => {
    showPreview('import', 'preview text');
    expect(document.getElementById('confirm-btn')?.textContent).toBe('importExport.importBtn');
  });

  it('hides the preview panel', () => {
    showPreview('export', 'x');
    hidePreview();
    expect(document.getElementById('preview-panel')?.classList.contains('hidden')).toBe(true);
  });
});
