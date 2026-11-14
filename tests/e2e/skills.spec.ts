// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import AxeBuilder from '@axe-core/playwright';
import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';

/**
 * End-to-end smoke test for skill packages (011-skill-packages): import a
 * skill, open it, move through the file tree with the keyboard, view a file,
 * download it, and run an accessibility scan on the detail view.
 *
 * Needs a running dev server with a test admin (see scripts/init_test_admin.py).
 */

const TEST_ADMIN_USERNAME =
  process.env.TEST_ADMIN_USERNAME ?? process.env.TEST_ADMIN_EMAIL ?? 'test_admin_ui@example.com';
const TEST_ADMIN_PASSWORD = process.env.TEST_ADMIN_PASSWORD ?? 'TestAdmin@Pass123456';

/** SC-001: from opening the import dialog to the skill in the list, under 30 s. */
const IMPORT_BUDGET_MS = 30_000;

function crc32(data: Buffer): number {
  let crc = 0xffffffff;
  for (const byte of data) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit++) {
      crc = crc & 1 ? (crc >>> 1) ^ 0xedb88320 : crc >>> 1;
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

/** Minimal ZIP writer (stored entries), so no binary fixture is committed. */
function buildZip(entries: Record<string, string>): Buffer {
  const locals: Buffer[] = [];
  const centrals: Buffer[] = [];
  let offset = 0;
  for (const [name, text] of Object.entries(entries)) {
    const nameBytes = Buffer.from(name, 'utf-8');
    const data = Buffer.from(text, 'utf-8');
    const crc = crc32(data);

    const local = Buffer.alloc(30 + nameBytes.length);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0x0800, 6); // UTF-8 names
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(data.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(nameBytes.length, 26);
    nameBytes.copy(local, 30);
    locals.push(local, data);

    const central = Buffer.alloc(46 + nameBytes.length);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0x0800, 8);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(data.length, 20);
    central.writeUInt32LE(data.length, 24);
    central.writeUInt16LE(nameBytes.length, 28);
    central.writeUInt32LE(offset, 42);
    nameBytes.copy(central, 46);
    centrals.push(central);

    offset += local.length + data.length;
  }
  const centralSize = centrals.reduce((sum, c) => sum + c.length, 0);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(centrals.length, 8);
  end.writeUInt16LE(centrals.length, 10);
  end.writeUInt32LE(centralSize, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, ...centrals, end]);
}

async function login(page: Page): Promise<void> {
  await page.goto('/auth/login', { waitUntil: 'networkidle' });
  await page.locator('#username-or-email').fill(TEST_ADMIN_USERNAME);
  await page.locator('#password').fill(TEST_ADMIN_PASSWORD);
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().includes('/api/auth/login') && response.request().method() === 'POST'
    ),
    page.locator('button[type="submit"]').first().click(),
  ]);
}

test.describe('skill packages', () => {
  test('import, browse by keyboard, view, download and pass axe', async ({ page }) => {
    const name = `e2e-skill-${Date.now()}`;
    const archive = buildZip({
      [`${name}/SKILL.md`]: `---\nname: ${name}\ndescription: End-to-end skill.\n---\n# E2E skill\nRun \${CLAUDE_SKILL_DIR}/scripts/run.sh\n`,
      [`${name}/scripts/run.sh`]: 'echo "hello from the e2e skill"\n',
      [`${name}/references/guide.md`]: '# Guide\n<script>window.__pwned = true</script>\n',
    });

    await login(page);
    await page.goto('/', { waitUntil: 'networkidle' });

    const newMenu = page.locator('#new-menu-btn');
    test.skip(!(await newMenu.isVisible()), 'The desktop "New" menu needs a wide viewport');

    // --- import (SC-001: under 30 s from opening the dialog) -----------------
    const started = Date.now();
    await newMenu.click();
    await page.locator('#import-skill-btn').click();
    await page.locator('input[type="file"][name="archive"]').setInputFiles({
      name: `${name}.zip`,
      mimeType: 'application/zip',
      buffer: archive,
    });
    await page.locator('form.skill-archive-form button[type="submit"]').click();

    const detail = page.locator('.skill-detail-overlay');
    await expect(detail).toBeVisible({ timeout: IMPORT_BUDGET_MS });
    expect(Date.now() - started).toBeLessThan(IMPORT_BUDGET_MS);
    const skillId = await detail.getAttribute('data-skill-id');
    expect(skillId).not.toBeNull();

    try {
      await expect(detail.locator('.skill-title')).toContainText(name);
      await expect(detail.locator('.skill-instructions')).toContainText('${CLAUDE_SKILL_DIR}');

      // --- keyboard navigation of the tree --------------------------------------
      const tree = detail.locator('[role="tree"]');
      await expect(tree).toBeVisible();
      await tree.locator('[role="treeitem"][tabindex="0"]').focus();
      await page.keyboard.press('Home');
      // Folders first: references/ then scripts/ then SKILL.md.
      await expect(tree.locator('[data-path="references"]')).toBeFocused();
      await page.keyboard.press('ArrowDown');
      await expect(tree.locator('[data-path="scripts"]')).toBeFocused();
      await page.keyboard.press('ArrowRight'); // expand
      await expect(tree.locator('[data-path="scripts"]')).toHaveAttribute('aria-expanded', 'true');
      await page.keyboard.press('ArrowRight'); // into the folder
      await expect(tree.locator('[data-path="scripts/run.sh"]')).toBeFocused();
      await page.keyboard.press('Enter');

      // --- view a file (text, shown as text) ------------------------------------
      await expect(detail.locator('.viewer-name')).toHaveText('scripts/run.sh');
      await expect(detail.locator('.viewer-text')).toContainText('hello from the e2e skill');

      // A file with markup-shaped content never runs.
      await tree.locator('[data-path="references"]').focus();
      await page.keyboard.press('Enter'); // expand
      await tree.locator('[data-path="references/guide.md"]').click();
      await expect(detail.locator('.viewer-text')).toContainText('<script>');
      expect(
        await page.evaluate(() => (window as unknown as { __pwned?: boolean }).__pwned)
      ).toBeUndefined();

      // --- accessibility of the detail view -------------------------------------
      const results = await new AxeBuilder({ page })
        .include('.skill-detail-overlay')
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze();
      expect(results.violations).toEqual([]);

      // --- downloads --------------------------------------------------------------
      const [zipDownload] = await Promise.all([
        page.waitForEvent('download'),
        detail.locator('a.skill-download-btn').click(),
      ]);
      expect(zipDownload.suggestedFilename()).toBe(`${name}.zip`);

      const [fileDownload] = await Promise.all([
        page.waitForEvent('download'),
        detail.locator('a.viewer-download').click(),
      ]);
      expect(fileDownload.suggestedFilename()).toBe('guide.md');
    } finally {
      // Always remove what the test created, whatever happened above.
      await page.request.delete(`/api/skills/${skillId}`);
    }
  });

  test('a rejected archive shows a translated reason and stores nothing', async ({ page }) => {
    await login(page);
    await page.goto('/', { waitUntil: 'networkidle' });
    const newMenu = page.locator('#new-menu-btn');
    test.skip(!(await newMenu.isVisible()), 'The desktop "New" menu needs a wide viewport');

    await newMenu.click();
    await page.locator('#import-skill-btn').click();
    await page.locator('input[type="file"][name="archive"]').setInputFiles({
      name: 'no-skill-md.zip',
      mimeType: 'application/zip',
      buffer: buildZip({ 'only/README.md': '# no SKILL.md here\n' }),
    });
    await page.locator('form.skill-archive-form button[type="submit"]').click();

    const status = page.locator('.skill-archive-status');
    await expect(status).toBeVisible();
    await expect(status).not.toBeEmpty();
    await expect(page.locator('.skill-detail-overlay')).toHaveCount(0);
  });

  // Set E2E_SKILL_ZIP to a real skill archive (for example one made on macOS,
  // with __MACOSX clutter and bundled PDFs) to run this extra check.
  test('a real archive imports, drops clutter, and its files can be read', async ({ page }) => {
    const zipPath = process.env.E2E_SKILL_ZIP;
    test.skip(!zipPath, 'Set E2E_SKILL_ZIP to run the real-archive check');
    const buffer = readFileSync(zipPath as string);

    await login(page);
    await page.goto('/', { waitUntil: 'networkidle' });
    const newMenu = page.locator('#new-menu-btn');
    test.skip(!(await newMenu.isVisible()), 'The desktop "New" menu needs a wide viewport');

    await newMenu.click();
    await page.locator('#import-skill-btn').click();
    await page.locator('input[type="file"][name="archive"]').setInputFiles({
      name: 'real-skill.zip',
      mimeType: 'application/zip',
      buffer,
    });
    await page.locator('form.skill-archive-form button[type="submit"]').click();

    const detail = page.locator('.skill-detail-overlay');
    await expect(detail).toBeVisible({ timeout: 60_000 });
    const skillId = await detail.getAttribute('data-skill-id');
    try {
      const treeItems = detail.locator('[role="tree"] [role="treeitem"]');
      const paths = await treeItems.evaluateAll((els) =>
        els.map((el) => (el as HTMLElement).dataset['path'] ?? '')
      );
      // OS clutter never reaches the vault.
      expect(paths.some((p) => p.includes('__MACOSX') || p.endsWith('.DS_Store'))).toBe(false);
      expect(paths).toContain('SKILL.md');

      // A bundled PDF is binary: size and download link, no text.
      await detail.locator('[data-path="references"] > .tree-row').click();
      await detail.locator('[data-path="references/source-pdfs"] > .tree-row').click();
      await detail
        .locator('[data-path="references/source-pdfs/21-cfr-part-11.pdf"] > .tree-row')
        .click();
      await expect(detail.locator('.viewer-size')).toBeVisible();
      await expect(detail.locator('a.viewer-download')).toBeVisible();
      await expect(detail.locator('.viewer-text')).toHaveCount(0);

      const [download] = await Promise.all([
        page.waitForEvent('download'),
        detail.locator('a.skill-download-btn').click(),
      ]);
      expect(download.suggestedFilename()).toMatch(/\.zip$/);
    } finally {
      await page.request.delete(`/api/skills/${skillId}`);
    }
  });
});
