/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string) => `tr:${key}`),
    language: 'en',
  },
}));

import { setSelectedTags } from './tag-autocomplete';

const XSS_TAG = '<img src=x onerror=alert(1)>';

describe('tag chip rendering XSS hardening', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="tag-chips"></div>
      <input id="prompt-tags-input" />
      <input id="prompt-tags" />
    `;
    (window as unknown as { alert?: unknown }).alert = vi.fn();
  });

  it('renders a malicious tag name as inert text, not a live element', () => {
    setSelectedTags([XSS_TAG]);

    const chipContainer = document.getElementById('tag-chips');
    expect(chipContainer).not.toBeNull();
    expect(chipContainer?.querySelector('img')).toBeNull();
    expect(chipContainer?.querySelector('[onerror], [onload]')).toBeNull();
    expect(chipContainer?.textContent).toContain(XSS_TAG);
    expect((window as unknown as { alert: ReturnType<typeof vi.fn> }).alert).not.toHaveBeenCalled();
  });
});
