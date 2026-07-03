/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  cleanupTabindex,
  createFocusTrap,
  fixSemanticHTML,
  getFocusableElements,
  handleEscapeKey,
  manageModalFocus,
  syncRovingTabindex,
} from '../keyboard-nav';

describe('getFocusableElements', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('returns buttons and links', () => {
    document.body.innerHTML = `
      <div id="container">
        <button>Click</button>
        <a href="#">Link</a>
        <input type="text" />
        <span>Not focusable</span>
      </div>
    `;
    const container = document.getElementById('container') as HTMLElement;
    const focusables = getFocusableElements(container);
    expect(focusables.length).toBe(3);
  });

  it('excludes hidden elements', () => {
    document.body.innerHTML = `
      <div id="container">
        <button style="display:none">Hidden</button>
        <button>Visible</button>
      </div>
    `;
    const container = document.getElementById('container') as HTMLElement;
    const focusables = getFocusableElements(container);
    expect(focusables.length).toBe(1);
  });

  it('excludes disabled elements when excludeDisabled is true', () => {
    document.body.innerHTML = `
      <div id="container">
        <button disabled>Disabled</button>
        <button>Enabled</button>
      </div>
    `;
    const container = document.getElementById('container') as HTMLElement;
    const focusables = getFocusableElements(container, { excludeDisabled: true });
    expect(focusables.length).toBe(1);
  });

  it('returns empty array for empty container', () => {
    document.body.innerHTML = '<div id="container"><p>Text</p></div>';
    const container = document.getElementById('container') as HTMLElement;
    expect(getFocusableElements(container)).toHaveLength(0);
  });
});

describe('createFocusTrap', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="modal">
        <button id="btn1">First</button>
        <button id="btn2">Second</button>
        <button id="btn3">Third</button>
      </div>
    `;
  });

  it('activate moves focus to first element', () => {
    const modal = document.getElementById('modal') as HTMLElement;
    const btn1 = document.getElementById('btn1') as HTMLElement;
    const focusSpy = vi.spyOn(btn1, 'focus');

    const trap = createFocusTrap(modal);
    trap.activate();

    expect(focusSpy).toHaveBeenCalled();
    trap.deactivate();
  });

  it('deactivate removes keydown listener and restores focus', () => {
    const trigger = document.createElement('button');
    trigger.textContent = 'Trigger';
    document.body.appendChild(trigger);
    trigger.focus();

    const modal = document.getElementById('modal') as HTMLElement;
    const trap = createFocusTrap(modal);
    trap.activate();

    const focusSpy = vi.spyOn(trigger, 'focus');
    trap.deactivate();

    expect(focusSpy).toHaveBeenCalled();
  });

  it('moveFocusToFirst focuses first focusable', () => {
    const modal = document.getElementById('modal') as HTMLElement;
    const btn1 = document.getElementById('btn1') as HTMLElement;
    const trap = createFocusTrap(modal);
    trap.activate();

    const focusSpy = vi.spyOn(btn1, 'focus');
    trap.moveFocusToFirst();
    expect(focusSpy).toHaveBeenCalled();

    trap.deactivate();
  });

  it('activate with no focusable elements makes container focusable', () => {
    document.body.innerHTML = '<div id="empty-modal"><p>No buttons</p></div>';
    const modal = document.getElementById('empty-modal') as HTMLElement;
    const focusSpy = vi.spyOn(modal, 'focus');

    const trap = createFocusTrap(modal);
    trap.activate();

    expect(modal.getAttribute('tabindex')).toBe('-1');
    expect(focusSpy).toHaveBeenCalled();
    trap.deactivate();
  });

  it('traps Tab key at end of focusables', () => {
    const modal = document.getElementById('modal') as HTMLElement;
    const btn1 = document.getElementById('btn1') as HTMLElement;
    const btn3 = document.getElementById('btn3') as HTMLElement;

    const trap = createFocusTrap(modal);
    trap.activate();

    // Simulate btn3 having focus
    btn3.focus();
    Object.defineProperty(document, 'activeElement', { value: btn3, configurable: true });

    const focusSpy = vi.spyOn(btn1, 'focus');
    const tabEvent = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true });
    document.dispatchEvent(tabEvent);

    expect(focusSpy).toHaveBeenCalled();
    trap.deactivate();
  });

  it('traps Shift+Tab key at start of focusables', () => {
    const modal = document.getElementById('modal') as HTMLElement;
    const btn1 = document.getElementById('btn1') as HTMLElement;
    const btn3 = document.getElementById('btn3') as HTMLElement;

    const trap = createFocusTrap(modal);
    trap.activate();

    btn1.focus();
    Object.defineProperty(document, 'activeElement', { value: btn1, configurable: true });

    const focusSpy = vi.spyOn(btn3, 'focus');
    const tabEvent = new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true });
    document.dispatchEvent(tabEvent);

    expect(focusSpy).toHaveBeenCalled();
    trap.deactivate();
  });
});

describe('handleEscapeKey', () => {
  it('calls onEscape and returns true for Escape key', () => {
    const onEscape = vi.fn();
    const event = new KeyboardEvent('keydown', { key: 'Escape' });
    const result = handleEscapeKey(event, onEscape);

    expect(onEscape).toHaveBeenCalled();
    expect(result).toBe(true);
  });

  it('returns false for non-Escape key', () => {
    const onEscape = vi.fn();
    const event = new KeyboardEvent('keydown', { key: 'Enter' });
    const result = handleEscapeKey(event, onEscape);

    expect(onEscape).not.toHaveBeenCalled();
    expect(result).toBe(false);
  });
});

describe('manageModalFocus', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <button id="trigger">Open</button>
      <div id="modal" class="hidden" style="display:none">
        <h2>My Modal</h2>
        <button id="close-btn">Close</button>
      </div>
    `;
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('show makes modal visible and focuses first element', () => {
    const modal = document.getElementById('modal') as HTMLElement;
    const closeBtn = document.getElementById('close-btn') as HTMLElement;
    const focusSpy = vi.spyOn(closeBtn, 'focus');

    const manager = manageModalFocus(modal);
    manager.show();

    expect(modal.classList.contains('hidden')).toBe(false);
    expect(focusSpy).toHaveBeenCalled();
  });

  it('hide makes modal hidden', () => {
    const modal = document.getElementById('modal') as HTMLElement;

    const manager = manageModalFocus(modal);
    manager.show();
    manager.hide();

    expect(modal.classList.contains('hidden')).toBe(true);
    expect(modal.style.display).toBe('none');
  });

  it('calls onOpen callback', () => {
    const modal = document.getElementById('modal') as HTMLElement;
    const onOpen = vi.fn();

    const manager = manageModalFocus(modal, { onOpen });
    manager.show();

    expect(onOpen).toHaveBeenCalled();
  });

  it('calls onClose callback', () => {
    const modal = document.getElementById('modal') as HTMLElement;
    const onClose = vi.fn();

    const manager = manageModalFocus(modal, { onClose });
    manager.show();
    manager.hide();

    expect(onClose).toHaveBeenCalled();
  });

  it('Escape key closes modal', () => {
    const modal = document.getElementById('modal') as HTMLElement;
    const onClose = vi.fn();

    const manager = manageModalFocus(modal, { onClose });
    manager.show();

    const escEvent = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
    document.dispatchEvent(escEvent);

    expect(onClose).toHaveBeenCalled();
  });

  it('show without trapFocus just moves to first element', () => {
    const modal = document.getElementById('modal') as HTMLElement;
    const closeBtn = document.getElementById('close-btn') as HTMLElement;
    const focusSpy = vi.spyOn(closeBtn, 'focus');

    const manager = manageModalFocus(modal, { trapFocus: false });
    manager.show();

    expect(focusSpy).toHaveBeenCalled();
    manager.hide();
  });
});

describe('cleanupTabindex', () => {
  it('removes tabindex > 0', () => {
    document.body.innerHTML = `
      <div id="container">
        <button tabindex="1">Bad</button>
        <button tabindex="0">Good</button>
        <button tabindex="-1">Skip</button>
      </div>
    `;
    const container = document.getElementById('container') as HTMLElement;
    cleanupTabindex(container);

    const buttons = container.querySelectorAll('button');
    expect(buttons[0]?.hasAttribute('tabindex')).toBe(false);
    expect(buttons[1]?.getAttribute('tabindex')).toBe('0');
    expect(buttons[2]?.getAttribute('tabindex')).toBe('-1');
  });
});

describe('fixSemanticHTML', () => {
  it('adds tabindex to role=button elements', () => {
    document.body.innerHTML = `
      <div id="container">
        <span role="button" id="span-btn">Click me</span>
      </div>
    `;
    const container = document.getElementById('container') as HTMLElement;
    fixSemanticHTML(container);

    const span = document.getElementById('span-btn') as HTMLElement;
    expect(span.getAttribute('tabindex')).toBe('0');
  });

  it('adds keydown handler to role=button elements', () => {
    document.body.innerHTML = `
      <div id="container">
        <span role="button" id="span-btn">Click me</span>
      </div>
    `;
    const container = document.getElementById('container') as HTMLElement;
    fixSemanticHTML(container);

    const span = document.getElementById('span-btn') as HTMLElement;
    const clickSpy = vi.spyOn(span, 'click');

    const enterEvent = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    span.dispatchEvent(enterEvent);
    expect(clickSpy).toHaveBeenCalled();
  });

  it('does not add duplicate keydown handlers', () => {
    document.body.innerHTML = `
      <div id="container">
        <span role="button" id="span-btn">Click me</span>
      </div>
    `;
    const container = document.getElementById('container') as HTMLElement;
    fixSemanticHTML(container);
    fixSemanticHTML(container);

    const span = document.getElementById('span-btn') as HTMLElement;
    const clickSpy = vi.spyOn(span, 'click');

    const enterEvent = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    span.dispatchEvent(enterEvent);
    expect(clickSpy).toHaveBeenCalledTimes(1);
  });
});

describe('syncRovingTabindex', () => {
  it('sets tabindex=0 on focused item, -1 on others', () => {
    document.body.innerHTML = `
      <ul id="list">
        <li role="button" id="item1">A</li>
        <li role="button" id="item2">B</li>
        <li role="button" id="item3">C</li>
      </ul>
    `;
    const list = document.getElementById('list') as HTMLElement;
    const item2 = document.getElementById('item2') as HTMLElement;

    syncRovingTabindex(list, item2);

    expect(document.getElementById('item1')?.getAttribute('tabindex')).toBe('-1');
    expect(document.getElementById('item2')?.getAttribute('tabindex')).toBe('0');
    expect(document.getElementById('item3')?.getAttribute('tabindex')).toBe('-1');
  });
});
