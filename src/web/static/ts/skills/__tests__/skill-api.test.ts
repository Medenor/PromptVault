/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({ default: { t: vi.fn((key: string) => key), language: 'en' } }));

const apiGetMock = vi.fn();
const apiPatchMock = vi.fn();
const apiDeleteMock = vi.fn();
const apiPostFormMock = vi.fn();
const apiPutFormMock = vi.fn();

vi.mock('@/utils/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/utils/api')>();
  return {
    ...actual,
    apiGet: (...args: unknown[]) => apiGetMock(...args),
    apiPatch: (...args: unknown[]) => apiPatchMock(...args),
    apiDelete: (...args: unknown[]) => apiDeleteMock(...args),
    apiPostForm: (...args: unknown[]) => apiPostFormMock(...args),
    apiPutForm: (...args: unknown[]) => apiPutFormMock(...args),
  };
});

import { APIRequestError } from '@/utils/api';
import {
  deleteSkill,
  downloadSkillUrl,
  getSkill,
  getSkillFileContent,
  importSkill,
  isSkillItem,
  replaceSkillArchive,
  skillRawFileUrl,
  toSkillApiError,
  updateSkill,
} from '../skill-api';
import type { PromptResponse, SkillSummary } from '@/types';

beforeEach(() => {
  for (const mock of [apiGetMock, apiPatchMock, apiDeleteMock, apiPostFormMock, apiPutFormMock]) {
    mock.mockReset();
  }
});

function file(): File {
  return new File(['zip'], 'skill.zip', { type: 'application/zip' });
}

describe('importSkill', () => {
  it('posts the archive as multipart form data through apiPostForm', async () => {
    apiPostFormMock.mockResolvedValue({ skill: { id: 1 }, warnings: [] });
    await importSkill(file(), 'Docs', 'a, b');

    expect(apiPostFormMock).toHaveBeenCalledTimes(1);
    const [url, form] = apiPostFormMock.mock.calls[0] as [string, FormData];
    expect(url).toBe('/api/skills/import');
    expect(form).toBeInstanceOf(FormData);
    expect((form.get('archive') as File).name).toBe('skill.zip');
    expect(form.get('category')).toBe('Docs');
    expect(form.get('tags')).toBe('a, b');
  });

  it('omits empty optional fields', async () => {
    apiPostFormMock.mockResolvedValue({});
    await importSkill(file());
    const form = apiPostFormMock.mock.calls[0]?.[1] as FormData;
    expect(form.has('category')).toBe(false);
    expect(form.has('tags')).toBe(false);
  });
});

describe('endpoint helpers', () => {
  it('reads detail and file content', async () => {
    apiGetMock.mockResolvedValue({});
    await getSkill(7);
    await getSkillFileContent(7, 'docs/a b.md');
    expect(apiGetMock).toHaveBeenNthCalledWith(1, '/api/skills/7');
    expect(apiGetMock).toHaveBeenNthCalledWith(
      2,
      '/api/skills/7/files/content?path=docs%2Fa%20b.md'
    );
  });

  it('builds download URLs without calling the API', () => {
    expect(skillRawFileUrl(3, 'a/ü.txt')).toBe('/api/skills/3/files/raw?path=a%2F%C3%BC.txt');
    expect(downloadSkillUrl(3)).toBe('/api/skills/3/download');
    expect(apiGetMock).not.toHaveBeenCalled();
  });

  it('patches, replaces and deletes', async () => {
    apiPatchMock.mockResolvedValue({});
    apiPutFormMock.mockResolvedValue({});
    apiDeleteMock.mockResolvedValue(undefined);
    await updateSkill(4, { title: 'T', category: null });
    await replaceSkillArchive(4, file());
    await deleteSkill(4);
    expect(apiPatchMock).toHaveBeenCalledWith('/api/skills/4', { title: 'T', category: null });
    const [url, form] = apiPutFormMock.mock.calls[0] as [string, FormData];
    expect(url).toBe('/api/skills/4/archive');
    expect(form.get('archive')).toBeInstanceOf(File);
    expect(apiDeleteMock).toHaveBeenCalledWith('/api/skills/4');
  });
});

describe('toSkillApiError', () => {
  it('reads the contract error body', () => {
    const error = new APIRequestError(400, {
      detail: { code: 'ENTRY_LINK', message: 'no links', offending_entry: 'a/link' },
    } as never);
    expect(toSkillApiError(error)).toEqual({
      code: 'ENTRY_LINK',
      message: 'no links',
      offendingEntry: 'a/link',
      status: 400,
    });
  });

  it('keeps a null offending entry', () => {
    const error = new APIRequestError(413, {
      detail: { code: 'LIMIT_UPLOAD_SIZE', message: 'big', offending_entry: null },
    } as never);
    expect(toSkillApiError(error).offendingEntry).toBeNull();
  });

  it('falls back to unknown for other API errors and plain errors', () => {
    expect(toSkillApiError(new APIRequestError(500, { detail: 'boom' })).code).toBe('unknown');
    expect(toSkillApiError(new APIRequestError(422, { detail: [] })).code).toBe('unknown');
    expect(toSkillApiError(new Error('network')).message).toBe('network');
    expect(toSkillApiError('weird')).toMatchObject({
      code: 'unknown',
      message: 'weird',
      status: 0,
    });
  });
});

describe('isSkillItem', () => {
  it('tells skills from prompts', () => {
    const skill = { id: 1, item_type: 'skill' } as SkillSummary;
    const prompt = { id: 2, item_type: 'prompt' } as PromptResponse;
    const legacy = { id: 3 } as PromptResponse;
    expect(isSkillItem(skill)).toBe(true);
    expect(isSkillItem(prompt)).toBe(false);
    expect(isSkillItem(legacy)).toBe(false);
  });
});
