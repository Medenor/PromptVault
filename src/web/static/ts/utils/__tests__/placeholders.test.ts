/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, expect, it } from 'vitest';
import { detectPlaceholders, substitutePlaceholders } from '../placeholders';

describe('detectPlaceholders', () => {
  it('detects distinct bracket tokens', () => {
    const tokens = detectPlaceholders('Hello [NAME], welcome to [PLACE].');
    expect(tokens).toEqual([
      { raw: '[NAME]', delimiter: 'bracket', label: 'NAME' },
      { raw: '[PLACE]', delimiter: 'bracket', label: 'PLACE' },
    ]);
  });

  it('detects distinct brace tokens', () => {
    const tokens = detectPlaceholders('Hello {NAME}, welcome to {PLACE}.');
    expect(tokens).toEqual([
      { raw: '{NAME}', delimiter: 'brace', label: 'NAME' },
      { raw: '{PLACE}', delimiter: 'brace', label: 'PLACE' },
    ]);
  });

  it('de-duplicates repeated tokens, preserving first-seen order', () => {
    const tokens = detectPlaceholders('[NAME] said hi. Later, [NAME] left. Then [PLACE].');
    expect(tokens).toEqual([
      { raw: '[NAME]', delimiter: 'bracket', label: 'NAME' },
      { raw: '[PLACE]', delimiter: 'bracket', label: 'PLACE' },
    ]);
  });

  it('treats [DURATION] and {DURATION} as distinct tokens', () => {
    const tokens = detectPlaceholders('For [DURATION] or {DURATION}.');
    expect(tokens).toEqual([
      { raw: '[DURATION]', delimiter: 'bracket', label: 'DURATION' },
      { raw: '{DURATION}', delimiter: 'brace', label: 'DURATION' },
    ]);
  });

  it('ignores empty brackets', () => {
    expect(detectPlaceholders('nothing here []')).toEqual([]);
  });

  it('ignores unmatched/unterminated brackets while still matching well-formed spans', () => {
    expect(detectPlaceholders('array[0] and [unterminated')).toEqual([]);
  });

  it('ignores a fully unterminated bracket span', () => {
    expect(detectPlaceholders('[unterminated')).toEqual([]);
  });

  it('does not treat doubled outer brackets as part of the token identity', () => {
    expect(detectPlaceholders('[[XY]]')).toEqual([
      { raw: '[XY]', delimiter: 'bracket', label: 'XY' },
    ]);
  });

  it('ignores multi-line spans', () => {
    expect(detectPlaceholders('[NAME\nSTILL]')).toEqual([]);
  });

  it('ignores lowercase names', () => {
    expect(detectPlaceholders('Say hello to [point] and [titre].')).toEqual([]);
  });

  it('ignores names shorter than 2 characters', () => {
    expect(detectPlaceholders('Check [P] and [N] and {X}.')).toEqual([]);
  });

  it('ignores names with hyphens or slashes', () => {
    expect(detectPlaceholders('Date: [YYYY-MM-DD] and path: [A/B].')).toEqual([]);
  });

  it('accepts names with digits, underscores, and spaces', () => {
    const tokens = detectPlaceholders('[ID_2] and [TYPE OF THING] and {V2}.');
    expect(tokens).toEqual([
      { raw: '[ID_2]', delimiter: 'bracket', label: 'ID_2' },
      { raw: '[TYPE OF THING]', delimiter: 'bracket', label: 'TYPE OF THING' },
      { raw: '{V2}', delimiter: 'brace', label: 'V2' },
    ]);
  });

  it('preserves first-seen order across mixed delimiters', () => {
    const tokens = detectPlaceholders('{BB} then [AA] then {BB} then [AA]');
    expect(tokens).toEqual([
      { raw: '{BB}', delimiter: 'brace', label: 'BB' },
      { raw: '[AA]', delimiter: 'bracket', label: 'AA' },
    ]);
  });

  it('returns empty array for empty content', () => {
    expect(detectPlaceholders('')).toEqual([]);
  });

  it('returns empty array for content with no placeholders', () => {
    expect(detectPlaceholders('just plain text, no tokens here.')).toEqual([]);
  });
});

describe('substitutePlaceholders', () => {
  it('replaces filled tokens everywhere they occur', () => {
    const content = '[NAME] met [NAME] and {PLACE}.';
    const values = new Map([
      ['[NAME]', 'Alice'],
      ['{PLACE}', 'Paris'],
    ]);
    expect(substitutePlaceholders(content, values)).toBe('Alice met Alice and Paris.');
  });

  it('leaves unfilled tokens byte-for-byte unchanged', () => {
    const content = 'Hello [NAME], welcome to [PLACE].';
    const values = new Map([['[NAME]', 'Bob']]);
    expect(substitutePlaceholders(content, values)).toBe('Hello Bob, welcome to [PLACE].');
  });

  it('does not re-expand a filled value containing placeholder-like text', () => {
    const content = 'Use [NAME] here.';
    const values = new Map([['[NAME]', 'literal [NESTED] text']]);
    expect(substitutePlaceholders(content, values)).toBe('Use literal [NESTED] text here.');
  });

  it('returns content unchanged for an empty values map', () => {
    const content = 'Hello [NAME], welcome to {PLACE}.';
    expect(substitutePlaceholders(content, new Map())).toBe(content);
  });

  it('returns content unchanged when no keys match', () => {
    const content = 'Hello [NAME].';
    const values = new Map([['[OTHER]', 'value']]);
    expect(substitutePlaceholders(content, values)).toBe(content);
  });
});
