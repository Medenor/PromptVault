/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Read-only viewer for one stored skill file (011-skill-packages, FR-016/017).
 *
 * Text goes into a <pre> through textContent: bundled content is never
 * parsed as HTML or run. Binary files, and text that was truncated, show the
 * name, size and a download link instead. Nothing here edits a file.
 */

import { t } from '@/utils/i18n';
import {
  getSkillFileContent,
  skillRawFileUrl,
  toSkillApiError,
  type SkillFileEntry,
} from './skill-api';
import { describeSkillError, formatBytes } from './skill-messages';

export interface FileViewerHandle {
  element: HTMLElement;
  /** Show a file of the given skill. Resolves once it has rendered. */
  show: (skillId: number, entry: SkillFileEntry) => Promise<void>;
  /** Return to the "select a file" state. */
  clear: () => void;
}

export function createFileViewer(): FileViewerHandle {
  const root = document.createElement('section');
  root.className = 'skill-file-viewer min-w-0';
  root.setAttribute('aria-label', t('skills.viewer.region'));
  root.setAttribute('aria-live', 'polite');

  let requestId = 0;

  const setContent = (...nodes: Node[]): void => {
    root.replaceChildren(...nodes);
  };

  const message = (text: string, tone: 'info' | 'error' = 'info'): HTMLParagraphElement => {
    const p = document.createElement('p');
    p.className =
      tone === 'error'
        ? 'text-sm text-red-700 dark:text-red-400'
        : 'text-sm text-gray-600 dark:text-gray-300';
    p.textContent = text;
    return p;
  };

  const header = (skillId: number, entry: SkillFileEntry): HTMLElement => {
    const bar = document.createElement('div');
    bar.className = 'flex flex-wrap items-center justify-between gap-2 mb-2';
    const info = document.createElement('div');
    const name = document.createElement('h4');
    name.className = 'viewer-name font-semibold text-gray-900 dark:text-gray-100 break-all';
    name.textContent = entry.path;
    const size = document.createElement('p');
    size.className = 'viewer-size text-xs text-gray-500 dark:text-gray-400';
    size.textContent = t('skills.viewer.size', { size: formatBytes(entry.size) });
    info.append(name, size);

    const link = document.createElement('a');
    link.className =
      'viewer-download px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-800 hover:bg-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700';
    link.href = skillRawFileUrl(skillId, entry.path);
    link.setAttribute('download', '');
    link.textContent = t('skills.viewer.download');
    bar.append(info, link);
    return bar;
  };

  const clear = (): void => {
    requestId += 1;
    setContent(message(t('skills.viewer.empty')));
  };

  const show = async (skillId: number, entry: SkillFileEntry): Promise<void> => {
    requestId += 1;
    const current = requestId;
    const bar = header(skillId, entry);

    if (!entry.is_text) {
      setContent(bar, message(t('skills.viewer.binary')));
      return;
    }

    setContent(bar, message(t('skills.viewer.loading')));
    try {
      const content = await getSkillFileContent(skillId, entry.path);
      if (current !== requestId) return; // a newer selection replaced this one

      const pre = document.createElement('pre');
      pre.className =
        'viewer-text max-h-[60vh] overflow-auto rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-3 text-xs text-gray-800 dark:text-gray-100 whitespace-pre-wrap break-words';
      pre.tabIndex = 0;
      pre.textContent = content.text ?? '';
      const nodes: Node[] = [bar];
      if (content.truncated) {
        const notice = message(t('skills.viewer.truncated'));
        notice.classList.add('viewer-truncated', 'mb-2');
        nodes.push(notice);
      }
      nodes.push(pre);
      setContent(...nodes);
    } catch (error) {
      if (current !== requestId) return;
      const text = describeSkillError(toSkillApiError(error)).message || t('skills.viewer.error');
      setContent(bar, message(text, 'error'));
    }
  };

  clear();
  return { element: root, show, clear };
}
