/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

// Known keys translate to "T:<key>"; unknown keys echo the key, which is how
// the code detects a missing translation and falls back.
const KNOWN = new Set([
  'skills.errors.ENTRY_LINK',
  'skills.errors.ARCHIVE_INVALID',
  'skills.errors.unknown',
  'skills.warnings.name_missing',
  'skills.warnings.no_wrapping_folder',
]);
vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string, options?: Record<string, string>) => {
      if (options?.['entry']) return `Entry: ${options['entry']}`;
      return KNOWN.has(key) ? `T:${key}` : key;
    }),
    language: 'en',
  },
}));

const importMock = vi.fn();
const replaceMock = vi.fn();
vi.mock('../skill-api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../skill-api')>();
  return {
    ...actual,
    importSkill: (...args: unknown[]) => importMock(...args),
    replaceSkillArchive: (...args: unknown[]) => replaceMock(...args),
  };
});

const notifyMock = vi.fn();
vi.mock('@/utils/notifications', () => ({
  showNotification: (...args: unknown[]) => notifyMock(...args),
}));

import { APIRequestError } from '@/utils/api';
import { notifyWarnings, openSkillImportDialog, openSkillReplaceDialog } from '../skill-import';

function zip(name = 'skill.zip'): File {
  return new File(['zip'], name, { type: 'application/zip' });
}

function chooseFile(file: File | null): void {
  const input = document.querySelector<HTMLInputElement>('input[type="file"]') as HTMLInputElement;
  Object.defineProperty(input, 'files', {
    configurable: true,
    value: file ? [file] : [],
  });
}

function submit(): void {
  document
    .querySelector<HTMLFormElement>('form.skill-archive-form')
    ?.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
}

const status = (): HTMLElement => document.querySelector('.skill-archive-status') as HTMLElement;
const flush = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));

const RESULT = { skill: { id: 5, title: 'x' }, warnings: [] as string[] };

beforeEach(() => {
  document.body.innerHTML = '';
  importMock.mockReset();
  replaceMock.mockReset();
  notifyMock.mockReset();
});

describe('openSkillImportDialog', () => {
  it('opens a dialog limited to .zip files with optional metadata fields', () => {
    openSkillImportDialog(vi.fn());
    const input = document.querySelector<HTMLInputElement>('input[type="file"]');
    expect(input?.accept).toContain('.zip');
    expect(document.querySelector('input[name="category"]')).not.toBeNull();
    expect(document.querySelector('input[name="tags"]')).not.toBeNull();
    expect(document.querySelector('[role="dialog"]')).not.toBeNull();
  });

  it('asks for a file before uploading', () => {
    openSkillImportDialog(vi.fn());
    chooseFile(null);
    submit();
    expect(status().textContent).toBe('skills.import.selectFile');
    expect(status().classList.contains('hidden')).toBe(false);
    expect(importMock).not.toHaveBeenCalled();
  });

  it('refuses a file that is not a .zip', () => {
    openSkillImportDialog(vi.fn());
    chooseFile(zip('notes.txt'));
    submit();
    expect(status().textContent).toBe('skills.import.onlyZip');
    expect(importMock).not.toHaveBeenCalled();
  });

  it('uploads with the optional fields and reports success', async () => {
    importMock.mockResolvedValue(RESULT);
    const onDone = vi.fn();
    openSkillImportDialog(onDone);
    chooseFile(zip());
    (document.querySelector('input[name="category"]') as HTMLInputElement).value = ' Docs ';
    (document.querySelector('input[name="tags"]') as HTMLInputElement).value = 'a, b';
    submit();
    await flush();

    expect(importMock).toHaveBeenCalledWith(expect.any(File), 'Docs', 'a, b');
    expect(onDone).toHaveBeenCalledWith(RESULT.skill, []);
    expect(notifyMock).toHaveBeenCalledWith('skills.import.success', 'success');
    expect(document.querySelector('[role="dialog"]')).toBeNull();
  });

  it('shows a progress state and disables the buttons while uploading', async () => {
    let release: (value: unknown) => void = () => {};
    importMock.mockImplementation(() => new Promise((resolve) => (release = resolve)));
    openSkillImportDialog(vi.fn());
    chooseFile(zip());
    submit();

    const submitBtn = document.querySelector<HTMLButtonElement>('button[type="submit"]');
    expect(submitBtn?.disabled).toBe(true);
    expect(submitBtn?.textContent).toBe('skills.import.uploading');
    release(RESULT);
    await flush();
  });

  it('lists the warnings in a non-blocking notice', async () => {
    importMock.mockResolvedValue({ ...RESULT, warnings: ['name_missing', 'no_wrapping_folder'] });
    openSkillImportDialog(vi.fn());
    chooseFile(zip());
    submit();
    await flush();

    const warning = notifyMock.mock.calls.find((call) => call[1] === 'warning');
    expect(warning?.[0]).toContain('skills.import.warningsTitle');
    expect(warning?.[0]).toContain('• T:skills.warnings.name_missing');
    expect(warning?.[0]).toContain('• T:skills.warnings.no_wrapping_folder');
  });

  it('shows a translated rejection and the offending entry as text only', async () => {
    const payload = '<img src=x onerror=alert(1)>';
    importMock.mockRejectedValue(
      new APIRequestError(400, {
        detail: { code: 'ENTRY_LINK', message: 'english', offending_entry: payload },
      } as never)
    );
    const onDone = vi.fn();
    openSkillImportDialog(onDone);
    chooseFile(zip());
    submit();
    await flush();

    expect(status().textContent).toContain('T:skills.errors.ENTRY_LINK');
    expect(status().textContent).toContain(payload);
    expect(status().querySelector('img')).toBeNull();
    expect(onDone).not.toHaveBeenCalled();
    // The dialog stays open and can be retried.
    expect(document.querySelector('[role="dialog"]')).not.toBeNull();
    expect(document.querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled).toBe(
      false
    );
  });

  it('shows the generic message for non-API failures', async () => {
    importMock.mockRejectedValue(new Error('offline'));
    openSkillImportDialog(vi.fn());
    chooseFile(zip());
    submit();
    await flush();
    expect(status().textContent).toContain('T:skills.errors.unknown');
  });

  it('closes on cancel', () => {
    openSkillImportDialog(vi.fn());
    const cancel = document.querySelector<HTMLButtonElement>('button[type="button"].bg-gray-200');
    cancel?.click();
    expect(document.querySelector('[role="dialog"]')).toBeNull();
  });
});

describe('openSkillReplaceDialog', () => {
  it('uploads to the replace endpoint without metadata fields', async () => {
    replaceMock.mockResolvedValue(RESULT);
    const onDone = vi.fn();
    openSkillReplaceDialog(9, onDone);
    expect(document.querySelector('input[name="category"]')).toBeNull();
    chooseFile(zip());
    submit();
    await flush();

    expect(replaceMock).toHaveBeenCalledWith(9, expect.any(File));
    expect(importMock).not.toHaveBeenCalled();
    expect(onDone).toHaveBeenCalledWith(RESULT.skill, []);
    expect(notifyMock).toHaveBeenCalledWith('skills.replace.success', 'success');
  });

  it('shows the rejection and leaves the dialog open', async () => {
    replaceMock.mockRejectedValue(
      new APIRequestError(400, {
        detail: { code: 'ARCHIVE_INVALID', message: 'x', offending_entry: null },
      } as never)
    );
    openSkillReplaceDialog(9, vi.fn());
    chooseFile(zip());
    submit();
    await flush();
    expect(status().textContent).toContain('T:skills.errors.ARCHIVE_INVALID');
  });
});

describe('notifyWarnings', () => {
  it('does nothing without warnings', () => {
    notifyWarnings([]);
    expect(notifyMock).not.toHaveBeenCalled();
  });
});
