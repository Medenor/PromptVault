// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/**
 * Test data setup and fixtures for accessibility tests
 * Provides helpers to create and manage test data without affecting production
 */

import { Page, APIRequestContext } from '@playwright/test';

/**
 * Test user credentials
 */
export const TEST_USERS = {
  regular: {
    username: process.env.ACCESSIBILITY_USER_USERNAME || 'testuser@example.com',
    password: process.env.ACCESSIBILITY_USER_PASSWORD || 'Test@123456',
  },
  admin: {
    username: process.env.ACCESSIBILITY_ADMIN_USERNAME || 'admin@example.com',
    password: process.env.ACCESSIBILITY_ADMIN_PASSWORD || 'Admin@123456',
  },
};

/**
 * Base URL for API calls
 */
export function getBaseURL(): string {
  return process.env.ACCESSIBILITY_BASE_URL ?? 'http://127.0.0.1:8003';
}

/**
 * Create a test prompt/item
 */
export async function createTestPrompt(
  request: APIRequestContext,
  data: {
    title: string;
    content: string;
    category?: string;
    tags?: string[];
  }
): Promise<any> {
  const baseURL = getBaseURL();

  const response = await request.post(`${baseURL}/api/prompts`, {
    data,
  });

  if (!response.ok()) {
    throw new Error(`Failed to create test prompt: ${response.statusText()}`);
  }

  return response.json();
}

/**
 * Create multiple test prompts
 */
export async function createTestPrompts(
  request: APIRequestContext,
  count: number = 5
): Promise<any[]> {
  const prompts = [];

  for (let i = 1; i <= count; i++) {
    const prompt = await createTestPrompt(request, {
      title: `Test Prompt ${i}`,
      content: `This is test prompt number ${i}. Lorem ipsum dolor sit amet.`,
      category: `Category ${Math.ceil(i / 2)}`,
      tags: [`tag-${i}`, 'test-data'],
    });
    prompts.push(prompt);
  }

  return prompts;
}

/**
 * Create a test category
 */
export async function createTestCategory(
  request: APIRequestContext,
  name: string,
  description?: string
): Promise<any> {
  const baseURL = getBaseURL();

  const response = await request.post(`${baseURL}/api/categories`, {
    data: {
      name,
      description: description || `Test category: ${name}`,
    },
  });

  if (!response.ok()) {
    throw new Error(`Failed to create test category: ${response.statusText()}`);
  }

  return response.json();
}

/**
 * Create test categories
 */
export async function createTestCategories(
  request: APIRequestContext,
  count: number = 3
): Promise<any[]> {
  const categories = [];

  for (let i = 1; i <= count; i++) {
    const category = await createTestCategory(request, `Test Category ${i}`);
    categories.push(category);
  }

  return categories;
}

/**
 * Create a test tag
 */
export async function createTestTag(
  request: APIRequestContext,
  name: string,
  color?: string
): Promise<any> {
  const baseURL = getBaseURL();

  const response = await request.post(`${baseURL}/api/tags`, {
    data: {
      name,
      color: color || '#667eea',
    },
  });

  if (!response.ok()) {
    throw new Error(`Failed to create test tag: ${response.statusText()}`);
  }

  return response.json();
}

/**
 * Create test tags
 */
export async function createTestTags(
  request: APIRequestContext,
  count: number = 5
): Promise<any[]> {
  const tags = [];
  const colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe'];

  for (let i = 1; i <= count; i++) {
    const tag = await createTestTag(request, `test-tag-${i}`, colors[(i - 1) % colors.length]);
    tags.push(tag);
  }

  return tags;
}

/**
 * Delete all test data (cleanup)
 */
export async function cleanupTestData(request: APIRequestContext): Promise<void> {
  const baseURL = getBaseURL();

  try {
    // Delete prompts
    const promptsResponse = await request.get(`${baseURL}/api/prompts?tags=test-data`);
    if (promptsResponse.ok()) {
      const prompts = await promptsResponse.json();
      for (const prompt of prompts) {
        await request.delete(`${baseURL}/api/prompts/${prompt.id}`);
      }
    }

    // Delete categories
    const categoriesResponse = await request.get(`${baseURL}/api/categories`);
    if (categoriesResponse.ok()) {
      const categories = await categoriesResponse.json();
      for (const cat of categories) {
        if (cat.name.includes('Test Category')) {
          await request.delete(`${baseURL}/api/categories/${cat.id}`);
        }
      }
    }

    // Delete tags
    const tagsResponse = await request.get(`${baseURL}/api/tags`);
    if (tagsResponse.ok()) {
      const tags = await tagsResponse.json();
      for (const tag of tags) {
        if (tag.name.includes('test-tag')) {
          await request.delete(`${baseURL}/api/tags/${tag.id}`);
        }
      }
    }
  } catch (error) {
    console.warn('Cleanup warning:', error);
  }
}

/**
 * Seed database with test data for accessibility testing
 */
export async function seedTestData(request: APIRequestContext): Promise<void> {
  try {
    // Create test categories
    await createTestCategories(request, 3);

    // Create test tags
    await createTestTags(request, 5);

    // Create test prompts
    await createTestPrompts(request, 10);

    console.log('Test data seeded successfully');
  } catch (error) {
    console.warn('Seed warning:', error);
  }
}

/**
 * Wait for page to be fully loaded and interactive
 */
export async function waitForPageReady(page: Page, timeout: number = 30000): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout });

  // Wait for any aria-busy to be false
  await page.waitForFunction(
    () => {
      const busyElements = document.querySelectorAll('[aria-busy="true"]');
      return busyElements.length === 0;
    },
    { timeout }
  );
}

/**
 * Get all form inputs on page
 */
export async function getAllFormInputs(
  page: Page
): Promise<{ selector: string; type: string; label?: string }[]> {
  return page.evaluate(() => {
    const inputs: { selector: string; type: string; label?: string }[] = [];
    const allInputs = document.querySelectorAll('input, textarea, select, [role="textbox"]');

    allInputs.forEach((input, index) => {
      const type = input.getAttribute('type') || input.tagName.toLowerCase();
      const label = input.getAttribute('aria-label') ?? undefined;
      const testId = input.getAttribute('data-testid');

      inputs.push({
        selector: testId ? `[data-testid="${testId}"]` : `input:nth-of-type(${index})`,
        type,
        label,
      });
    });

    return inputs;
  });
}

/**
 * Fill a form with test data
 */
export async function fillFormWithTestData(
  page: Page,
  formData: Record<string, string>
): Promise<void> {
  for (const [selector, value] of Object.entries(formData)) {
    const input = page.locator(selector).first();
    const inputType = await input.getAttribute('type');

    if (inputType === 'checkbox') {
      await input.check();
    } else if (inputType === 'radio') {
      await input.click();
    } else {
      await input.fill(value);
    }
  }
}

/**
 * Get all validation errors on page
 */
export async function getValidationErrors(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const errors: string[] = [];
    const errorElements = document.querySelectorAll(
      '[role="alert"], [aria-invalid="true"], .error, [aria-describedby*="error"]'
    );

    errorElements.forEach((el) => {
      const text = el.textContent?.trim();
      if (text) {
        errors.push(text);
      }
    });

    return errors;
  });
}

/**
 * Verify page is in expected state
 */
export async function verifyPageState(
  page: Page,
  expectations: {
    title?: string;
    hasMainContent?: boolean;
    hasNavigation?: boolean;
    hasFooter?: boolean;
  }
): Promise<boolean> {
  return page.evaluate((exp) => {
    let isValid = true;

    if (exp.title && document.title !== exp.title) {
      isValid = false;
    }

    if (exp.hasMainContent && !document.querySelector('main')) {
      isValid = false;
    }

    if (exp.hasNavigation && !document.querySelector('nav')) {
      isValid = false;
    }

    if (exp.hasFooter && !document.querySelector('footer')) {
      isValid = false;
    }

    return isValid;
  }, expectations);
}

/**
 * Get all interactive elements on page
 */
export async function getAllInteractiveElements(
  page: Page
): Promise<{ selector: string; type: string; label?: string; ariaLabel?: string }[]> {
  return page.evaluate(() => {
    const elements: { selector: string; type: string; label?: string; ariaLabel?: string }[] = [];
    const interactive = document.querySelectorAll(
      'button, a, input, [role="button"], [role="link"], [role="tab"], [role="menuitem"]'
    );

    interactive.forEach((el) => {
      const type = el.getAttribute('role') || el.tagName.toLowerCase();
      const ariaLabel = el.getAttribute('aria-label') ?? undefined;
      const label = el.textContent?.trim().substring(0, 50) || ariaLabel;

      elements.push({
        selector: el.className || type,
        type,
        label,
        ariaLabel,
      });
    });

    return elements;
  });
}

/**
 * Export test data for reporting
 */
export interface TestDataExport {
  timestamp: string;
  userCount: number;
  promptCount: number;
  categoryCount: number;
  tagCount: number;
}

export async function exportTestMetadata(request: APIRequestContext): Promise<TestDataExport> {
  const baseURL = getBaseURL();

  try {
    const [prompts, categories, tags] = await Promise.all([
      request.get(`${baseURL}/api/prompts`).then((r) => r.json()),
      request.get(`${baseURL}/api/categories`).then((r) => r.json()),
      request.get(`${baseURL}/api/tags`).then((r) => r.json()),
    ]);

    return {
      timestamp: new Date().toISOString(),
      userCount: 1, // Typically testing as single user
      promptCount: Array.isArray(prompts) ? prompts.length : 0,
      categoryCount: Array.isArray(categories) ? categories.length : 0,
      tagCount: Array.isArray(tags) ? tags.length : 0,
    };
  } catch (error) {
    console.warn('Error exporting test metadata:', error);
    return {
      timestamp: new Date().toISOString(),
      userCount: 0,
      promptCount: 0,
      categoryCount: 0,
      tagCount: 0,
    };
  }
}
