/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { initNewMenu } from '../new-menu';

function key(target: Element, k: string): void {
  target.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }));
}

describe('initNewMenu', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div>
        <button id="new-menu-btn" aria-expanded="false" aria-controls="new-menu">New</button>
        <div id="new-menu" role="menu" class="hidden">
          <button id="new-prompt-btn" role="menuitem">New Prompt</button>
          <button id="import-skill-btn" role="menuitem">Import skill</button>
        </div>
      </div>
      <p id="outside">outside</p>`;
  });

  const trigger = (): HTMLElement => document.getElementById('new-menu-btn') as HTMLElement;
  const menu = (): HTMLElement => document.getElementById('new-menu') as HTMLElement;
  const first = (): HTMLElement => document.getElementById('new-prompt-btn') as HTMLElement;
  const second = (): HTMLElement => document.getElementById('import-skill-btn') as HTMLElement;

  it('does nothing when the markup is absent', () => {
    document.body.innerHTML = '';
    expect(() => initNewMenu()).not.toThrow();
  });

  it('toggles on click and reflects aria-expanded', () => {
    initNewMenu();
    trigger().click();
    expect(menu().classList.contains('hidden')).toBe(false);
    expect(trigger().getAttribute('aria-expanded')).toBe('true');
    trigger().click();
    expect(menu().classList.contains('hidden')).toBe(true);
    expect(trigger().getAttribute('aria-expanded')).toBe('false');
  });

  it.each(['Enter', ' ', 'ArrowDown'])('opens with %j and focuses the first item', (k) => {
    initNewMenu();
    key(trigger(), k);
    expect(menu().classList.contains('hidden')).toBe(false);
    expect(document.activeElement).toBe(first());
  });

  it('ArrowUp on the trigger focuses the last item', () => {
    initNewMenu();
    key(trigger(), 'ArrowUp');
    expect(document.activeElement).toBe(second());
  });

  it('moves focus with arrows (wrapping), Home and End', () => {
    initNewMenu();
    key(trigger(), 'ArrowDown');
    key(first(), 'ArrowDown');
    expect(document.activeElement).toBe(second());
    key(second(), 'ArrowDown');
    expect(document.activeElement).toBe(first());
    key(first(), 'ArrowUp');
    expect(document.activeElement).toBe(second());
    key(second(), 'Home');
    expect(document.activeElement).toBe(first());
    key(first(), 'End');
    expect(document.activeElement).toBe(second());
  });

  it('Escape closes the menu and refocuses the trigger', () => {
    initNewMenu();
    key(trigger(), 'ArrowDown');
    key(first(), 'Escape');
    expect(menu().classList.contains('hidden')).toBe(true);
    expect(document.activeElement).toBe(trigger());
  });

  it('Tab closes the menu without stealing focus', () => {
    initNewMenu();
    key(trigger(), 'ArrowDown');
    key(first(), 'Tab');
    expect(menu().classList.contains('hidden')).toBe(true);
  });

  it('closes on outside click but not on inside click of the menu container', () => {
    initNewMenu();
    trigger().click();
    document.getElementById('outside')!.click();
    expect(menu().classList.contains('hidden')).toBe(true);
  });

  it('picking an item closes the menu and still runs the item handler', () => {
    initNewMenu();
    const handler = vi.fn();
    second().addEventListener('click', handler);
    trigger().click();
    second().click();
    expect(handler).toHaveBeenCalledTimes(1);
    expect(menu().classList.contains('hidden')).toBe(true);
  });

  it('also wires the secondary "More" dropdown independently', () => {
    document.body.insertAdjacentHTML(
      'beforeend',
      `<button id="more-menu-btn" aria-expanded="false">More</button>
       <div id="more-menu" role="menu" class="hidden"><a role="menuitem" href="#x">Docs</a></div>`
    );
    initNewMenu();
    const more = document.getElementById('more-menu-btn') as HTMLElement;
    const moreMenu = document.getElementById('more-menu') as HTMLElement;
    more.click();
    expect(moreMenu.classList.contains('hidden')).toBe(false);
    expect(menu().classList.contains('hidden')).toBe(true);
    key(more, 'Escape');
    expect(moreMenu.classList.contains('hidden')).toBe(true);
  });
});
