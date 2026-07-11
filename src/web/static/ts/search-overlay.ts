/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Full-screen mobile search overlay (FR-016): replaces the desktop inline
 * search bar with a dedicated, one-tap full-screen search UI on mobile.
 * The overlay's input participates in the same search pipeline as the
 * desktop/drawer search inputs via a shared `input` event dispatched to it.
 */

import {
  createFocusTrap,
  focusFirstElement,
  restoreFocusToTrigger,
} from '@/utils/focus-management';

let removeFocusTrap: (() => void) | null = null;
const lastTrigger: { current: HTMLElement | null } = { current: null };

function getOverlayElements(): { overlay: HTMLElement; toggle: HTMLElement } | null {
  const overlay = document.getElementById('mobile-search-overlay');
  const toggle = document.getElementById('mobile-search-toggle');
  if (!overlay || !toggle) return null;
  return { overlay, toggle };
}

export function isSearchOverlayOpen(): boolean {
  const overlay = document.getElementById('mobile-search-overlay');
  return !!overlay && !overlay.classList.contains('hidden');
}

export function openSearchOverlay(triggerElement?: HTMLElement | null): void {
  const els = getOverlayElements();
  if (!els) return;
  const { overlay, toggle } = els;

  if (triggerElement) {
    lastTrigger.current = triggerElement;
  }

  overlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  toggle.setAttribute('aria-expanded', 'true');

  focusFirstElement(overlay);
  removeFocusTrap?.();
  removeFocusTrap = createFocusTrap(overlay);

  document.addEventListener('keydown', handleOverlayKeydown);
}

export function closeSearchOverlay(): void {
  const els = getOverlayElements();
  if (!els) return;
  const { overlay, toggle } = els;

  if (overlay.classList.contains('hidden')) {
    return;
  }

  overlay.classList.add('hidden');
  document.body.style.overflow = '';
  toggle.setAttribute('aria-expanded', 'false');

  removeFocusTrap?.();
  removeFocusTrap = null;

  document.removeEventListener('keydown', handleOverlayKeydown);

  restoreFocusToTrigger(lastTrigger);
}

function handleOverlayKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    closeSearchOverlay();
  }
}

/**
 * Wires up the search overlay's toggle button and close button.
 * The overlay's own search input is wired to the shared search handler by
 * the caller (see setupSearchEventListeners in app.ts), matching how the
 * desktop/drawer search inputs are wired.
 */
export function initSearchOverlay(): void {
  const els = getOverlayElements();
  if (!els) return;
  const { toggle } = els;

  toggle.setAttribute('aria-expanded', 'false');
  toggle.addEventListener('click', () => openSearchOverlay(toggle));

  const closeBtn = document.getElementById('search-overlay-close');
  closeBtn?.addEventListener('click', closeSearchOverlay);
}
