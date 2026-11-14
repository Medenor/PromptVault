/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Skill detail view (011-skill-packages): header with metadata, the rendered
 * instructions, a file tree beside a read-only file viewer, and the manage
 * actions (download, edit details, replace files, delete).
 *
 * Only `instructions_html`, which the server has already sanitised, is ever
 * inserted as HTML (through raw()). Everything else is set with textContent.
 */

import { createModal } from '@components';
import { t } from '@/utils/i18n';
import { confirmAsync } from '@/utils/dialogs';
import { createFocusTrap } from '@/utils/keyboard-nav';
import { showNotification } from '@/utils/notifications';
import { html, raw } from '@/utils/safe-html';
import { createTypeBadge } from './skill-card';
import {
  deleteSkill,
  downloadSkillUrl,
  getSkill,
  toSkillApiError,
  updateSkill,
  type SkillDetail,
  type SkillFileEntry,
  type SkillUpdate,
} from './skill-api';
import { createFileTree } from './skill-file-tree';
import { createFileViewer } from './skill-file-viewer';
import { describeSkillError, describeWarnings, formatBytes } from './skill-messages';
import { openSkillReplaceDialog } from './skill-import';

export interface SkillDetailOptions {
  /** Called after the skill was edited, replaced or deleted, so lists can refresh. */
  onChanged?: () => void;
  /** Use an already-fetched skill (for example right after an import). */
  initial?: SkillDetail;
}

export interface SkillDetailHandle {
  element: HTMLElement;
  close: () => void;
}

const BUTTON_BASE =
  'min-h-[44px] md:min-h-0 px-3 py-1.5 text-sm font-medium rounded-lg transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700';

function button(label: string, className: string): HTMLButtonElement {
  const el = document.createElement('button');
  el.type = 'button';
  el.className = `${BUTTON_BASE} ${className}`;
  el.textContent = label;
  return el;
}

function paragraph(text: string, className: string): HTMLParagraphElement {
  const p = document.createElement('p');
  p.className = className;
  p.textContent = text;
  return p;
}

function splitTags(value: string): string[] {
  return value
    .split(',')
    .map((tag) => tag.trim())
    .filter((tag) => tag !== '');
}

/** Open the detail view for a skill. */
export function openSkillDetail(
  skillId: number,
  options: SkillDetailOptions = {}
): SkillDetailHandle {
  const previousFocus =
    document.activeElement instanceof HTMLElement ? document.activeElement : null;

  const overlay = document.createElement('div');
  overlay.className = 'skill-detail-overlay fixed inset-0 z-40 bg-black/50 overflow-y-auto';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.dataset.skillId = String(skillId);

  const panel = document.createElement('div');
  panel.className =
    'skill-detail-panel relative mx-auto my-0 md:my-8 max-w-6xl bg-white dark:bg-gray-900 md:rounded-lg shadow-lg p-4 md:p-6 min-h-full md:min-h-0';
  overlay.appendChild(panel);

  const trap = createFocusTrap(overlay, { manageFocus: false });
  let closed = false;

  const close = (): void => {
    if (closed) return;
    closed = true;
    document.removeEventListener('keydown', onKeydown);
    trap.deactivate();
    overlay.remove();
    previousFocus?.focus?.();
  };

  function onKeydown(event: KeyboardEvent): void {
    // Dialogs stacked above the detail view (edit form, confirmations) handle Escape themselves.
    if (event.key === 'Escape' && document.querySelectorAll('[role="dialog"]').length <= 1) {
      event.preventDefault();
      close();
    }
  }
  document.addEventListener('keydown', onKeydown);

  const closeButton = button(
    t('skills.detail.close'),
    'skill-close-btn bg-gray-200 text-gray-900 hover:bg-gray-300'
  );
  closeButton.addEventListener('click', close);

  const showLoadError = (error: unknown): void => {
    const { message } = describeSkillError(toSkillApiError(error));
    panel.replaceChildren(
      paragraph(
        t('skills.detail.loadError'),
        'skill-load-error text-red-700 dark:text-red-400 mb-2'
      ),
      paragraph(message, 'text-sm text-gray-600 dark:text-gray-300 mb-4'),
      closeButton
    );
  };

  const reload = async (): Promise<void> => {
    try {
      render(await getSkill(skillId));
    } catch (error) {
      showLoadError(error);
    }
  };

  const changed = (): void => options.onChanged?.();

  function openEditForm(skill: SkillDetail): void {
    const form = document.createElement('form');
    form.noValidate = true;
    const inputs: Record<string, HTMLInputElement | HTMLTextAreaElement> = {};
    const addField = (
      name: string,
      labelText: string,
      value: string,
      element: HTMLInputElement | HTMLTextAreaElement
    ): void => {
      const wrapper = document.createElement('div');
      wrapper.className = 'mb-3';
      const label = document.createElement('label');
      element.id = `skill-edit-${name}`;
      label.htmlFor = element.id;
      label.className = 'block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1';
      label.textContent = labelText;
      element.value = value;
      element.className =
        'w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700';
      inputs[name] = element;
      wrapper.append(label, element);
      form.appendChild(wrapper);
    };
    addField('title', t('skills.edit.titleLabel'), skill.title, document.createElement('input'));
    addField(
      'category',
      t('skills.edit.categoryLabel'),
      skill.category,
      document.createElement('input')
    );
    addField(
      'tags',
      t('skills.edit.tagsLabel'),
      skill.tags.join(', '),
      document.createElement('input')
    );
    addField('note', t('skills.edit.noteLabel'), skill.note, document.createElement('textarea'));

    const favoriteWrapper = document.createElement('label');
    favoriteWrapper.className =
      'flex items-center gap-2 mb-3 text-sm text-gray-700 dark:text-gray-200';
    const favorite = document.createElement('input');
    favorite.type = 'checkbox';
    favorite.checked = Boolean(skill.favorite);
    favoriteWrapper.append(favorite, document.createTextNode(t('skills.edit.favoriteLabel')));
    form.appendChild(favoriteWrapper);

    const status = paragraph(
      '',
      'skill-edit-status text-sm text-red-700 dark:text-red-400 mb-3 hidden'
    );
    status.setAttribute('role', 'alert');
    form.appendChild(status);

    const buttons = document.createElement('div');
    buttons.className = 'flex justify-end gap-2';
    const cancel = button(t('skills.edit.cancel'), 'bg-gray-200 text-gray-900 hover:bg-gray-300');
    const save = button(t('skills.edit.save'), 'bg-blue-700 text-white hover:bg-blue-800');
    save.type = 'submit';
    buttons.append(cancel, save);
    form.appendChild(buttons);

    const modal = createModal({ title: t('skills.edit.title'), content: form, size: 'md' });
    const dispose = (): void => {
      modal.close();
      modal.element.remove();
    };
    cancel.addEventListener('click', dispose);

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const title = (inputs['title'] as HTMLInputElement).value.trim();
      if (title === '') {
        status.textContent = t('skills.edit.error');
        status.classList.remove('hidden');
        return;
      }
      const category = (inputs['category'] as HTMLInputElement).value.trim();
      const changes: SkillUpdate = {
        title,
        category: category === '' ? null : category,
        tags: splitTags((inputs['tags'] as HTMLInputElement).value),
        note: (inputs['note'] as HTMLTextAreaElement).value,
        favorite: favorite.checked,
      };
      save.disabled = true;
      void updateSkill(skill.id, changes)
        .then((updated) => {
          dispose();
          showNotification(t('skills.edit.saved'), 'success');
          render(updated);
          changed();
        })
        .catch(() => {
          status.textContent = t('skills.edit.error');
          status.classList.remove('hidden');
          save.disabled = false;
        });
    });

    document.body.appendChild(modal.element);
    modal.open();
  }

  async function confirmAndDelete(skill: SkillDetail): Promise<void> {
    const confirmed = await confirmAsync({
      title: t('skills.delete.confirmTitle'),
      message: t('skills.delete.confirmPermanent'),
      confirmLabel: t('skills.delete.confirmButton'),
      cancelLabel: t('skills.edit.cancel'),
    });
    if (!confirmed) return;
    try {
      await deleteSkill(skill.id);
      // Deleting a skill is permanent: no undo toast is offered (FR-023).
      showNotification(t('skills.delete.success'), 'success');
      close();
      changed();
    } catch {
      showNotification(t('skills.delete.error'), 'error');
    }
  }

  function render(skill: SkillDetail): void {
    const header = document.createElement('div');
    header.className = 'flex items-start justify-between gap-3 mb-4';
    const titleBlock = document.createElement('div');
    titleBlock.className = 'min-w-0';
    const heading = document.createElement('h2');
    heading.id = `skill-detail-title-${skill.id}`;
    heading.className =
      'skill-title text-2xl font-bold text-gray-900 dark:text-gray-100 break-words flex items-center flex-wrap gap-2';
    heading.append(document.createTextNode(skill.title), createTypeBadge('skill'));
    overlay.setAttribute('aria-labelledby', heading.id);
    titleBlock.appendChild(heading);
    titleBlock.appendChild(
      paragraph(
        skill.description || t('skills.detail.noDescription'),
        'skill-description text-sm text-gray-700 dark:text-gray-200 mt-1'
      )
    );
    header.append(titleBlock, closeButton);

    // Meta
    const meta = document.createElement('dl');
    meta.className =
      'skill-meta grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-sm text-gray-700 dark:text-gray-200 mb-4';
    const addMeta = (label: string, value: string): void => {
      if (!value) return;
      const row = document.createElement('div');
      row.className = 'flex gap-2';
      const dt = document.createElement('dt');
      dt.className = 'font-medium text-gray-500 dark:text-gray-400';
      dt.textContent = label;
      const dd = document.createElement('dd');
      dd.className = 'break-words';
      dd.textContent = value;
      row.append(dt, dd);
      meta.appendChild(row);
    };
    addMeta(t('skills.detail.identifier'), skill.skill_identifier);
    addMeta(t('skills.detail.category'), skill.category);
    addMeta(t('skills.detail.tags'), skill.tags.join(', '));
    addMeta(t('skills.detail.note'), skill.note);
    addMeta(
      t('skills.detail.filesHeading'),
      `${t('skills.detail.files', { count: skill.file_count })}, ${t('skills.detail.totalSize', { size: formatBytes(skill.total_bytes) })}`
    );

    // Warnings
    let warnings: HTMLElement | null = null;
    if (skill.format_warnings.length > 0) {
      warnings = document.createElement('div');
      warnings.className =
        'skill-warnings rounded-lg bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 text-sm mb-4';
      const warningHeading = document.createElement('p');
      warningHeading.className = 'font-semibold mb-1';
      warningHeading.textContent = t('skills.detail.warnings');
      const list = document.createElement('ul');
      list.className = 'list-disc pl-5';
      for (const line of describeWarnings(skill.format_warnings)) {
        const item = document.createElement('li');
        item.textContent = line;
        list.appendChild(item);
      }
      warnings.append(warningHeading, list);
    }

    // Actions
    const actions = document.createElement('div');
    actions.className = 'skill-actions flex flex-wrap gap-2 mb-6';
    const download = document.createElement('a');
    download.href = downloadSkillUrl(skill.id);
    download.className = `${BUTTON_BASE} skill-download-btn inline-flex items-center bg-blue-700 text-white hover:bg-blue-800`;
    download.textContent = t('skills.download.button');
    download.setAttribute('aria-label', t('skills.download.aria'));
    download.setAttribute('download', '');
    const edit = button(
      t('skills.edit.button'),
      'skill-edit-btn bg-gray-100 text-gray-800 hover:bg-gray-200'
    );
    const replace = button(
      t('skills.replace.button'),
      'skill-replace-btn bg-gray-100 text-gray-800 hover:bg-gray-200'
    );
    const remove = button(
      t('skills.delete.button'),
      'skill-delete-btn bg-red-100 text-red-700 hover:bg-red-200'
    );
    edit.addEventListener('click', () => openEditForm(skill));
    replace.addEventListener('click', () =>
      openSkillReplaceDialog(skill.id, (updated) => {
        render(updated);
        changed();
      })
    );
    remove.addEventListener('click', () => void confirmAndDelete(skill));
    actions.append(download, edit, replace, remove);

    // Instructions: the only HTML on this page, sanitised by the server.
    const instructions = document.createElement('section');
    instructions.className = 'mb-6';
    const instructionsHeading = document.createElement('h3');
    instructionsHeading.className = 'text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2';
    instructionsHeading.textContent = t('skills.detail.instructions');
    const body = document.createElement('div');
    body.className = 'skill-instructions max-w-none text-sm text-gray-800 dark:text-gray-100';
    // eslint-disable-next-line no-restricted-properties -- instructions_html is sanitised server-side (markdown-it with raw HTML off, then nh3 allow-list)
    body.innerHTML = html`${raw(skill.instructions_html)}`;
    instructions.append(instructionsHeading, body);

    // Files: tree beside viewer on large screens, stacked on small ones.
    const filesSection = document.createElement('section');
    const filesHeading = document.createElement('h3');
    filesHeading.className = 'text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2';
    filesHeading.textContent = t('skills.detail.filesHeading');
    const layout = document.createElement('div');
    layout.className = 'grid grid-cols-1 lg:grid-cols-[minmax(14rem,1fr)_2fr] gap-4';
    const viewer = createFileViewer();
    const tree = createFileTree(skill.files, {
      onSelect: (path) => {
        const entry = skill.files.find((file: SkillFileEntry) => file.path === path);
        if (entry) void viewer.show(skill.id, entry);
      },
    });
    const treeWrapper = document.createElement('div');
    treeWrapper.className =
      'rounded-lg border border-gray-200 dark:border-gray-700 p-2 max-h-[60vh] overflow-auto';
    treeWrapper.appendChild(tree.element);
    layout.append(treeWrapper, viewer.element);
    filesSection.append(filesHeading, layout);

    panel.replaceChildren(header, meta);
    if (warnings) panel.appendChild(warnings);
    panel.append(actions, instructions, filesSection);

    // Start on SKILL.md, the entry point, when it is there.
    const entry = skill.files.find((file) => file.path === 'SKILL.md');
    if (entry) {
      tree.select(entry.path);
      void viewer.show(skill.id, entry);
    }
  }

  // Loading state, then the data.
  panel.appendChild(
    paragraph(t('skills.detail.loading'), 'skill-loading text-sm text-gray-600 dark:text-gray-300')
  );
  document.body.appendChild(overlay);
  trap.activate();
  overlay.setAttribute('aria-label', t('skills.detail.loading'));

  if (options.initial) {
    render(options.initial);
  } else {
    void reload();
  }

  return { element: overlay, close };
}
