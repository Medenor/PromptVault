/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * List card for a skill (011-skill-packages).
 *
 * A skill card shows the escaped description instead of a prompt body, and
 * deliberately offers only Open, Favorite and Delete. Copy, placeholders,
 * version history and sharing are prompt-only. Clicks, taps and keyboard
 * activation open the skill detail view; none of them reach prompt editing.
 *
 * Built with createElement/textContent only: every value comes from the
 * server and from archive contents, so nothing is interpolated into HTML.
 */

import type { SkillSummary } from '@/types';
import { t } from '@/utils/i18n';
import { selectedPromptIds, handleCheckboxChange } from '@/app/bulk-actions';
import {
  buildPillStyleFilled,
  buildPillStyleOutline,
  getCategoryColorMap,
  getTagColorMap,
} from '@/app/colors';
import { describeWarnings, formatBytes } from './skill-messages';

const SNIPPET_MATCH_START = '[[MATCH]]';
const SNIPPET_MATCH_END = '[[/MATCH]]';

export interface SkillCardHandlers {
  /** Open the skill detail view. */
  onOpen: (id: number) => void;
  onDelete: (id: string) => void;
  onToggleFavorite: (id: string) => void;
  /** Remember the id for keyboard shortcuts. */
  onSelect: (id: number) => void;
}

/** Type badge shared by prompt and skill cards. */
export function createTypeBadge(itemType: 'prompt' | 'skill'): HTMLSpanElement {
  const badge = document.createElement('span');
  const label = t(`skills.badge.${itemType}`);
  badge.dataset.itemType = itemType;
  badge.className =
    itemType === 'skill'
      ? 'type-badge px-2 py-0.5 text-xs font-semibold rounded-full bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100'
      : 'type-badge px-2 py-0.5 text-xs font-semibold rounded-full bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200';
  badge.textContent = label;
  badge.setAttribute('aria-label', label);
  return badge;
}

/**
 * Render a ranked-search snippet as text nodes plus <mark> elements.
 * The sentinels never reach the DOM and the text is never parsed as HTML.
 */
function appendSnippet(target: HTMLElement, snippet: string): void {
  let marked = false;
  for (const chunk of snippet.split(new RegExp(`(\\[\\[/?MATCH\\]\\])`))) {
    if (chunk === SNIPPET_MATCH_START) {
      marked = true;
    } else if (chunk === SNIPPET_MATCH_END) {
      marked = false;
    } else if (chunk) {
      if (marked) {
        const mark = document.createElement('mark');
        mark.textContent = chunk;
        target.appendChild(mark);
      } else {
        target.appendChild(document.createTextNode(chunk));
      }
    }
  }
}

function pill(text: string, className: string, style: string): HTMLSpanElement {
  const span = document.createElement('span');
  span.className = className;
  span.textContent = text;
  if (style) {
    // buildPill* return a ` style="..."` attribute string; apply the value.
    const match = /style="([^"]*)"/.exec(style);
    if (match?.[1]) span.setAttribute('style', match[1]);
  }
  return span;
}

function actionButton(label: string, className: string, onClick: () => void): HTMLButtonElement {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `${className} min-h-[44px] md:min-h-0 px-3 py-1.5 text-xs font-medium rounded-lg transition-all hover:scale-105 active:scale-95`;
  button.textContent = label;
  button.title = label;
  button.addEventListener('click', (event) => {
    event.stopPropagation();
    onClick();
  });
  return button;
}

/** Build the card for one skill in the vault list. */
export function createSkillElement(
  id: string,
  skill: SkillSummary,
  handlers: SkillCardHandlers
): HTMLDivElement {
  const numericId = parseInt(id, 10);
  const div = document.createElement('div');
  div.className =
    'prompt-item skill-item bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 transition-all hover:scale-[1.02] cursor-pointer';
  div.dataset.id = id;
  div.dataset.itemType = 'skill';
  div.dataset.navLabel = skill.title || '';
  if (selectedPromptIds.has(numericId)) div.classList.add('selected');

  const hasPermission = skill.permission !== undefined && skill.permission !== null;
  const isOwner = !hasPermission || skill.permission === 'owner';

  // Header: checkbox, title, type badge, favorite
  const header = document.createElement('div');
  header.className = 'flex items-start justify-between mb-3';

  const titleId = `prompt-title-${id}`;
  const heading = document.createElement('h4');
  heading.id = titleId;
  heading.className =
    'text-prompt-title font-semibold text-gray-900 dark:text-gray-100 flex-1 flex items-center flex-wrap gap-1';
  heading.append(document.createTextNode(skill.title), createTypeBadge('skill'));
  header.appendChild(heading);

  const actions = document.createElement('div');
  actions.className = 'flex items-center gap-1 ml-2';
  actions.id = `prompt-actions-${id}`;

  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.className =
    'prompt-checkbox w-5 h-5 md:w-4 md:h-4 rounded text-blue-500 focus:ring-blue-500';
  checkbox.dataset.promptId = id;
  checkbox.setAttribute('aria-labelledby', titleId);
  checkbox.checked = selectedPromptIds.has(numericId);
  checkbox.addEventListener('change', (event) => {
    handleCheckboxChange(numericId, (event.target as HTMLInputElement | null)?.checked ?? false);
    event.stopPropagation();
  });
  actions.appendChild(checkbox);

  if (isOwner) {
    const favorite = document.createElement('button');
    favorite.type = 'button';
    favorite.className =
      'favorite-btn flex items-center justify-center min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 text-xl hover:scale-110 transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700 rounded';
    favorite.dataset.id = id;
    favorite.textContent = skill.favorite ? '★' : '☆';
    const label = skill.favorite ? t('actions.removeFavorite') : t('actions.addFavorite');
    favorite.setAttribute('aria-pressed', skill.favorite ? 'true' : 'false');
    favorite.setAttribute('aria-label', label);
    favorite.title = label;
    favorite.addEventListener('click', (event) => {
      event.stopPropagation();
      handlers.onSelect(numericId);
      handlers.onToggleFavorite(id);
    });
    actions.appendChild(favorite);
  }
  header.appendChild(actions);
  div.appendChild(header);

  // Ranked-search snippet
  if (skill.match_context) {
    const snippet = document.createElement('p');
    snippet.className =
      'prompt-match-context text-prompt-body text-gray-500 dark:text-gray-400 mb-2 italic';
    appendSnippet(snippet, skill.match_context);
    div.appendChild(snippet);
  }

  // Category and tags
  const pills = document.createElement('div');
  pills.className = 'flex flex-wrap gap-2 mb-3';
  const categoryColor = skill.category_color ?? getCategoryColorMap()[skill.category];
  const categoryPill = pill(
    skill.category || t('categories.noCategory'),
    'px-2 py-1 text-xs font-semibold rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200',
    buildPillStyleFilled(categoryColor)
  );
  categoryPill.dataset.categoryPill = 'true';
  categoryPill.dataset.categoryName = skill.category;
  pills.appendChild(categoryPill);
  const tagColors = skill.tag_colors ?? {};
  for (const tag of skill.tags ?? []) {
    const color = tagColors[tag] ?? getTagColorMap()[tag];
    const tagPill = pill(
      tag,
      'px-2 py-1 text-xs font-medium rounded-full border border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200',
      buildPillStyleOutline(color)
    );
    tagPill.dataset.tagPill = 'true';
    tagPill.dataset.tagName = tag;
    pills.appendChild(tagPill);
  }
  div.appendChild(pills);

  // Description (escaped text, never a prompt-body preview)
  const description = document.createElement('p');
  description.className =
    'skill-description text-prompt-body text-gray-600 dark:text-gray-300 mb-2 line-clamp-3';
  description.textContent = skill.description || t('skills.detail.noDescription');
  div.appendChild(description);

  // Meta: file count, size, warnings
  const meta = document.createElement('p');
  meta.className = 'skill-meta text-xs text-gray-500 dark:text-gray-400 mb-3';
  meta.textContent = `${t('skills.detail.files', { count: skill.file_count })} · ${formatBytes(skill.total_bytes)}`;
  if (skill.format_warnings.length > 0) {
    const warning = document.createElement('span');
    warning.className = 'skill-warning-flag ml-2 text-amber-700 dark:text-amber-400';
    warning.textContent = `⚠ ${t('skills.detail.warnings')}`;
    warning.title = describeWarnings(skill.format_warnings).join('\n');
    meta.appendChild(warning);
  }
  div.appendChild(meta);

  // Buttons
  const buttons = document.createElement('div');
  buttons.className = 'flex flex-wrap gap-2';
  const open = (): void => {
    handlers.onSelect(numericId);
    handlers.onOpen(numericId);
  };
  buttons.appendChild(
    actionButton(
      t('actions.view'),
      'skill-open-btn bg-blue-100 text-blue-700 hover:bg-blue-200',
      open
    )
  );
  if (isOwner) {
    buttons.appendChild(
      actionButton(
        t('actions.delete'),
        'delete-btn bg-red-100 text-red-700 hover:bg-red-200',
        () => {
          handlers.onSelect(numericId);
          handlers.onDelete(id);
        }
      )
    );
  }
  div.appendChild(buttons);

  // Card click opens the skill; interactive children keep their own behaviour.
  div.addEventListener('click', (event) => {
    const target = event.target as Element | null;
    if (target && (target.closest('button') || target.closest('input') || target.closest('a'))) {
      return;
    }
    open();
  });

  return div;
}
