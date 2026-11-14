/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string, options?: Record<string, string>) =>
      options?.['size'] ? `${key}:${options['size']}` : key
    ),
    language: 'en',
  },
}));

const getContentMock = vi.fn();
vi.mock('../skill-api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../skill-api')>();
  return { ...actual, getSkillFileContent: (...args: unknown[]) => getContentMock(...args) };
});

import { createFileViewer } from '../skill-file-viewer';
import { APIRequestError } from '@/utils/api';
import type { SkillFileEntry } from '../skill-api';

const TEXT: SkillFileEntry = { path: 'docs/a.md', size: 2048, is_text: true, sha256: 'x' };
const BINARY: SkillFileEntry = { path: 'img/logo.png', size: 5, is_text: false, sha256: 'y' };

beforeEach(() => {
  getContentMock.mockReset();
  document.body.innerHTML = '';
});

describe('createFileViewer', () => {
  it('starts on the empty state', () => {
    const viewer = createFileViewer();
    expect(viewer.element.textContent).toBe('skills.viewer.empty');
    expect(viewer.element.getAttribute('aria-live')).toBe('polite');
  });

  it('shows text through textContent so markup stays inert', async () => {
    const payload = '<script>alert(1)</script><img src=x onerror=alert(1)>';
    getContentMock.mockResolvedValue({
      path: TEXT.path,
      size: 2048,
      is_text: true,
      truncated: false,
      text: payload,
    });
    const viewer = createFileViewer();
    document.body.appendChild(viewer.element);
    await viewer.show(7, TEXT);

    const pre = viewer.element.querySelector('pre');
    expect(pre?.textContent).toBe(payload);
    expect(viewer.element.querySelector('script')).toBeNull();
    expect(viewer.element.querySelector('img')).toBeNull();
    expect(viewer.element.querySelector('.viewer-name')?.textContent).toBe('docs/a.md');
    expect(viewer.element.querySelector('.viewer-size')?.textContent).toBe(
      'skills.viewer.size:2 KB'
    );
    expect(viewer.element.querySelector('.viewer-truncated')).toBeNull();
    expect(getContentMock).toHaveBeenCalledWith(7, 'docs/a.md');
  });

  it('offers a download link to the raw bytes', async () => {
    getContentMock.mockResolvedValue({
      path: TEXT.path,
      size: 1,
      is_text: true,
      truncated: false,
      text: 'x',
    });
    const viewer = createFileViewer();
    await viewer.show(7, TEXT);
    const link = viewer.element.querySelector<HTMLAnchorElement>('a.viewer-download');
    expect(link?.getAttribute('href')).toBe('/api/skills/7/files/raw?path=docs%2Fa.md');
    expect(link?.hasAttribute('download')).toBe(true);
  });

  it('warns when the text was truncated', async () => {
    getContentMock.mockResolvedValue({
      path: TEXT.path,
      size: 9_999_999,
      is_text: true,
      truncated: true,
      text: 'partial',
    });
    const viewer = createFileViewer();
    await viewer.show(1, TEXT);
    expect(viewer.element.querySelector('.viewer-truncated')?.textContent).toBe(
      'skills.viewer.truncated'
    );
  });

  it('does not fetch a binary file and shows its size and download link instead', async () => {
    const viewer = createFileViewer();
    await viewer.show(1, BINARY);
    expect(getContentMock).not.toHaveBeenCalled();
    expect(viewer.element.textContent).toContain('skills.viewer.binary');
    expect(viewer.element.querySelector('.viewer-size')?.textContent).toBe(
      'skills.viewer.size:5 B'
    );
    expect(viewer.element.querySelector('a.viewer-download')).not.toBeNull();
    expect(viewer.element.querySelector('pre')).toBeNull();
  });

  it('shows a translated error when loading fails', async () => {
    getContentMock.mockRejectedValue(
      new APIRequestError(404, {
        detail: { code: 'FILE_NOT_FOUND', message: 'x', offending_entry: null },
      } as never)
    );
    const viewer = createFileViewer();
    await viewer.show(1, TEXT);
    expect(viewer.element.querySelector('pre')).toBeNull();
    expect(viewer.element.textContent).toContain('skills.errors.unknown');
  });

  it('ignores a slow response that a newer selection has replaced', async () => {
    let releaseFirst: (value: unknown) => void = () => {};
    getContentMock.mockImplementationOnce(() => new Promise((resolve) => (releaseFirst = resolve)));
    getContentMock.mockResolvedValueOnce({
      path: 'b.md',
      size: 1,
      is_text: true,
      truncated: false,
      text: 'second',
    });
    const viewer = createFileViewer();
    const first = viewer.show(1, TEXT);
    await viewer.show(1, { ...TEXT, path: 'b.md' });
    releaseFirst({ path: TEXT.path, size: 1, is_text: true, truncated: false, text: 'first' });
    await first;
    expect(viewer.element.querySelector('pre')?.textContent).toBe('second');
  });

  it('clear() returns to the empty state and drops pending results', async () => {
    let release: (value: unknown) => void = () => {};
    getContentMock.mockImplementation(() => new Promise((resolve) => (release = resolve)));
    const viewer = createFileViewer();
    const pending = viewer.show(1, TEXT);
    viewer.clear();
    release({ path: 'x', size: 1, is_text: true, truncated: false, text: 'late' });
    await pending;
    expect(viewer.element.textContent).toBe('skills.viewer.empty');
  });
});
