/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { announce } from '../a11y';

describe('announce', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    // Stub requestAnimationFrame to call callback synchronously
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
      cb(0);
      return 0;
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('creates a live region element if one does not exist', () => {
    announce('Hello world');

    const el = document.getElementById('sr-announcer');
    expect(el).not.toBeNull();
    expect(el?.getAttribute('role')).toBe('status');
    expect(el?.getAttribute('aria-live')).toBe('polite');
    expect(el?.getAttribute('aria-atomic')).toBe('true');
    expect(el?.className).toContain('sr-only');
  });

  it('sets text content via requestAnimationFrame callback', () => {
    announce('Test message');

    const el = document.getElementById('sr-announcer');
    expect(el?.textContent).toBe('Test message');
  });

  it('reuses existing live region element', () => {
    announce('First');
    announce('Second');

    const elements = document.querySelectorAll('#sr-announcer');
    expect(elements.length).toBe(1);
    expect(elements[0]?.textContent).toBe('Second');
  });

  it('creates assertive live region when politeness is assertive', () => {
    announce('Alert!', { politeness: 'assertive' });

    const el = document.getElementById('sr-announcer');
    expect(el?.getAttribute('aria-live')).toBe('assertive');
    expect(el?.getAttribute('role')).toBe('alert');
  });

  it('respects custom id option', () => {
    announce('Custom id', { id: 'custom-announcer' });

    const el = document.getElementById('custom-announcer');
    expect(el).not.toBeNull();
  });

  it('respects custom role option', () => {
    announce('Alert role', { role: 'alert' });

    const el = document.getElementById('sr-announcer');
    expect(el?.getAttribute('role')).toBe('alert');
  });

  it('clears text before setting new message', () => {
    // Use real requestAnimationFrame to check clearing behavior
    const captured: { cb: FrameRequestCallback | null } = { cb: null };
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
      captured.cb = cb;
      return 0;
    });

    const el = document.createElement('div');
    el.id = 'sr-announcer';
    el.textContent = 'old text';
    document.body.appendChild(el);

    announce('new text');
    expect(el.textContent).toBe('');

    captured.cb?.(0);
    expect(el.textContent).toBe('new text');
  });
});
