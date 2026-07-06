/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  announceToScreenReader,
  focusFirstElement,
  getNextFocusElementAfterItemDelete,
  getNextFocusElementAfterRowDelete,
  manageModalFocus,
  restoreFocusToTrigger,
  storeFocusTrigger,
} from '../focus-management';

describe('getNextFocusElementAfterRowDelete', () => {
  let tableBody: HTMLTableSectionElement;

  beforeEach(() => {
    document.body.innerHTML = `
      <table>
        <tbody id="tbody">
          <tr id="row0"><td><button id="btn0">Action</button></td></tr>
          <tr id="row1"><td><button id="btn1">Action</button></td></tr>
          <tr id="row2"><td><button id="btn2">Action</button></td></tr>
        </tbody>
      </table>
    `;
    tableBody = document.getElementById('tbody') as HTMLTableSectionElement;
  });

  it('returns null when tableBody is null', () => {
    const row = document.getElementById('row1') as HTMLTableRowElement;
    expect(getNextFocusElementAfterRowDelete(row, null)).toBeNull();
  });

  it('returns next row button when deleting non-last row', () => {
    const row = document.getElementById('row0') as HTMLTableRowElement;
    const result = getNextFocusElementAfterRowDelete(row, tableBody);
    expect(result).toBe(document.getElementById('btn1'));
  });

  it('returns previous row button when deleting last row', () => {
    const row = document.getElementById('row2') as HTMLTableRowElement;
    const result = getNextFocusElementAfterRowDelete(row, tableBody);
    expect(result).toBe(document.getElementById('btn1'));
  });

  it('returns tableBody when no other rows exist', () => {
    document.body.innerHTML = `
      <table><tbody id="tbody2"><tr id="only"><td><button>X</button></td></tr></tbody></table>
    `;
    const tbody = document.getElementById('tbody2') as HTMLTableSectionElement;
    const row = document.getElementById('only') as HTMLTableRowElement;
    const result = getNextFocusElementAfterRowDelete(row, tbody);
    expect(result).toBe(tbody);
  });

  it('returns null when row is not in tableBody', () => {
    const orphanRow = document.createElement('tr');
    expect(getNextFocusElementAfterRowDelete(orphanRow, tableBody)).toBeNull();
  });
});

describe('getNextFocusElementAfterItemDelete', () => {
  let list: HTMLUListElement;

  beforeEach(() => {
    document.body.innerHTML = `
      <ul id="list">
        <li id="item0">A</li>
        <li id="item1">B</li>
        <li id="item2">C</li>
      </ul>
    `;
    list = document.getElementById('list') as HTMLUListElement;
  });

  it('returns null when listContainer is null', () => {
    const item = document.getElementById('item0') as HTMLElement;
    expect(getNextFocusElementAfterItemDelete(item, null)).toBeNull();
  });

  it('returns next item when deleting non-last item', () => {
    const item = document.getElementById('item0') as HTMLElement;
    const result = getNextFocusElementAfterItemDelete(item, list);
    expect(result).toBe(document.getElementById('item1'));
  });

  it('returns previous item when deleting last item', () => {
    const item = document.getElementById('item2') as HTMLElement;
    const result = getNextFocusElementAfterItemDelete(item, list);
    expect(result).toBe(document.getElementById('item1'));
  });

  it('returns null when item not found in list', () => {
    const orphan = document.createElement('li');
    const result = getNextFocusElementAfterItemDelete(orphan, list);
    expect(result).toBeNull();
  });

  it('returns list container when only one item remains and it is deleted', () => {
    document.body.innerHTML = '<ul id="list2"><li id="only-item">A</li></ul>';
    const singleList = document.getElementById('list2') as HTMLElement;
    const onlyItem = document.getElementById('only-item') as HTMLElement;
    const result = getNextFocusElementAfterItemDelete(onlyItem, singleList);
    expect(result).toBe(singleList);
  });
});

describe('storeFocusTrigger', () => {
  it('stores target element from event', () => {
    const button = document.createElement('button');
    document.body.appendChild(button);
    const event = { target: button } as unknown as Event;
    const ref = { current: null as HTMLElement | null };

    storeFocusTrigger(event, ref);
    expect(ref.current).toBe(button);
  });

  it('does nothing when event is null', () => {
    const ref = { current: null as HTMLElement | null };
    storeFocusTrigger(null, ref);
    expect(ref.current).toBeNull();
  });

  it('does nothing when target is not HTMLElement', () => {
    const event = { target: 'string' } as unknown as Event;
    const ref = { current: null as HTMLElement | null };
    storeFocusTrigger(event, ref);
    expect(ref.current).toBeNull();
  });
});

describe('restoreFocusToTrigger', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('calls focus on connected element', () => {
    const button = document.createElement('button');
    document.body.appendChild(button);
    const focusSpy = vi.spyOn(button, 'focus');
    const ref = { current: button };

    restoreFocusToTrigger(ref);
    vi.runAllTimers();

    expect(focusSpy).toHaveBeenCalled();
  });

  it('does nothing when ref is null', () => {
    const ref = { current: null as HTMLElement | null };
    // Should not throw
    expect(() => restoreFocusToTrigger(ref)).not.toThrow();
    vi.runAllTimers();
  });

  it('announces when element has aria-label', () => {
    const button = document.createElement('button');
    button.setAttribute('aria-label', 'Close');
    document.body.appendChild(button);
    const ref = { current: button };

    restoreFocusToTrigger(ref);
    vi.runAllTimers();

    const announcer = document.getElementById('focus-announcer');
    // After the inner requestAnimationFrame
    vi.runAllTimers();
    expect(announcer).not.toBeNull();
  });
});

describe('focusFirstElement', () => {
  it('focuses first focusable element', () => {
    document.body.innerHTML = `
      <div id="container">
        <button id="btn1">First</button>
        <button id="btn2">Second</button>
      </div>
    `;
    const container = document.getElementById('container') as HTMLElement;
    const btn1 = document.getElementById('btn1') as HTMLElement;
    const focusSpy = vi.spyOn(btn1, 'focus');

    focusFirstElement(container);
    expect(focusSpy).toHaveBeenCalled();
  });

  it('makes container focusable when no focusable children', () => {
    document.body.innerHTML = '<div id="container"><p>No buttons</p></div>';
    const container = document.getElementById('container') as HTMLElement;
    const focusSpy = vi.spyOn(container, 'focus');

    focusFirstElement(container);
    expect(container.getAttribute('tabindex')).toBe('-1');
    expect(focusSpy).toHaveBeenCalled();
  });

  it('does nothing when container is null', () => {
    expect(() => focusFirstElement(null)).not.toThrow();
  });
});

describe('announceToScreenReader', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('creates announcer div and sets message', () => {
    announceToScreenReader('Test message');
    vi.runAllTimers();

    const el = document.getElementById('focus-announcer');
    expect(el).not.toBeNull();
    expect(el?.textContent).toBe('Test message');
  });

  it('reuses existing announcer', () => {
    announceToScreenReader('First');
    vi.runAllTimers();
    announceToScreenReader('Second');
    vi.runAllTimers();

    const els = document.querySelectorAll('#focus-announcer');
    expect(els.length).toBe(1);
    expect(els[0]?.textContent).toBe('Second');
  });

  it('sets aria-live to assertive', () => {
    announceToScreenReader('Urgent', 'assertive');

    const el = document.getElementById('focus-announcer');
    expect(el?.getAttribute('aria-live')).toBe('assertive');
  });
});

describe('manageModalFocus', () => {
  it('focuses first element when isOpen is true', () => {
    document.body.innerHTML = `
      <div id="modal">
        <button id="close">Close</button>
      </div>
    `;
    const modal = document.getElementById('modal') as HTMLElement;
    const btn = document.getElementById('close') as HTMLElement;
    const focusSpy = vi.spyOn(btn, 'focus');

    manageModalFocus(modal, true);
    expect(focusSpy).toHaveBeenCalled();
  });

  it('focuses trigger element when closing and trigger is connected', () => {
    document.body.innerHTML = `
      <button id="trigger">Open</button>
      <div id="modal"></div>
    `;
    const trigger = document.getElementById('trigger') as HTMLElement;
    const modal = document.getElementById('modal') as HTMLElement;
    const focusSpy = vi.spyOn(trigger, 'focus');

    manageModalFocus(modal, false, trigger);
    expect(focusSpy).toHaveBeenCalled();
  });

  it('does not throw when closing without trigger', () => {
    document.body.innerHTML = '<div id="modal"></div>';
    const modal = document.getElementById('modal') as HTMLElement;
    expect(() => manageModalFocus(modal, false)).not.toThrow();
  });
});
