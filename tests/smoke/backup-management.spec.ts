// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// @ts-nocheck

/**
 * Functional smoke test for the backup management page
 * (/backup-management), backed by backup-management.ts. Only exercises the
 * additive "create backup" flow — restore is intentionally NOT driven here,
 * mirroring tests/accessibility/backup-management.spec.ts which also stops
 * short of clicking #confirm-restore-btn against real data (data-loss risk
 * flagged in Phase 6 of the god-file refactor plan). Phase 0c safety net.
 */

import { expect } from '@playwright/test';
import {
  authenticatedAdminTest,
  navigateToProtectedRoute,
} from '../accessibility/fixtures/auth.js';

// Backup creation requires the admin role.
const test = authenticatedAdminTest;

test.describe('Backup management functional smoke tests', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await navigateToProtectedRoute(page, '/backup-management');
    await page.waitForLoadState('networkidle');
  });

  test('creating a backup adds an entry to the backup list', async ({
    authenticatedPage: page,
  }) => {
    test.setTimeout(90000);
    const backupList = page.locator('#backup-list');
    const initialCount = await backupList.locator('[data-id][data-encrypted]').count();

    // This deployment has backup encryption enabled, so the passphrase field
    // is required before the create request is even sent.
    const passphraseInput = page.locator('#backup-create-passphrase');
    if (await passphraseInput.isVisible().catch(() => false)) {
      await passphraseInput.fill('SmokeTestBackupPassphrase123!');
    }

    const createBtn = page.locator('button[onclick="createBackup()"]');
    await createBtn.click();

    // Real backup creation (DB dump + encryption) can take a while, especially
    // against a dev DB that has accumulated many prior smoke-test artifacts.
    await expect
      .poll(async () => await backupList.locator('[data-id][data-encrypted]').count(), {
        timeout: 60000,
      })
      .toBeGreaterThan(initialCount);
  });

  test('backup list is populated on page load', async ({ authenticatedPage: page }) => {
    const backupList = page.locator('#backup-list');
    await expect(backupList).not.toContainText('Loading backups', { timeout: 15000 });
  });
});
