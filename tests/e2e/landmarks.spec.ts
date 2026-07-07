import { test, expect } from '@playwright/test';

test.describe('Landmark Regions & ARIA Labels Verification', () => {
  const baseURL = 'http://localhost:8003';

  const testPages = [
    { url: '/', name: 'Home Page' },
    { url: '/manage-categories', name: 'Manage Categories' },
    { url: '/manage-tags', name: 'Manage Tags' },
    { url: '/admin/users', name: 'Admin Users Page' },
  ];

  testPages.forEach(({ url, name }) => {
    test(`${name} has proper landmark regions`, async ({ page }) => {
      await page.goto(`${baseURL}${url}`, { waitUntil: 'networkidle' });

      // Test header landmark
      const header = page.locator('header[role="banner"]');
      await expect(header).toBeVisible({ timeout: 5000 });
      expect(await header.getAttribute('role')).toBe('banner');

      // Test main landmark
      const main = page.locator('main');
      await expect(main).toBeVisible({ timeout: 5000 });
      const mainId = await main.getAttribute('id');
      expect(mainId).toBe('main-content');
      expect(await main.getAttribute('role')).toBe('main');

      // Test footer landmark
      const footer = page.locator('footer[role="contentinfo"]');
      await expect(footer).toBeVisible({ timeout: 5000 });
      expect(await footer.getAttribute('role')).toBe('contentinfo');
    });

    test(`${name} has proper navigation aria-labels`, async ({ page }) => {
      await page.goto(`${baseURL}${url}`, { waitUntil: 'networkidle' });

      // Find all nav elements
      const navs = page.locator('nav[aria-label]');
      const count = await navs.count();

      if (count > 0) {
        for (let i = 0; i < count; i++) {
          const nav = navs.nth(i);
          const ariaLabel = await nav.getAttribute('aria-label');
          expect(ariaLabel).toBeTruthy();
          expect(ariaLabel?.length).toBeGreaterThan(0);
        }
      }
    });
  });
});
