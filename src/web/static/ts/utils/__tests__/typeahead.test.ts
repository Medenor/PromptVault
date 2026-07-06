/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createTypeahead } from '../typeahead';

describe('createTypeahead', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts with empty query', () => {
    const t = createTypeahead();
    expect(t.getQuery()).toBe('');
  });

  it('pushKey accumulates characters', () => {
    const t = createTypeahead();
    t.pushKey('h');
    t.pushKey('e');
    const result = t.pushKey('l');
    expect(result).toBe('hel');
    expect(t.getQuery()).toBe('hel');
  });

  it('normalizes keys to lowercase', () => {
    const t = createTypeahead();
    t.pushKey('H');
    t.pushKey('E');
    expect(t.getQuery()).toBe('he');
  });

  it('ignores whitespace-only keys', () => {
    const t = createTypeahead();
    t.pushKey(' ');
    expect(t.getQuery()).toBe('');
  });

  it('resets buffer after timeout', () => {
    const t = createTypeahead(500);
    t.pushKey('a');
    vi.advanceTimersByTime(600);
    t.pushKey('b');
    expect(t.getQuery()).toBe('b');
  });

  it('cycling: same single character repeats do not grow buffer', () => {
    const t = createTypeahead();
    t.pushKey('a');
    t.pushKey('a');
    expect(t.getQuery()).toBe('a');
  });

  it('reset clears buffer', () => {
    const t = createTypeahead();
    t.pushKey('a');
    t.pushKey('b');
    t.reset();
    expect(t.getQuery()).toBe('');
  });

  it('pushText sets buffer to normalized text', () => {
    const t = createTypeahead();
    t.pushKey('x');
    const result = t.pushText('Hello');
    expect(result).toBe('hello');
    expect(t.getQuery()).toBe('hello');
  });

  it('pushText ignores empty text', () => {
    const t = createTypeahead();
    t.pushKey('a');
    t.pushText('  ');
    expect(t.getQuery()).toBe('a');
  });

  it('subsequent pushKey after pushText appends', () => {
    const t = createTypeahead();
    t.pushText('he');
    t.pushKey('l');
    expect(t.getQuery()).toBe('hel');
  });
});
