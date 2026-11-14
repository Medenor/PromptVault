/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string, options?: Record<string, string | number>) => {
      if (options && 'count' in options) return `${key}:${String(options['count'])}`;
      if (options && 'size' in options) return `${key}:${String(options['size'])}`;
      return key;
    }),
    language: 'en',
  },
}));

const getSkillMock = vi.fn();
const updateSkillMock = vi.fn();
const deleteSkillMock = vi.fn();
const getContentMock = vi.fn();
vi.mock('../skill-api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../skill-api')>();
  return {
    ...actual,
    getSkill: (...args: unknown[]) => getSkillMock(...args),
    updateSkill: (...args: unknown[]) => updateSkillMock(...args),
    deleteSkill: (...args: unknown[]) => deleteSkillMock(...args),
    getSkillFileContent: (...args: unknown[]) => getContentMock(...args),
  };
});

const replaceDialogMock = vi.fn();
vi.mock('../skill-import', () => ({
  openSkillReplaceDialog: (...args: unknown[]) => replaceDialogMock(...args),
}));

const confirmMock = vi.fn();
vi.mock('@/utils/dialogs', () => ({ confirmAsync: (...args: unknown[]) => confirmMock(...args) }));

const notifyMock = vi.fn();
vi.mock('@/utils/notifications', () => ({
  showNotification: (...args: unknown[]) => notifyMock(...args),
}));

import { openSkillDetail } from '../skill-detail';
import type { SkillDetail } from '../skill-api';

const flush = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));

function skill(overrides: Partial<SkillDetail> = {}): SkillDetail {
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
    note: 'my note',
    instructions_html: '<h1>PDF tools</h1><p>Run <code>${CLAUDE_SKILL_DIR}/x.sh</code></p>',
    files: [
      { path: 'SKILL.md', size: 100, is_text: true, sha256: 'a' },
      { path: 'scripts/fill.py', size: 20, is_text: true, sha256: 'b' },
      { path: 'references/sample.bin', size: 2048, is_text: false, sha256: 'c' },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  document.body.innerHTML = '';
  for (const mock of [
    getSkillMock,
    updateSkillMock,
    deleteSkillMock,
    getContentMock,
    replaceDialogMock,
    confirmMock,
    notifyMock,
  ]) {
    mock.mockReset();
  }
  getContentMock.mockResolvedValue({
    path: 'SKILL.md',
    size: 100,
    is_text: true,
    truncated: false,
    text: '# raw skill text',
  });
});

const q = <T extends Element = HTMLElement>(selector: string): T =>
  document.querySelector(selector) as T;

describe('loading and rendering', () => {
  it('shows a loading state, then the skill', async () => {
    let release: (value: unknown) => void = () => {};
    getSkillMock.mockImplementation(() => new Promise((resolve) => (release = resolve)));
    openSkillDetail(7);
    expect(q('.skill-loading').textContent).toBe('skills.detail.loading');
    release(skill());
    await flush();
    expect(q('.skill-title').textContent).toContain('pdf-tools');
    expect(getSkillMock).toHaveBeenCalledWith(7);
  });

  it('can render an already-fetched skill without a request', () => {
    openSkillDetail(7, { initial: skill() });
    expect(getSkillMock).not.toHaveBeenCalled();
    expect(q('.skill-title').textContent).toContain('pdf-tools');
  });

  it('shows a translated error when the skill cannot be loaded', async () => {
    getSkillMock.mockRejectedValue(new Error('gone'));
    openSkillDetail(7);
    await flush();
    expect(q('.skill-load-error').textContent).toBe('skills.detail.loadError');
    expect(q('.skill-close-btn')).not.toBeNull();
  });

  it('shows the header: title with a Skill badge, description and metadata', () => {
    openSkillDetail(7, { initial: skill() });
    expect(q('.skill-title .type-badge').dataset['itemType']).toBe('skill');
    expect(q('.skill-description').textContent).toBe('Fill PDF forms.');
    const meta = q('.skill-meta').textContent ?? '';
    expect(meta).toContain('pdf-tools');
    expect(meta).toContain('Docs');
    expect(meta).toContain('my note');
    expect(meta).toContain('skills.detail.files:3');
    expect(meta).toContain('skills.detail.totalSize:2 KB');
  });

  it('shows the rendered instructions and keeps placeholders literal', () => {
    openSkillDetail(7, { initial: skill() });
    expect(q('.skill-instructions h1').textContent).toBe('PDF tools');
    expect(q('.skill-instructions').textContent).toContain('${CLAUDE_SKILL_DIR}/x.sh');
  });

  it('lists format warnings when there are any', () => {
    openSkillDetail(7, { initial: skill({ format_warnings: ['name_missing'] }) });
    expect(q('.skill-warnings').textContent).toContain('name_missing');
  });

  it('omits the warnings block when the skill is compliant', () => {
    openSkillDetail(7, { initial: skill() });
    expect(document.querySelector('.skill-warnings')).toBeNull();
  });

  it('renders hostile metadata as text', () => {
    const xss = '<img src=x onerror=alert(1)>';
    openSkillDetail(7, {
      initial: skill({ title: xss, description: xss, category: xss, tags: [xss], note: xss }),
    });
    const panel = q('.skill-detail-panel');
    // Only the server-sanitised instructions may contain elements from data.
    expect(panel.querySelector('img')).toBeNull();
    expect(panel.querySelector('[onerror]')).toBeNull();
    expect(panel.textContent).toContain(xss);
  });
});

describe('files', () => {
  it('shows the tree beside the viewer and opens SKILL.md first', async () => {
    openSkillDetail(7, { initial: skill() });
    await flush();
    const tree = q('[role="tree"]');
    expect(tree.querySelector('[data-path="scripts"]')).not.toBeNull();
    expect(q('.viewer-name').textContent).toBe('SKILL.md');
    expect(q('.viewer-text').textContent).toBe('# raw skill text');
  });

  it('selecting a file in the tree loads it into the viewer', async () => {
    openSkillDetail(7, { initial: skill() });
    await flush();
    getContentMock.mockResolvedValueOnce({
      path: 'scripts/fill.py',
      size: 20,
      is_text: true,
      truncated: false,
      text: 'echo hi',
    });
    q('[data-path="scripts"] .tree-row').click(); // expand
    q('[data-path="scripts/fill.py"] .tree-row').click();
    await flush();
    expect(q('.viewer-name').textContent).toBe('scripts/fill.py');
    expect(getContentMock).toHaveBeenLastCalledWith(7, 'scripts/fill.py');
  });

  it('shows text from a file with markup-shaped content as plain text', async () => {
    getContentMock.mockResolvedValue({
      path: 'SKILL.md',
      size: 100,
      is_text: true,
      truncated: false,
      text: '<script>alert(1)</script>',
    });
    openSkillDetail(7, { initial: skill() });
    await flush();
    expect(q('.viewer-text').textContent).toBe('<script>alert(1)</script>');
    expect(q('.skill-detail-panel').querySelector('script')).toBeNull();
  });

  it('shows size and a download link for a binary file instead of text', async () => {
    openSkillDetail(7, { initial: skill() });
    await flush();
    q('[data-path="references"] .tree-row').click();
    q('[data-path="references/sample.bin"] .tree-row').click();
    await flush();
    expect(q('.viewer-name').textContent).toBe('references/sample.bin');
    expect(q('.viewer-size').textContent).toBe('skills.viewer.size:2 KB');
    expect(q<HTMLAnchorElement>('a.viewer-download').getAttribute('href')).toBe(
      '/api/skills/7/files/raw?path=references%2Fsample.bin'
    );
  });
});

describe('download and closing', () => {
  it('offers the whole skill as a plain download link', () => {
    openSkillDetail(7, { initial: skill() });
    const link = q<HTMLAnchorElement>('a.skill-download-btn');
    expect(link.getAttribute('href')).toBe('/api/skills/7/download');
    expect(link.hasAttribute('download')).toBe(true);
    expect(link.getAttribute('aria-label')).toBe('skills.download.aria');
  });

  it('is a modal dialog labelled by the title', () => {
    openSkillDetail(7, { initial: skill() });
    const dialog = q('.skill-detail-overlay');
    expect(dialog.getAttribute('role')).toBe('dialog');
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(dialog.getAttribute('aria-labelledby')).toBe(q('.skill-title').id);
  });

  it('closes from the button and returns focus', () => {
    const trigger = document.createElement('button');
    document.body.appendChild(trigger);
    trigger.focus();
    openSkillDetail(7, { initial: skill() });
    q('.skill-close-btn').click();
    expect(document.querySelector('.skill-detail-overlay')).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it('closes on Escape', () => {
    openSkillDetail(7, { initial: skill() });
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    expect(document.querySelector('.skill-detail-overlay')).toBeNull();
  });

  it('close() is idempotent', () => {
    const handle = openSkillDetail(7, { initial: skill() });
    handle.close();
    expect(() => handle.close()).not.toThrow();
  });
});
