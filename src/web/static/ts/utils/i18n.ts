/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * i18next initialization and utilities
 */

import i18next from 'i18next';
import Backend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import type { TranslationKey } from '@/types/i18n';

type InitCallback = () => void;

/**
 * Update all elements with data-i18n attribute
 */
export function updateStaticTranslations(): void {
  document.querySelectorAll('[data-i18n]').forEach((element) => {
    const key = element.getAttribute('data-i18n');
    if (!key) return;

    if (key.includes('[') && key.includes(']')) {
      // Support attribute names containing dashes, e.g. `[aria-label]actions.close`.
      const match = key.match(/\[([^\]]+)\](.+)/);
      if (match) {
        const [, attribute, translationKey] = match;
        if (!translationKey) {
          return;
        }
        const translation = tUnsafe(translationKey);
        if (translation && attribute) {
          element.setAttribute(attribute.trim(), translation);
        }
      }
    } else {
      element.textContent = tUnsafe(key);
    }
  });

  document.querySelectorAll('[data-i18n-placeholder]').forEach((element) => {
    const key = element.getAttribute('data-i18n-placeholder');
    if (key && element instanceof HTMLInputElement) {
      element.placeholder = tUnsafe(key);
    }
  });

  document.querySelectorAll('[data-i18n-title]').forEach((element) => {
    const key = element.getAttribute('data-i18n-title');
    if (key && element instanceof HTMLElement) {
      element.title = tUnsafe(key);
    }
  });

  const languageSelector = document.getElementById('language-selector');
  if (languageSelector instanceof HTMLSelectElement) {
    languageSelector.value = i18next.language;
  }
}

/**
 * Initialize i18next with standard configuration
 */
export function initI18n(callback: InitCallback): void {
  i18next
    .use(Backend)
    .use(LanguageDetector)
    .init(
      {
        fallbackLng: 'en',
        supportedLngs: ['en', 'fr', 'es', 'de'],
        debug: false,
        backend: {
          loadPath: '/static/locales/{{lng}}.json',
        },
        detection: {
          order: ['localStorage', 'navigator', 'htmlTag'],
          caches: ['localStorage'],
        },
      },
      (err: Error | null) => {
        if (err) {
          // Error is already logged by i18next, just proceed with callback
        }

        if (document.readyState === 'loading') {
          document.addEventListener('DOMContentLoaded', callback);
        } else {
          callback();
        }
      }
    );
}

/**
 * Change the current language
 */
export function changeLanguage(lang: string): Promise<void> {
  return new Promise((resolve, reject) => {
    i18next.changeLanguage(lang, (err) => {
      if (err) {
        reject(err);
      } else {
        updateStaticTranslations();
        resolve();
      }
    });
  });
}

/**
 * Get current language
 */
export function getCurrentLanguage(): string {
  return i18next.language;
}

/**
 * Translate a key with optional interpolation
 */
export function t(key: TranslationKey, options?: Record<string, unknown>): string {
  if (options) {
    return i18next.t(key, options);
  }
  return i18next.t(key);
}

export function tUnsafe(key: string, options?: Record<string, unknown>): string {
  if (options) {
    return i18next.t(key, options);
  }
  return i18next.t(key);
}
