/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

export interface TagInfo {
  name: string;
  count: number;
  color?: string | null;
}

export interface CategoryItem {
  name: string;
  color?: string | null;
}

export interface TagItem {
  name: string;
  color?: string | null;
  usage_count?: number | null;
  count?: number | null;
}

export interface VersionSummary {
  version_id: string;
  version_number: number;
  timestamp: string;
  author: string;
  message: string;
  parents: string[];
  semantic_version: string | null;
}

export interface VersionHistoryResponse {
  versions: VersionSummary[];
}

export interface DiffOperation {
  op: 'equal' | 'delete' | 'insert';
  text: string;
}

export interface FieldChange {
  old: string | string[] | null;
  new: string | string[] | null;
  diff?: DiffOperation[];
}

export interface VersionDiffResponse {
  v1_id: string;
  v2_id: string;
  changes: Record<string, FieldChange>;
}

export interface VersionCacheEntry {
  timestamp: number;
  data: VersionHistoryResponse;
}

export interface DiffCacheEntry {
  timestamp: number;
  data: VersionDiffResponse;
}

export interface VersionSortItem {
  id: string;
  number: number;
}

export interface BulkDeleteResponse {
  success: boolean;
  deleted_count: number;
  failed_count: number;
  failed_ids: number[];
  detail?: string;
}

export type PromptId = string;

export type PromptFieldError = {
  fieldId: string;
  errorId: string;
  messageKey: import('@/types/i18n').TranslationKey;
};
