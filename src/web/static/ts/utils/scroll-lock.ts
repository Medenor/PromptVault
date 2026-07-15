/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Shared, reference-counted body scroll lock.
 *
 * Multiple overlays (mobile drawer, search overlay, etc.) may each want to
 * suppress background scrolling while open. If each overlay independently
 * set/cleared `document.body.style.overflow`, closing one overlay while
 * another is still open would incorrectly re-enable scrolling. This module
 * tracks the set of active lock holders by id and only touches
 * `document.body.style.overflow` when the set transitions to/from empty.
 */

const activeLocks = new Set<string>();

export function lockBodyScroll(id: string): void {
  activeLocks.add(id);
  document.body.style.overflow = 'hidden';
}

export function unlockBodyScroll(id: string): void {
  activeLocks.delete(id);
  if (activeLocks.size === 0) {
    document.body.style.overflow = '';
  }
}
