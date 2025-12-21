/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

type Join<K extends string, P extends string> = P extends '' ? K : `${K}.${P}`;

type NestedKeys<T> = {
  [K in keyof T & string]: T[K] extends readonly unknown[]
    ? K
    : T[K] extends Record<string, unknown>
      ? Join<K, NestedKeys<T[K]>>
      : K;
}[keyof T & string];

type EnLocale = typeof import('../../locales/en.json');

export type TranslationKey = NestedKeys<EnLocale>;
