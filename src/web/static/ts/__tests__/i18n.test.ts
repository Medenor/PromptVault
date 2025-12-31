import { describe, expect, it, vi } from 'vitest';

const i18nMocks = vi.hoisted(() => {
  const tMock = vi.fn((key: string) => `tr:${key}`);
  const changeLanguageMock = vi.fn((_lang: string, cb?: (err?: Error | null) => void) =>
    cb?.(null)
  );
  const initMock = vi.fn((_opts: unknown, cb?: (err?: Error | null) => void) => cb?.(null));
  const useMock = vi.fn(() => ({
    use: useMock,
    init: initMock,
  }));

  return {
    tMock,
    changeLanguageMock,
    initMock,
    useMock,
  };
});

vi.mock('i18next', () => ({
  default: {
    t: i18nMocks.tMock,
    language: 'en',
    changeLanguage: i18nMocks.changeLanguageMock,
    use: i18nMocks.useMock,
    init: i18nMocks.initMock,
  },
}));

import { changeLanguage, initI18n, t, updateStaticTranslations } from '@/utils/i18n';

describe('i18n utils', () => {
  it('translates keys with and without options', () => {
    expect(t('nav.newPrompt')).toBe('tr:nav.newPrompt');
    expect(t('nav.newPrompt', { name: 'world' })).toBe('tr:nav.newPrompt');
  });

  it('updates static translations in the DOM', () => {
    document.body.innerHTML = `
      <div data-i18n="nav.prompts"></div>
      <input data-i18n-placeholder="nav.searchPlaceholder" />
      <span data-i18n-title="actions.delete"></span>
      <button data-i18n="[title]actions.refresh"></button>
      <select id="language-selector">
        <option value="en">English</option>
      </select>
    `;

    updateStaticTranslations();

    const textNode = document.querySelector('[data-i18n="nav.prompts"]');
    const input = document.querySelector('[data-i18n-placeholder]') as HTMLInputElement | null;
    const titled = document.querySelector('[data-i18n-title]') as HTMLElement | null;
    const tooltip = document.querySelector('button[data-i18n]') as HTMLElement | null;
    const selector = document.getElementById('language-selector') as HTMLSelectElement | null;

    expect(textNode?.textContent).toBe('tr:nav.prompts');
    expect(input?.placeholder).toBe('tr:nav.searchPlaceholder');
    expect(titled?.title).toBe('tr:actions.delete');
    expect(tooltip?.getAttribute('title')).toBe('tr:actions.refresh');
    expect(selector?.value).toBe('en');
  });

  it('initializes and resolves language changes', async () => {
    Object.defineProperty(document, 'readyState', {
      value: 'complete',
      configurable: true,
    });
    const callback = vi.fn();
    initI18n(callback);
    expect(callback).toHaveBeenCalled();

    await expect(changeLanguage('fr')).resolves.toBeUndefined();
    expect(i18nMocks.changeLanguageMock).toHaveBeenCalledWith('fr', expect.any(Function));
  });
});
