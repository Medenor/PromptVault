/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({ default: { t: vi.fn((key: string) => key), language: 'en' } }));

import { closePromptEditorForListChange } from '../prompt-list';

function mount(editorHidden: boolean): void {
  document.body.innerHTML = `
    <div id="prompt-editor" class="${editorHidden ? 'hidden' : ''}"></div>
    <div id="prompts-list" class="hidden"></div>
    <div id="pull-refresh-toolbar" class="hidden"></div>
  `;
}

describe('closePromptEditorForListChange', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('hides an open editor and restores the list and toolbar', () => {
    mount(false);
    closePromptEditorForListChange();
    expect(document.getElementById('prompt-editor')?.classList.contains('hidden')).toBe(true);
    expect(document.getElementById('prompts-list')?.classList.contains('hidden')).toBe(false);
    expect(document.getElementById('pull-refresh-toolbar')?.classList.contains('hidden')).toBe(
      false
    );
  });

  it('leaves the page untouched when the editor is already closed', () => {
    mount(true);
    closePromptEditorForListChange();
    expect(document.getElementById('prompts-list')?.classList.contains('hidden')).toBe(true);
  });
});
