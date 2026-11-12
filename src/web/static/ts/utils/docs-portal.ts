/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

const LOCAL_DOCS_PORTAL_URL = 'http://localhost:7876';

export function getDocsPortalUrl(): string {
  return import.meta.env.VITE_DOCS_PORTAL_URL || LOCAL_DOCS_PORTAL_URL;
}

export function initializeDocsPortalLinks(): void {
  document.querySelectorAll<HTMLAnchorElement>('[data-docs-portal-link]').forEach((link) => {
    link.href = getDocsPortalUrl();
  });
}
