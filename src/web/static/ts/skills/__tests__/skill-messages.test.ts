/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, expect, it, vi } from 'vitest';

const dictionary: Record<string, string> = {
  'skills.errors.ENTRY_LINK': 'Links are not allowed.',
  'skills.errors.unknown': 'Something went wrong.',
  'skills.import.offendingEntry': 'Entry: {{entry}}',
  'skills.warnings.name_missing': 'No name.',
};

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string, options?: Record<string, string>) => {
      const template = dictionary[key] ?? key;
      return template.replace('{{entry}}', options?.['entry'] ?? '');
    }),
    language: 'en',
  },
}));

import { describeSkillError, describeWarnings, formatBytes } from '../skill-messages';

describe('formatBytes', () => {
  it.each([
    [0, '0 B'],
    [512, '512 B'],
    [1536, '1.5 KB'],
    [10 * 1024, '10 KB'],
    [5 * 1024 * 1024, '5 MB'],
    [3 * 1024 ** 3, '3 GB'],
    [-5, '0 B'],
    [Number.NaN, '0 B'],
  ])('%s -> %s', (input, expected) => {
    expect(formatBytes(input)).toBe(expected);
  });
});

describe('describeSkillError', () => {
  it('translates a known code and shows the entry as text', () => {
    const result = describeSkillError({
      code: 'ENTRY_LINK',
      message: 'server text',
      offendingEntry: '<img src=x onerror=alert(1)>',
      status: 400,
    });
    expect(result.message).toBe('Links are not allowed.');
    expect(result.entry).toBe('Entry: <img src=x onerror=alert(1)>');
  });

  it('falls back to the generic message for an unknown code', () => {
    const result = describeSkillError({
      code: 'WHO_KNOWS',
      message: 'server text',
      offendingEntry: null,
      status: 500,
    });
    expect(result.message).toBe('Something went wrong.');
    expect(result.entry).toBeNull();
  });
});

describe('describeWarnings', () => {
  it('translates known codes and keeps unknown ones as-is', () => {
    expect(describeWarnings(['name_missing', 'future_code'])).toEqual(['No name.', 'future_code']);
  });

  it('returns an empty list for no warnings', () => {
    expect(describeWarnings([])).toEqual([]);
  });
});
