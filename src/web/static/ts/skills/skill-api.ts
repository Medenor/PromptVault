/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Typed client for the skills API (contracts/skills-api.md).
 *
 * Uploads use apiPostForm / apiPutForm, never apiFetch: apiFetch forces a
 * JSON Content-Type, which breaks multipart parsing on the server.
 */

import type { ItemResponse, SkillSummary } from '@/types';
import { APIRequestError, apiDelete, apiGet, apiPatch, apiPostForm, apiPutForm } from '@/utils/api';

export type { SkillSummary };

/** One stored file of a skill (no content). */
export interface SkillFileEntry {
  path: string;
  size: number;
  is_text: boolean;
  sha256: string;
}

/** A skill with its sanitised instructions and file list. */
export interface SkillDetail extends SkillSummary {
  note: string;
  /** Server-sanitised HTML of the SKILL.md body (frontmatter removed). */
  instructions_html: string;
  files: SkillFileEntry[];
}

/** Result of importing or replacing an archive. */
export interface SkillImportResult {
  skill: SkillDetail;
  warnings: string[];
}

/** Text preview of one stored file. */
export interface SkillFileContent {
  path: string;
  size: number;
  is_text: boolean;
  truncated: boolean;
  text: string | null;
}

/** Fields accepted by PATCH /api/skills/{id}. Only present fields are applied. */
export interface SkillUpdate {
  title?: string;
  category?: string | null;
  tags?: string[];
  note?: string;
  favorite?: boolean;
}

/** A structured API failure, already reduced to what the UI needs. */
export interface SkillApiError {
  /** Stable code from the API contract, or 'unknown'. */
  code: string;
  /** Developer-facing English message from the server (never shown as-is). */
  message: string;
  /** Archive entry that caused a rejection, if any. Show as text only. */
  offendingEntry: string | null;
  status: number;
}

/** True when a list item is a skill (never edit it as a prompt). */
export function isSkillItem(item: ItemResponse): item is SkillSummary {
  return item.item_type === 'skill';
}

interface ErrorDetail {
  code?: unknown;
  message?: unknown;
  offending_entry?: unknown;
}

/**
 * Reduce any thrown value to a SkillApiError.
 *
 * Reads the contract's `{detail: {code, message, offending_entry}}` body from
 * an APIRequestError; anything else becomes `code: 'unknown'`.
 */
export function toSkillApiError(error: unknown): SkillApiError {
  if (error instanceof APIRequestError) {
    const detail = error.error.detail as unknown;
    if (detail !== null && typeof detail === 'object' && !Array.isArray(detail)) {
      const body = detail as ErrorDetail;
      if (typeof body.code === 'string') {
        return {
          code: body.code,
          message: typeof body.message === 'string' ? body.message : error.message,
          offendingEntry: typeof body.offending_entry === 'string' ? body.offending_entry : null,
          status: error.status,
        };
      }
    }
    return { code: 'unknown', message: error.message, offendingEntry: null, status: error.status };
  }
  const message = error instanceof Error ? error.message : String(error);
  return { code: 'unknown', message, offendingEntry: null, status: 0 };
}

/** Import a skill from a .zip archive. Nothing is stored if it is rejected. */
export function importSkill(
  file: File,
  category?: string,
  tags?: string
): Promise<SkillImportResult> {
  const form = new FormData();
  form.append('archive', file);
  if (category) form.append('category', category);
  if (tags) form.append('tags', tags);
  return apiPostForm<SkillImportResult>('/api/skills/import', form);
}

/** Metadata, sanitised instructions and the file list of one skill. */
export function getSkill(id: number): Promise<SkillDetail> {
  return apiGet<SkillDetail>(`/api/skills/${id}`);
}

/** Text preview of one stored file. */
export function getSkillFileContent(id: number, path: string): Promise<SkillFileContent> {
  return apiGet<SkillFileContent>(
    `/api/skills/${id}/files/content?path=${encodeURIComponent(path)}`
  );
}

/** URL of the exact bytes of one file (served as an attachment). */
export function skillRawFileUrl(id: number, path: string): string {
  return `/api/skills/${id}/files/raw?path=${encodeURIComponent(path)}`;
}

/** URL that downloads the whole skill as `<identifier>.zip`. */
export function downloadSkillUrl(id: number): string {
  return `/api/skills/${id}/download`;
}

/** Edit title, category, tags, note or favorite. Never creates a version. */
export function updateSkill(id: number, changes: SkillUpdate): Promise<SkillDetail> {
  return apiPatch<SkillDetail>(`/api/skills/${id}`, changes);
}

/** Replace every file of a skill with a new archive (all or nothing). */
export function replaceSkillArchive(id: number, file: File): Promise<SkillImportResult> {
  const form = new FormData();
  form.append('archive', file);
  return apiPutForm<SkillImportResult>(`/api/skills/${id}/archive`, form);
}

/** Permanently delete a skill and its files. */
export function deleteSkill(id: number): Promise<void> {
  return apiDelete<void>(`/api/skills/${id}`);
}
