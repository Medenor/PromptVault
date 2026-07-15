/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Unified mobile navigation drawer: hamburger toggle, slide-out drawer,
 * focus trap, outside-tap/Escape close, ARIA state.
 *
 * Replaces the previous split between a filters-only "mobile sidebar" and a
 * separate "mobile menu dropdown" — both triggers now open the same drawer
 * (#mobile-sidebar), which contains both primary nav actions and filters.
 */

import {
  createFocusTrap,
  focusFirstElement,
  restoreFocusToTrigger,
} from '@/utils/focus-management';
import { lockBodyScroll, unlockBodyScroll } from '@/utils/scroll-lock';

let removeFocusTrap: (() => void) | null = null;
const lastTrigger: { current: HTMLElement | null } = { current: null };

function getDrawerElements(): {
  drawer: HTMLElement;
  backdrop: HTMLElement;
  toggles: HTMLElement[];
} | null {
  const drawer = document.getElementById('mobile-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (!drawer || !backdrop) return null;

  const toggles = Array.from(
    document.querySelectorAll<HTMLElement>('#mobile-menu-toggle, #sidebar-toggle')
  );

  return { drawer, backdrop, toggles };
}

export function isMobileDrawerOpen(): boolean {
  const drawer = document.getElementById('mobile-sidebar');
  return !!drawer && !drawer.classList.contains('-translate-x-full');
}

export function openMobileDrawer(triggerElement?: HTMLElement | null): void {
  const els = getDrawerElements();
  if (!els) return;
  const { drawer, backdrop, toggles } = els;

  if (triggerElement) {
    lastTrigger.current = triggerElement;
  }

  drawer.classList.remove('-translate-x-full');
  backdrop.classList.remove('hidden');
  lockBodyScroll('mobile-nav');

  toggles.forEach((toggle) => toggle.setAttribute('aria-expanded', 'true'));

  focusFirstElement(drawer);
  removeFocusTrap?.();
  removeFocusTrap = createFocusTrap(drawer);

  document.addEventListener('keydown', handleDrawerKeydown);
}

export function closeMobileDrawer(): void {
  const els = getDrawerElements();
  if (!els) return;
  const { drawer, backdrop, toggles } = els;

  if (drawer.classList.contains('-translate-x-full')) {
    return;
  }

  drawer.classList.add('-translate-x-full');
  backdrop.classList.add('hidden');
  unlockBodyScroll('mobile-nav');

  toggles.forEach((toggle) => toggle.setAttribute('aria-expanded', 'false'));

  removeFocusTrap?.();
  removeFocusTrap = null;

  document.removeEventListener('keydown', handleDrawerKeydown);

  restoreFocusToTrigger(lastTrigger);
}

export function toggleMobileDrawer(triggerElement?: HTMLElement | null): void {
  if (isMobileDrawerOpen()) {
    closeMobileDrawer();
  } else {
    openMobileDrawer(triggerElement);
  }
}

function handleDrawerKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    closeMobileDrawer();
  }
}

function handleBackdropClick(): void {
  closeMobileDrawer();
}

function handleOutsideClick(event: MouseEvent): void {
  if (!isMobileDrawerOpen()) return;

  const drawer = document.getElementById('mobile-sidebar');
  const toggles = document.querySelectorAll<HTMLElement>('#mobile-menu-toggle, #sidebar-toggle');
  const target = event.target as Node;

  const clickedInsideDrawer = !!drawer && drawer.contains(target);
  const clickedToggle = Array.from(toggles).some((toggle) => toggle.contains(target));

  if (!clickedInsideDrawer && !clickedToggle) {
    closeMobileDrawer();
  }
}

/**
 * Wires up the drawer's triggers, close button, backdrop, and outside-tap
 * close handler. Call once at app startup (mirrors the other `initialize*`
 * setup functions in app.ts, none of which guard against re-invocation).
 */
export function initMobileNav(): void {
  const els = getDrawerElements();
  if (!els) return;
  const { backdrop, toggles } = els;

  toggles.forEach((toggle) => {
    toggle.setAttribute('aria-expanded', 'false');
    toggle.addEventListener('click', () => toggleMobileDrawer(toggle));
  });

  const closeBtn = document.getElementById('sidebar-close');
  closeBtn?.addEventListener('click', closeMobileDrawer);

  backdrop.addEventListener('click', handleBackdropClick);

  document.addEventListener('click', handleOutsideClick);
}

/**
 * Keeps a focused text input/textarea visible above the on-screen virtual
 * keyboard on mobile (FR-005). `interactive-widget=resizes-content` in the
 * viewport meta tag handles this natively in modern browsers; this is a
 * `scrollIntoView` fallback for browsers/OS versions that don't yet honor it.
 */
export function initKeyboardSafeScroll(selectors: string[]): void {
  selectors.forEach((selector) => {
    const el = document.querySelector<HTMLElement>(selector);
    el?.addEventListener('focus', () => {
      window.setTimeout(() => {
        el.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }, 300);
    });
  });
}
