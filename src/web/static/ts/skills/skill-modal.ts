/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Dark-mode chrome for the shared modal, whose card, title and close button
 * are light-only. Scoped here so other dialogs keep their current look.
 */
export const SKILL_MODAL_CLASS =
  'dark:bg-gray-800 dark:[&_h2]:text-gray-100 dark:[&_button[aria-label="Close_modal"]]:text-gray-300 dark:[&_button[aria-label="Close_modal"]]:hover:text-gray-100';
