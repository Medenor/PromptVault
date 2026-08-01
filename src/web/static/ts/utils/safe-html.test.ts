/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { describe, expect, it } from 'vitest';
import { html, raw } from './safe-html';

describe('html tagged template', () => {
  it('escapes basic interpolated values', () => {
    const title = '<script>alert(1)</script>';
    const result = html`<div>${title}</div>`;
    expect(result).toBe('<div>&lt;script&gt;alert(1)&lt;/script&gt;</div>');
    expect(result).not.toContain('<script>');
  });

  it('escapes quotes and ampersands', () => {
    const value = `"quoted" & 'single' <tag>`;
    const result = html`<span title="${value}">${value}</span>`;
    expect(result).not.toContain('<tag>');
    expect(result).toContain('&lt;tag&gt;');
  });

  it('does not allow a double-quoted attribute value to break out and inject a new attribute', () => {
    const evil = '" onmouseover="alert(1)';
    const result = html`<div data-name="${evil}"></div>`;

    const container = document.createElement('div');
    container.innerHTML = result;
    const parsed = container.firstElementChild;

    expect(parsed).not.toBeNull();
    expect(parsed?.hasAttribute('onmouseover')).toBe(false);
    expect(parsed?.attributes.length).toBe(1);
    expect(parsed?.getAttribute('data-name')).toBe(evil);
  });

  it('leaves raw()-wrapped values unescaped', () => {
    const trusted = raw('<b>bold</b>');
    const result = html`<div>${trusted}</div>`;
    expect(result).toBe('<div><b>bold</b></div>');
  });

  it('nests a raw()-wrapped html template inside another template', () => {
    const inner = html`<li>${'<img src=x onerror=alert(1)>'}</li>`;
    const rawInner = raw(inner);
    const outer = html`<ul>
      ${rawInner}
    </ul>`;
    expect(outer.replace(/\s+/g, '')).toBe('<ul><li>&lt;imgsrc=xonerror=alert(1)&gt;</li></ul>');
    expect(outer).not.toContain('<img');
  });

  it('joins array interpolation by escaping/raw-checking each item', () => {
    const items = ['<a>', raw('<b>trusted</b>'), 'plain'];
    const result = html`<div>${items}</div>`;
    expect(result).toBe('<div>&lt;a&gt;<b>trusted</b>plain</div>');
  });

  it('treats null and undefined as empty string', () => {
    const result = html`<div>${null}-${undefined}-${''}</div>`;
    expect(result).toBe('<div>--</div>');
  });

  it('coerces non-string values to string before escaping', () => {
    const result = html`<div>${42}-${true}</div>`;
    expect(result).toBe('<div>42-true</div>');
  });
});
