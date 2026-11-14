/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Desktop header dropdowns: "New" (New prompt / Import skill) and "More"
 * (Import/Export, Backup, Documentation; shown only between md and xl) keep
 * the header on a single line.
 *
 * The menu items keep their own ids (#new-prompt-btn, #import-skill-btn) and
 * click handlers; this module only manages open/close and keyboard behaviour.
 */

const MENU_ITEM_SELECTOR = '[role="menuitem"]';

function initDropdown(triggerId: string, menuId: string): void {
  const trigger = document.getElementById(triggerId);
  const menu = document.getElementById(menuId);
  if (!trigger || !menu) {
    return;
  }

  const items = (): HTMLElement[] =>
    Array.from(menu.querySelectorAll<HTMLElement>(MENU_ITEM_SELECTOR));
  const isOpen = (): boolean => !menu.classList.contains('hidden');

  const close = (restoreFocus: boolean): void => {
    if (!isOpen()) return;
    menu.classList.add('hidden');
    trigger.setAttribute('aria-expanded', 'false');
    if (restoreFocus) trigger.focus();
  };

  const open = (focusIndex: number | null): void => {
    menu.classList.remove('hidden');
    trigger.setAttribute('aria-expanded', 'true');
    if (focusIndex !== null) {
      const list = items();
      list[focusIndex < 0 ? list.length - 1 : focusIndex]?.focus();
    }
  };

  trigger.addEventListener('click', () => {
    if (isOpen()) {
      close(false);
    } else {
      open(null);
    }
  });

  trigger.addEventListener('keydown', (event: KeyboardEvent) => {
    if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      open(0);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      open(-1);
    } else if (event.key === 'Escape') {
      close(true);
    }
  });

  menu.addEventListener('keydown', (event: KeyboardEvent) => {
    const list = items();
    const index = list.indexOf(document.activeElement as HTMLElement);
    if (event.key === 'Escape') {
      event.preventDefault();
      close(true);
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      list[(index + 1) % list.length]?.focus();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      list[(index - 1 + list.length) % list.length]?.focus();
    } else if (event.key === 'Home') {
      event.preventDefault();
      list[0]?.focus();
    } else if (event.key === 'End') {
      event.preventDefault();
      list[list.length - 1]?.focus();
    } else if (event.key === 'Tab') {
      close(false);
    }
  });

  // Picking an item closes the menu (the item's own handler still runs).
  menu.addEventListener('click', (event: MouseEvent) => {
    if ((event.target as HTMLElement).closest(MENU_ITEM_SELECTOR)) {
      close(false);
    }
  });

  document.addEventListener('click', (event: MouseEvent) => {
    const target = event.target as Node;
    if (isOpen() && !menu.contains(target) && !trigger.contains(target)) {
      close(false);
    }
  });
}

export function initNewMenu(): void {
  initDropdown('new-menu-btn', 'new-menu');
  initDropdown('more-menu-btn', 'more-menu');
}
