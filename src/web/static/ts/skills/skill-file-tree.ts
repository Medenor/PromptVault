/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Accessible file tree for a skill (011-skill-packages, FR-015).
 *
 * Built on the client from the flat `files[]` list. Folders come first, then
 * files, each group ordered with localeCompare. Uses the WAI-ARIA tree
 * pattern: role="tree"/"treeitem"/"group", aria-expanded on folders, a single
 * roving tab stop, and arrow-key navigation.
 */

import { t } from '@/utils/i18n';
import { syncRovingTabindex } from '@/utils/keyboard-nav';
import type { SkillFileEntry } from './skill-api';

export interface TreeNode {
  name: string;
  /** Full path from the skill root; folders have no trailing slash. */
  path: string;
  isFolder: boolean;
  children: TreeNode[];
  file: SkillFileEntry | null;
}

export interface FileTreeOptions {
  /** Called with the path of a file when it is chosen (click, Enter, Space). */
  onSelect: (path: string) => void;
}

export interface FileTreeHandle {
  element: HTMLElement;
  /** Mark a file as selected, expanding its folders. */
  select: (path: string) => void;
  /** Paths of the file items in the order they appear on screen. */
  visiblePaths: () => string[];
}

function compareNodes(a: TreeNode, b: TreeNode): number {
  if (a.isFolder !== b.isFolder) return a.isFolder ? -1 : 1;
  return a.name.localeCompare(b.name);
}

function sortTree(nodes: TreeNode[]): void {
  nodes.sort(compareNodes);
  for (const node of nodes) sortTree(node.children);
}

/** Build a nested, sorted tree from the flat file list. */
export function buildTree(files: readonly SkillFileEntry[]): TreeNode[] {
  const roots: TreeNode[] = [];
  const folders = new Map<string, TreeNode>();

  for (const file of files) {
    const parts = file.path.split('/').filter((part) => part !== '');
    let siblings = roots;
    let prefix = '';
    parts.forEach((part, index) => {
      prefix = prefix ? `${prefix}/${part}` : part;
      const isLast = index === parts.length - 1;
      if (isLast) {
        siblings.push({ name: part, path: prefix, isFolder: false, children: [], file });
        return;
      }
      let folder = folders.get(prefix);
      if (!folder) {
        folder = { name: part, path: prefix, isFolder: true, children: [], file: null };
        folders.set(prefix, folder);
        siblings.push(folder);
      }
      siblings = folder.children;
    });
  }

  sortTree(roots);
  return roots;
}

function isVisible(item: HTMLElement): boolean {
  for (let el = item.parentElement; el; el = el.parentElement) {
    if (el.getAttribute('role') === 'tree') return true;
    if (el.getAttribute('role') === 'group' && el.hidden) return false;
  }
  return true;
}

/** Create the tree element for a list of files. */
export function createFileTree(
  files: readonly SkillFileEntry[],
  options: FileTreeOptions
): FileTreeHandle {
  const root = document.createElement('ul');
  root.setAttribute('role', 'tree');
  root.setAttribute('aria-label', t('skills.tree.label'));
  root.className = 'skill-file-tree text-sm text-gray-800 dark:text-gray-100 space-y-0.5';

  let selected: HTMLElement | null = null;

  const allItems = (): HTMLElement[] =>
    Array.from(root.querySelectorAll<HTMLElement>('[role="treeitem"]'));
  const visibleItems = (): HTMLElement[] => allItems().filter(isVisible);

  const focusItem = (item: HTMLElement): void => {
    syncRovingTabindex(root, item);
    item.focus();
  };

  const setExpanded = (item: HTMLElement, expanded: boolean): void => {
    item.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    const group = item.querySelector<HTMLElement>(':scope > [role="group"]');
    if (group) group.hidden = !expanded;
    const icon = item.querySelector<HTMLElement>(':scope > .tree-row .tree-icon');
    if (icon) icon.textContent = expanded ? '📂' : '📁';
  };

  const markSelected = (item: HTMLElement): void => {
    if (selected) selected.setAttribute('aria-selected', 'false');
    selected = item;
    item.setAttribute('aria-selected', 'true');
  };

  const activate = (item: HTMLElement): void => {
    if (item.dataset.folder === 'true') {
      setExpanded(item, item.getAttribute('aria-expanded') !== 'true');
      return;
    }
    markSelected(item);
    const path = item.dataset.path;
    if (path) options.onSelect(path);
  };

  const renderNodes = (nodes: TreeNode[], container: HTMLElement, level: number): void => {
    for (const node of nodes) {
      const item = document.createElement('li');
      item.setAttribute('role', 'treeitem');
      item.setAttribute('aria-level', String(level));
      item.setAttribute('aria-selected', 'false');
      item.dataset.path = node.path;
      item.dataset.folder = node.isFolder ? 'true' : 'false';
      item.tabIndex = -1;

      const row = document.createElement('div');
      row.className =
        'tree-row flex items-center gap-1.5 rounded px-1.5 py-1 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700';
      row.style.paddingLeft = `${(level - 1) * 12 + 6}px`;
      const icon = document.createElement('span');
      icon.className = 'tree-icon';
      icon.setAttribute('aria-hidden', 'true');
      icon.textContent = node.isFolder ? '📁' : '📄';
      const label = document.createElement('span');
      label.className = 'tree-label break-all';
      label.textContent = node.name;
      row.append(icon, label);
      item.appendChild(row);

      if (node.isFolder) {
        const group = document.createElement('ul');
        group.setAttribute('role', 'group');
        group.className = 'space-y-0.5';
        item.appendChild(group);
        renderNodes(node.children, group, level + 1);
        setExpanded(item, false);
      }

      row.addEventListener('click', (event) => {
        event.stopPropagation();
        focusItem(item);
        activate(item);
      });
      container.appendChild(item);
    }
  };

  renderNodes(buildTree(files), root, 1);

  const first = root.querySelector<HTMLElement>('[role="treeitem"]');
  if (first) first.tabIndex = 0;

  root.addEventListener('keydown', (event) => {
    const current = (event.target as Element | null)?.closest<HTMLElement>('[role="treeitem"]');
    if (!current || !root.contains(current)) return;
    const items = visibleItems();
    const index = items.indexOf(current);
    const isFolder = current.dataset.folder === 'true';
    const expanded = current.getAttribute('aria-expanded') === 'true';
    let handled = true;

    switch (event.key) {
      case 'ArrowDown': {
        const next = items[index + 1];
        if (next) focusItem(next);
        break;
      }
      case 'ArrowUp': {
        const previous = items[index - 1];
        if (previous) focusItem(previous);
        break;
      }
      case 'ArrowRight':
        if (isFolder && !expanded) {
          setExpanded(current, true);
        } else if (isFolder) {
          const child = current.querySelector<HTMLElement>(
            ':scope > [role="group"] > [role="treeitem"]'
          );
          if (child) focusItem(child);
        }
        break;
      case 'ArrowLeft':
        if (isFolder && expanded) {
          setExpanded(current, false);
        } else {
          const parent = current.parentElement?.closest<HTMLElement>('[role="treeitem"]');
          if (parent) focusItem(parent);
        }
        break;
      case 'Home': {
        const firstItem = items[0];
        if (firstItem) focusItem(firstItem);
        break;
      }
      case 'End': {
        const last = items[items.length - 1];
        if (last) focusItem(last);
        break;
      }
      case 'Enter':
      case ' ':
        activate(current);
        break;
      default:
        handled = false;
    }
    if (handled) event.preventDefault();
  });

  return {
    element: root,
    select: (path: string) => {
      const item = allItems().find(
        (el) => el.dataset.path === path && el.dataset.folder !== 'true'
      );
      if (!item) return;
      for (
        let parent = item.parentElement?.closest<HTMLElement>('[role="treeitem"]');
        parent;
        parent = parent.parentElement?.closest<HTMLElement>('[role="treeitem"]')
      ) {
        setExpanded(parent, true);
      }
      markSelected(item);
      syncRovingTabindex(root, item);
    },
    visiblePaths: () =>
      visibleItems()
        .filter((el) => el.dataset.folder !== 'true')
        .map((el) => el.dataset.path ?? ''),
  };
}
