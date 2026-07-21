/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

export type CategoryItem = {
  id: number;
  name: string;
  description?: string | null;
  color?: string | null;
  sort_order?: number | null;
  usage_count: number;
};

export type CategoryListResponse = {
  items: CategoryItem[];
};

export type FormValidationError = {
  inputId: string;
  errorId: string;
  message: string;
};

export type OrphanPromptDetailsResponse = {
  items: Array<{ id: number; title: string }>;
  count: number;
};
