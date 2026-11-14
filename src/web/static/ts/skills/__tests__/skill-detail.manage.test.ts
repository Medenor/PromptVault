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

describe('edit details', () => {
  async function openEdit(onChanged = vi.fn()): Promise<void> {
    openSkillDetail(7, { initial: skill(), onChanged });
    q('.skill-edit-btn').click();
    await flush();
  }

  it('opens a form prefilled with the current values', async () => {
    await openEdit();
    expect(q<HTMLInputElement>('#skill-edit-title').value).toBe('pdf-tools');
    expect(q<HTMLInputElement>('#skill-edit-category').value).toBe('Docs');
    expect(q<HTMLInputElement>('#skill-edit-tags').value).toBe('pdf');
    expect(q<HTMLTextAreaElement>('#skill-edit-note').value).toBe('my note');
  });

  it('saves only metadata, updates the view and tells the list to refresh', async () => {
    const onChanged = vi.fn();
    updateSkillMock.mockResolvedValue(
      skill({ title: 'Renamed', tags: ['a', 'b'], favorite: true })
    );
    await openEdit(onChanged);

    q<HTMLInputElement>('#skill-edit-title').value = 'Renamed';
    q<HTMLInputElement>('#skill-edit-category').value = '';
    q<HTMLInputElement>('#skill-edit-tags').value = 'a, b , ';
    q<HTMLTextAreaElement>('#skill-edit-note').value = 'new note';
    (q('form input[type="checkbox"]') as HTMLInputElement).checked = true;
    q<HTMLFormElement>('form').dispatchEvent(new Event('submit', { cancelable: true }));
    await flush();

    expect(updateSkillMock).toHaveBeenCalledWith(7, {
      title: 'Renamed',
      category: null,
      tags: ['a', 'b'],
      note: 'new note',
      favorite: true,
    });
    expect(notifyMock).toHaveBeenCalledWith('skills.edit.saved', 'success');
    expect(q('.skill-title').textContent).toContain('Renamed');
    expect(onChanged).toHaveBeenCalledTimes(1);
    expect(document.querySelector('form')).toBeNull();
  });

  it('refuses a blank title without calling the API', async () => {
    await openEdit();
    q<HTMLInputElement>('#skill-edit-title').value = '   ';
    q<HTMLFormElement>('form').dispatchEvent(new Event('submit', { cancelable: true }));
    expect(updateSkillMock).not.toHaveBeenCalled();
    expect(q('.skill-edit-status').textContent).toBe('skills.edit.error');
  });

  it('keeps the form open and shows an error when saving fails', async () => {
    updateSkillMock.mockRejectedValue(new Error('nope'));
    await openEdit();
    q<HTMLFormElement>('form').dispatchEvent(new Event('submit', { cancelable: true }));
    await flush();
    expect(q('.skill-edit-status').textContent).toBe('skills.edit.error');
    expect(document.querySelector('form')).not.toBeNull();
  });

  it('cancels without saving', async () => {
    await openEdit();
    q<HTMLButtonElement>('form button[type="button"]').click();
    expect(document.querySelector('form')).toBeNull();
    expect(updateSkillMock).not.toHaveBeenCalled();
  });
});

describe('replace files', () => {
  it('opens the replace dialog and re-renders with the result', () => {
    const onChanged = vi.fn();
    openSkillDetail(7, { initial: skill(), onChanged });
    q('.skill-replace-btn').click();
    expect(replaceDialogMock).toHaveBeenCalledWith(7, expect.any(Function));

    const done = replaceDialogMock.mock.calls[0]?.[1] as (updated: SkillDetail) => void;
    done(skill({ title: 'after replace' }));
    expect(q('.skill-title').textContent).toContain('after replace');
    expect(onChanged).toHaveBeenCalledTimes(1);
  });
});

describe('delete', () => {
  it('asks for a permanent-deletion confirmation, deletes, and offers no undo', async () => {
    confirmMock.mockResolvedValue(true);
    deleteSkillMock.mockResolvedValue(undefined);
    const onChanged = vi.fn();
    openSkillDetail(7, { initial: skill(), onChanged });
    q('.skill-delete-btn').click();
    await flush();

    expect(confirmMock).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'skills.delete.confirmTitle',
        message: 'skills.delete.confirmPermanent',
        confirmLabel: 'skills.delete.confirmButton',
      })
    );
    expect(deleteSkillMock).toHaveBeenCalledWith(7);
    expect(notifyMock).toHaveBeenCalledTimes(1);
    expect(notifyMock).toHaveBeenCalledWith('skills.delete.success', 'success');
    // No undo action is passed to the notification (FR-023).
    expect(notifyMock.mock.calls[0]).toHaveLength(2);
    expect(document.querySelector('.skill-detail-overlay')).toBeNull();
    expect(onChanged).toHaveBeenCalledTimes(1);
  });

  it('does nothing when the confirmation is declined', async () => {
    confirmMock.mockResolvedValue(false);
    openSkillDetail(7, { initial: skill() });
    q('.skill-delete-btn').click();
    await flush();
    expect(deleteSkillMock).not.toHaveBeenCalled();
    expect(document.querySelector('.skill-detail-overlay')).not.toBeNull();
  });

  it('stays open and reports an error when deleting fails', async () => {
    confirmMock.mockResolvedValue(true);
    deleteSkillMock.mockRejectedValue(new Error('boom'));
    openSkillDetail(7, { initial: skill() });
    q('.skill-delete-btn').click();
    await flush();
    expect(notifyMock).toHaveBeenCalledWith('skills.delete.error', 'error');
    expect(document.querySelector('.skill-detail-overlay')).not.toBeNull();
  });
});
