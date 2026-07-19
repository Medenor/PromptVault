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

import {
  changeLanguage,
  getCurrentLanguage,
  initI18n,
  t,
  tUnsafe,
  updateStaticTranslations,
} from '@/utils/i18n';

describe('i18n utils', () => {
  it('translates keys with and without options', () => {
    expect(t('nav.newPrompt')).toBe('tr:nav.newPrompt');
    expect(t('nav.newPrompt', { name: 'world' })).toBe('tr:nav.newPrompt');
    expect(tUnsafe('any.key')).toBe('tr:any.key');
    expect(tUnsafe('any.key', { count: 1 })).toBe('tr:any.key');
  });

  it('returns the current language', () => {
    expect(getCurrentLanguage()).toBe('en');
  });

  it('updates static translations in the DOM', () => {
    document.body.innerHTML = `
      <div data-i18n="nav.prompts"></div>
      <div data-i18n=""></div>
      <div data-i18n="[invalid"></div>
      <div data-i18n="[]missingAttribute"></div>
      <input data-i18n-placeholder="nav.searchPlaceholder" />
      <input data-i18n-placeholder="" />
      <span data-i18n-title="actions.delete"></span>
      <span data-i18n-title=""></span>
      <button data-i18n="[title]actions.refresh"></button>
      <button data-i18n-aria-label="actions.close"></button>
      <button data-i18n-aria-label=""></button>
      <select class="language-selector">
        <option value="en">English</option>
      </select>
    `;

    updateStaticTranslations();

    const textNode = document.querySelector('[data-i18n="nav.prompts"]');
    const input = document.querySelector(
      'input[data-i18n-placeholder="nav.searchPlaceholder"]'
    ) as HTMLInputElement | null;
    const titled = document.querySelector(
      '[data-i18n-title="actions.delete"]'
    ) as HTMLElement | null;
    const tooltip = document.querySelector('button[data-i18n]') as HTMLElement | null;
    const ariaLabelled = document.querySelector(
      '[data-i18n-aria-label="actions.close"]'
    ) as HTMLElement | null;
    const selector = document.querySelector('.language-selector') as HTMLSelectElement | null;

    expect(textNode?.textContent).toBe('tr:nav.prompts');
    expect(input?.placeholder).toBe('tr:nav.searchPlaceholder');
    expect(titled?.title).toBe('tr:actions.delete');
    expect(tooltip?.getAttribute('title')).toBe('tr:actions.refresh');
    expect(ariaLabelled?.getAttribute('aria-label')).toBe('tr:actions.close');
    expect(selector?.value).toBe('en');
  });

  it('initializes immediately when the document is already ready', () => {
    Object.defineProperty(document, 'readyState', {
      value: 'complete',
      configurable: true,
    });
    const callback = vi.fn();
    initI18n(callback);
    expect(callback).toHaveBeenCalled();
  });

  it('waits for DOMContentLoaded when the document is still loading', () => {
    Object.defineProperty(document, 'readyState', {
      value: 'loading',
      configurable: true,
    });
    const callback = vi.fn();
    initI18n(callback);
    expect(callback).not.toHaveBeenCalled();

    document.dispatchEvent(new Event('DOMContentLoaded'));
    expect(callback).toHaveBeenCalled();

    Object.defineProperty(document, 'readyState', {
      value: 'complete',
      configurable: true,
    });
  });

  it('proceeds even when i18next reports an init error', () => {
    Object.defineProperty(document, 'readyState', {
      value: 'complete',
      configurable: true,
    });
    i18nMocks.initMock.mockImplementationOnce((_opts: unknown, cb?: (err?: Error) => void) =>
      cb?.(new Error('init failed'))
    );
    const callback = vi.fn();
    initI18n(callback);
    expect(callback).toHaveBeenCalled();
  });

  it('wires up language selector change events', () => {
    Object.defineProperty(document, 'readyState', {
      value: 'complete',
      configurable: true,
    });
    document.body.innerHTML = `
      <select class="language-selector">
        <option value="en">English</option>
        <option value="fr">Français</option>
      </select>
    `;

    initI18n(vi.fn());

    const selector = document.querySelector('.language-selector') as HTMLSelectElement;
    selector.value = 'fr';
    selector.dispatchEvent(new Event('change'));

    expect(i18nMocks.changeLanguageMock).toHaveBeenCalledWith('fr', expect.any(Function));
  });

  it('resolves language changes', async () => {
    await expect(changeLanguage('fr')).resolves.toBeUndefined();
    expect(i18nMocks.changeLanguageMock).toHaveBeenCalledWith('fr', expect.any(Function));
  });

  it('rejects when i18next fails to change language', async () => {
    i18nMocks.changeLanguageMock.mockImplementationOnce(
      (_lang: string, cb?: (err?: Error | null) => void) => cb?.(new Error('change failed'))
    );

    await expect(changeLanguage('fr')).rejects.toThrow('change failed');
  });
});
