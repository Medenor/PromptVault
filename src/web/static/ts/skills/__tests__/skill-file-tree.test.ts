/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({ default: { t: vi.fn((key: string) => key), language: 'en' } }));

import { buildTree, createFileTree } from '../skill-file-tree';
import type { SkillFileEntry } from '../skill-api';

function entry(path: string): SkillFileEntry {
  return { path, size: 1, is_text: true, sha256: 'x'.repeat(64) };
}

const FILES = [
  entry('SKILL.md'),
  entry('scripts/run.py'),
  entry('scripts/helpers/util.py'),
  entry('references/guide.md'),
  entry('Zed.txt'),
  entry('a.txt'),
];

describe('buildTree', () => {
  it('puts folders first, then files, each ordered by name', () => {
    const tree = buildTree(FILES);
    expect(tree.map((n) => `${n.isFolder ? 'd' : 'f'}:${n.name}`)).toEqual([
      'd:references',
      'd:scripts',
      'f:a.txt',
      'f:SKILL.md',
      'f:Zed.txt',
    ]);
    const scripts = tree.find((n) => n.name === 'scripts');
    expect(scripts?.children.map((n) => n.name)).toEqual(['helpers', 'run.py']);
    expect(scripts?.children[0]?.children[0]?.path).toBe('scripts/helpers/util.py');
  });

  it('keeps the file entry on leaves and nothing on folders', () => {
    const tree = buildTree([entry('a/b.txt')]);
    expect(tree[0]?.file).toBeNull();
    expect(tree[0]?.children[0]?.file?.path).toBe('a/b.txt');
  });

  it('handles an empty list', () => {
    expect(buildTree([])).toEqual([]);
  });
});

describe('createFileTree', () => {
  let onSelect: ReturnType<typeof vi.fn<(path: string) => void>>;
  let tree: ReturnType<typeof createFileTree>;

  beforeEach(() => {
    document.body.innerHTML = '';
    onSelect = vi.fn<(path: string) => void>();
    tree = createFileTree(FILES, { onSelect });
    document.body.appendChild(tree.element);
  });

  const item = (path: string): HTMLElement =>
    tree.element.querySelector<HTMLElement>(`[data-path="${path}"]`) as HTMLElement;
  const key = (target: HTMLElement, name: string): void => {
    target.dispatchEvent(
      new KeyboardEvent('keydown', { key: name, bubbles: true, cancelable: true })
    );
  };

  it('uses the ARIA tree pattern', () => {
    expect(tree.element.getAttribute('role')).toBe('tree');
    expect(tree.element.getAttribute('aria-label')).toBe('skills.tree.label');
    expect(item('scripts').getAttribute('role')).toBe('treeitem');
    expect(item('scripts').getAttribute('aria-expanded')).toBe('false');
    expect(item('scripts').querySelector('[role="group"]')).not.toBeNull();
    expect(item('SKILL.md').hasAttribute('aria-expanded')).toBe(false);
    expect(item('SKILL.md').getAttribute('aria-level')).toBe('1');
    expect(item('scripts/run.py').getAttribute('aria-level')).toBe('2');
  });

  it('has exactly one tab stop', () => {
    const stops = tree.element.querySelectorAll('[tabindex="0"]');
    expect(stops.length).toBe(1);
  });

  it('renders names as text, never as markup', () => {
    const hostile = createFileTree([entry('<img src=x onerror=alert(1)>.md')], { onSelect });
    expect(hostile.element.querySelector('img')).toBeNull();
    expect(hostile.element.textContent).toContain('<img src=x onerror=alert(1)>.md');
  });

  it('selects a file on click and reports its path', () => {
    (item('SKILL.md').querySelector('.tree-row') as HTMLElement).click();
    expect(onSelect).toHaveBeenCalledWith('SKILL.md');
    expect(item('SKILL.md').getAttribute('aria-selected')).toBe('true');
  });

  it('toggles a folder on click without selecting', () => {
    (item('scripts').querySelector('.tree-row') as HTMLElement).click();
    expect(item('scripts').getAttribute('aria-expanded')).toBe('true');
    expect(onSelect).not.toHaveBeenCalled();
    (item('scripts').querySelector('.tree-row') as HTMLElement).click();
    expect(item('scripts').getAttribute('aria-expanded')).toBe('false');
  });

  it('moves with the arrow keys over visible items only', () => {
    const first = item('references');
    first.focus();
    key(first, 'ArrowDown');
    expect(document.activeElement).toBe(item('scripts'));
    key(item('scripts'), 'ArrowDown');
    expect(document.activeElement).toBe(item('a.txt')); // collapsed folders hide their children
    key(item('a.txt'), 'ArrowUp');
    expect(document.activeElement).toBe(item('scripts'));
  });

  it('expands with ArrowRight, enters the folder, and collapses with ArrowLeft', () => {
    const folder = item('scripts');
    folder.focus();
    key(folder, 'ArrowRight');
    expect(folder.getAttribute('aria-expanded')).toBe('true');
    key(folder, 'ArrowRight');
    expect(document.activeElement).toBe(item('scripts/helpers'));
    key(item('scripts/helpers'), 'ArrowLeft');
    expect(document.activeElement).toBe(folder); // leaf/closed child goes to parent
    key(folder, 'ArrowLeft');
    expect(folder.getAttribute('aria-expanded')).toBe('false');
  });

  it('jumps with Home and End', () => {
    const start = item('a.txt');
    start.focus();
    key(start, 'Home');
    expect(document.activeElement).toBe(item('references'));
    key(item('references'), 'End');
    expect(document.activeElement).toBe(item('Zed.txt'));
  });

  it('activates with Enter and Space', () => {
    const file = item('SKILL.md');
    file.focus();
    key(file, 'Enter');
    key(file, ' ');
    expect(onSelect).toHaveBeenCalledTimes(2);
    const folder = item('references');
    key(folder, 'Enter');
    expect(folder.getAttribute('aria-expanded')).toBe('true');
  });

  it('ignores other keys', () => {
    const file = item('SKILL.md');
    const event = new KeyboardEvent('keydown', { key: 'x', bubbles: true, cancelable: true });
    file.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(false);
  });

  it('select() expands the folders above a file and marks it', () => {
    tree.select('scripts/helpers/util.py');
    expect(item('scripts').getAttribute('aria-expanded')).toBe('true');
    expect(item('scripts/helpers').getAttribute('aria-expanded')).toBe('true');
    expect(item('scripts/helpers/util.py').getAttribute('aria-selected')).toBe('true');
    expect(tree.visiblePaths()).toContain('scripts/helpers/util.py');
  });

  it('select() ignores unknown paths and folders', () => {
    tree.select('nope');
    tree.select('scripts');
    expect(tree.element.querySelectorAll('[aria-selected="true"]').length).toBe(0);
  });

  it('shows only the top level until folders open', () => {
    expect(tree.visiblePaths()).toEqual(['a.txt', 'SKILL.md', 'Zed.txt']);
  });
});
