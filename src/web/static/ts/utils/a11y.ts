/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Small accessibility helpers (live region announcers, etc.)
 */

type LivePoliteness = 'polite' | 'assertive';

function ensureLiveRegion(
  id: string,
  politeness: LivePoliteness,
  role: 'status' | 'alert' = 'status'
): HTMLElement {
  const existing = document.getElementById(id);
  if (existing) {
    return existing;
  }

  const el = document.createElement('div');
  el.id = id;
  el.className = 'sr-only';
  el.setAttribute('role', role);
  el.setAttribute('aria-live', politeness);
  el.setAttribute('aria-atomic', 'true');
  document.body.appendChild(el);
  return el;
}

/**
 * Announce a message through a dedicated live region.
 *
 * We clear the text first, then re-set it on the next frame, so screen readers
 * consistently announce repeated messages.
 */
export function announce(
  message: string,
  opts?: { id?: string; politeness?: LivePoliteness; role?: 'status' | 'alert' }
): void {
  const id = opts?.id || 'sr-announcer';
  const politeness = opts?.politeness || 'polite';
  const role = opts?.role || (politeness === 'assertive' ? 'alert' : 'status');

  const el = ensureLiveRegion(id, politeness, role);
  el.textContent = '';
  requestAnimationFrame(() => {
    el.textContent = message;
  });
}
