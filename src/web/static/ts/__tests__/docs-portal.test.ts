/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { getDocsPortalUrl, initializeDocsPortalLinks } from '@/utils/docs-portal';

describe('docs portal links', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    document.body.innerHTML = '';
  });

  it('uses the local docs portal when no URL is configured', () => {
    vi.stubEnv('VITE_DOCS_PORTAL_URL', '');

    expect(getDocsPortalUrl()).toBe('http://localhost:7876');
  });

  it('updates every docs link with the configured portal URL', () => {
    vi.stubEnv('VITE_DOCS_PORTAL_URL', 'https://docs.example.test');
    document.body.innerHTML = `
      <a data-docs-portal-link href="http://localhost:7876">Documentation</a>
      <a data-docs-portal-link href="http://localhost:7876">Documentation</a>
    `;

    initializeDocsPortalLinks();

    expect(
      Array.from(document.querySelectorAll<HTMLAnchorElement>('[data-docs-portal-link]')).map(
        (link) => link.href
      )
    ).toEqual(['https://docs.example.test/', 'https://docs.example.test/']);
  });
});
