/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Archive upload dialogs for skills (011-skill-packages): import a new skill
 * and replace the files of an existing one. Both share one form.
 *
 * Every message is written with textContent. Rejection text comes from the
 * error code (translated), and the offending archive entry is shown as plain
 * text, never as HTML.
 */

import { createModal } from '@components';
import { apiGet } from '@/utils/api';
import { t } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';
import {
  importSkill,
  replaceSkillArchive,
  toSkillApiError,
  type SkillDetail,
  type SkillImportResult,
} from './skill-api';
import { describeSkillError, describeWarnings } from './skill-messages';

export type ImportedCallback = (skill: SkillDetail, warnings: string[]) => void;

interface ArchiveDialogOptions {
  title: string;
  description: string;
  submitLabel: string;
  successMessage: string;
  /** Show the optional category and tags fields (import only). */
  withMetadata: boolean;
  upload: (file: File, category: string, tags: string) => Promise<SkillImportResult>;
  onDone: ImportedCallback;
}

/** Show a non-blocking notice that lists the format warnings, if any. */
export function notifyWarnings(warnings: readonly string[]): void {
  if (warnings.length === 0) return;
  const lines = describeWarnings(warnings).map((line) => `• ${line}`);
  showNotification(`${t('skills.import.warningsTitle')}\n${lines.join('\n')}`, 'warning');
}

const CONTROL_CLASS =
  'w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700';

// The native file picker keeps its browser behaviour; only its button and the
// frame around it are styled, to match the other form controls.
const FILE_CONTROL_CLASS =
  'block w-full cursor-pointer rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700 file:mr-3 file:cursor-pointer file:border-0 file:border-r file:border-gray-300 dark:file:border-gray-600 file:bg-gray-100 dark:file:bg-gray-700 file:px-4 file:py-2 file:text-sm file:font-medium file:text-gray-900 dark:file:text-gray-100 hover:file:bg-gray-200 dark:hover:file:bg-gray-600';

const TAG_CHIP_BASE =
  'skill-tag-chip px-2.5 py-1 text-xs font-medium rounded-full border focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700';
const TAG_CHIP_OFF =
  'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700';
const TAG_CHIP_ON = 'bg-blue-700 text-white border-blue-700 hover:bg-blue-800';

function field(
  labelText: string,
  control: HTMLInputElement | HTMLSelectElement,
  controlClass: string = CONTROL_CLASS
): HTMLDivElement {
  const wrapper = document.createElement('div');
  wrapper.className = 'mb-3';
  const label = document.createElement('label');
  label.className = 'block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1';
  control.id = control.id || `skill-field-${Math.random().toString(36).slice(2, 8)}`;
  label.htmlFor = control.id;
  label.textContent = labelText;
  control.className = controlClass;
  wrapper.append(label, control);
  return wrapper;
}

/** Split a comma-separated tag string into trimmed, non-empty names. */
function splitTags(value: string): string[] {
  return value
    .split(',')
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0);
}

/** Existing categories, in the order the server returns them. Never throws. */
async function loadCategories(): Promise<string[]> {
  try {
    const data = await apiGet<{ categories?: string[] }>('/api/categories');
    return data.categories ?? [];
  } catch {
    return [];
  }
}

/** Existing tag names. Never throws: the field stays usable as free text. */
async function loadTagNames(): Promise<string[]> {
  try {
    const data = await apiGet<{ tags?: Array<{ name: string }> }>('/api/tags');
    return (data.tags ?? []).map((tag) => tag.name);
  } catch {
    return [];
  }
}

/** Fill the category `<select>` once the existing categories are known. */
function fillCategories(select: HTMLSelectElement, categories: readonly string[]): void {
  for (const name of categories) {
    const option = document.createElement('option');
    option.value = name;
    option.textContent = name;
    select.appendChild(option);
  }
}

/**
 * Show the existing tags as toggle chips under the free-text tags field.
 * Clicking a chip adds or removes that tag in the field; typing in the field
 * keeps the chips in sync.
 */
function mountTagChips(
  container: HTMLElement,
  input: HTMLInputElement,
  tagNames: readonly string[]
): void {
  if (tagNames.length === 0) return;

  const hint = document.createElement('p');
  hint.className = 'text-xs text-gray-600 dark:text-gray-300 mt-2 mb-1';
  hint.textContent = t('skills.import.tagsSuggestions');
  const chips = document.createElement('div');
  chips.className = 'flex flex-wrap gap-1.5 max-h-28 overflow-y-auto';

  const buttons = new Map<string, HTMLButtonElement>();
  const paint = (): void => {
    const selected = new Set(splitTags(input.value).map((tag) => tag.toLowerCase()));
    for (const [name, button] of buttons) {
      const on = selected.has(name.toLowerCase());
      button.setAttribute('aria-pressed', String(on));
      button.className = `${TAG_CHIP_BASE} ${on ? TAG_CHIP_ON : TAG_CHIP_OFF}`;
    }
  };

  for (const name of tagNames) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = name;
    button.addEventListener('click', () => {
      const current = splitTags(input.value);
      const key = name.toLowerCase();
      const next = current.some((tag) => tag.toLowerCase() === key)
        ? current.filter((tag) => tag.toLowerCase() !== key)
        : [...current, name];
      input.value = next.join(', ');
      paint();
    });
    buttons.set(name, button);
    chips.appendChild(button);
  }

  input.addEventListener('input', paint);
  paint();
  container.append(hint, chips);
}

function openArchiveDialog(options: ArchiveDialogOptions): void {
  const form = document.createElement('form');
  form.className = 'skill-archive-form';
  form.noValidate = true;

  const description = document.createElement('p');
  description.className = 'text-sm text-gray-600 dark:text-gray-300 mb-4';
  description.textContent = options.description;
  form.appendChild(description);

  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.name = 'archive';
  fileInput.accept = '.zip,application/zip';
  form.appendChild(field(t('skills.import.fileLabel'), fileInput, FILE_CONTROL_CLASS));

  const categorySelect = document.createElement('select');
  categorySelect.name = 'category';
  const noCategory = document.createElement('option');
  noCategory.value = '';
  noCategory.textContent = t('skills.import.noCategory');
  categorySelect.appendChild(noCategory);
  const tagsInput = document.createElement('input');
  tagsInput.type = 'text';
  tagsInput.name = 'tags';
  if (options.withMetadata) {
    form.appendChild(field(t('skills.import.categoryLabel'), categorySelect));
    const tagsField = field(t('skills.import.tagsLabel'), tagsInput);
    form.appendChild(tagsField);
    // Existing categories and tags arrive after the dialog is shown; until
    // then (or if the lookup fails) the fields still work.
    void loadCategories().then((categories) => fillCategories(categorySelect, categories));
    void loadTagNames().then((names) => mountTagChips(tagsField, tagsInput, names));
  }

  const status = document.createElement('div');
  status.className = 'skill-archive-status text-sm mb-3 hidden';
  status.setAttribute('role', 'alert');
  form.appendChild(status);

  const buttons = document.createElement('div');
  buttons.className = 'flex justify-end gap-2';
  const cancel = document.createElement('button');
  cancel.type = 'button';
  cancel.className =
    'px-4 py-2 text-sm font-medium rounded-md bg-gray-200 text-gray-900 hover:bg-gray-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-500';
  cancel.textContent = t('skills.import.cancel');
  const submit = document.createElement('button');
  submit.type = 'submit';
  submit.className =
    'px-4 py-2 text-sm font-medium rounded-md bg-blue-700 text-white hover:bg-blue-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700 disabled:opacity-60';
  submit.textContent = options.submitLabel;
  buttons.append(cancel, submit);
  form.appendChild(buttons);

  const modal = createModal({ title: options.title, content: form, size: 'md' });
  const dispose = (): void => {
    modal.close();
    modal.element.remove();
  };

  const showStatus = (text: string, entry: string | null = null): void => {
    status.replaceChildren();
    const message = document.createElement('p');
    message.className = 'text-red-700 dark:text-red-400';
    message.textContent = text;
    status.appendChild(message);
    if (entry) {
      const detail = document.createElement('p');
      detail.className = 'skill-archive-entry text-xs text-gray-600 dark:text-gray-300 break-all';
      detail.textContent = entry;
      status.appendChild(detail);
    }
    status.classList.remove('hidden');
  };

  cancel.addEventListener('click', dispose);

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const file = fileInput.files?.[0];
    if (!file) {
      showStatus(t('skills.import.selectFile'));
      return;
    }
    if (!file.name.toLowerCase().endsWith('.zip')) {
      showStatus(t('skills.import.onlyZip'));
      return;
    }

    status.classList.add('hidden');
    submit.disabled = true;
    cancel.disabled = true;
    submit.textContent = t('skills.import.uploading');

    void options
      .upload(file, categorySelect.value.trim(), tagsInput.value.trim())
      .then((result) => {
        dispose();
        showNotification(options.successMessage, 'success');
        notifyWarnings(result.warnings);
        options.onDone(result.skill, result.warnings);
      })
      .catch((error: unknown) => {
        const { message, entry } = describeSkillError(toSkillApiError(error));
        showStatus(message, entry);
        submit.disabled = false;
        cancel.disabled = false;
        submit.textContent = options.submitLabel;
      });
  });

  document.body.appendChild(modal.element);
  modal.open();
}

/** Open the "Import skill" dialog. `onImported` receives the new skill. */
export function openSkillImportDialog(onImported: ImportedCallback): void {
  openArchiveDialog({
    title: t('skills.import.title'),
    description: t('skills.import.description'),
    submitLabel: t('skills.import.submit'),
    successMessage: t('skills.import.success'),
    withMetadata: true,
    upload: (file, category, tags) => importSkill(file, category, tags),
    onDone: onImported,
  });
}

/** Open the "Replace files" dialog for an existing skill. */
export function openSkillReplaceDialog(skillId: number, onReplaced: ImportedCallback): void {
  openArchiveDialog({
    title: t('skills.replace.title'),
    description: t('skills.replace.description'),
    submitLabel: t('skills.replace.submit'),
    successMessage: t('skills.replace.success'),
    withMetadata: false,
    upload: (file) => replaceSkillArchive(skillId, file),
    onDone: onReplaced,
  });
}
