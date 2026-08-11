/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string) => key),
    language: 'en',
  },
}));

const grantShareMock = vi.fn();
const searchUsersMock = vi.fn();
const listSharesMock = vi.fn();
const revokeShareMock = vi.fn();
const unGrandfatherPromptMock = vi.fn();
vi.mock('@/utils/api', () => ({
  grantShare: (...args: unknown[]) => grantShareMock(...args),
  searchUsers: (...args: unknown[]) => searchUsersMock(...args),
  listShares: (...args: unknown[]) => listSharesMock(...args),
  revokeShare: (...args: unknown[]) => revokeShareMock(...args),
  unGrandfatherPrompt: (...args: unknown[]) => unGrandfatherPromptMock(...args),
}));

const showNotificationMock = vi.fn();
vi.mock('@/utils/notifications', () => ({
  showNotification: (...args: unknown[]) => showNotificationMock(...args),
}));

import { createShareModal } from '../share-modal';

const PROMPT = { id: 42, title: 'Test prompt' };

function getInput(root: HTMLElement): HTMLInputElement {
  return root.querySelector('#share-modal-user-input') as HTMLInputElement;
}

function getSelect(root: HTMLElement): HTMLSelectElement {
  return root.querySelector('#share-modal-permission-select') as HTMLSelectElement;
}

function getButtons(root: HTMLElement): { cancel: HTMLButtonElement; submit: HTMLButtonElement } {
  const buttons = Array.from(root.querySelectorAll('button')).filter(
    (b) => b.textContent === 'actions.cancel' || b.textContent === 'sharing.grant'
  );
  const cancel = buttons.find((b) => b.textContent === 'actions.cancel') as HTMLButtonElement;
  const submit = buttons.find((b) => b.textContent === 'sharing.grant') as HTMLButtonElement;
  return { cancel, submit };
}

async function flushMicrotasks(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

describe('createShareModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    document.body.innerHTML = '';
    listSharesMock.mockResolvedValue({ prompt_id: 42, shares: [] });
  });

  it('opens and renders the picker, permission select, and action buttons', async () => {
    const modal = createShareModal(PROMPT);
    document.body.appendChild(modal.element);

    expect(modal.element.classList.contains('hidden')).toBe(true);
    modal.open();
    await flushMicrotasks();
    expect(modal.element.classList.contains('hidden')).toBe(false);

    expect(getInput(modal.element)).toBeInstanceOf(HTMLInputElement);
    expect(getSelect(modal.element)).toBeInstanceOf(HTMLSelectElement);
    const { cancel, submit } = getButtons(modal.element);
    expect(cancel).toBeTruthy();
    expect(submit).toBeTruthy();
  });

  it('selecting a typeahead suggestion fills the picker and hides results', async () => {
    searchUsersMock.mockResolvedValue({ users: [{ id: 'u1', username: 'alice' }] });

    const modal = createShareModal(PROMPT);
    document.body.appendChild(modal.element);
    modal.open();

    const input = getInput(modal.element);
    input.value = 'al';
    input.dispatchEvent(new Event('input', { bubbles: true }));

    // Debounced search: wait past the debounce window.
    await new Promise((resolve) => setTimeout(resolve, 300));
    await flushMicrotasks();

    const option = modal.element.querySelector('[role="option"]') as HTMLLIElement;
    expect(option).toBeTruthy();
    expect(option.textContent).toBe('alice');

    option.dispatchEvent(new Event('mousedown', { bubbles: true }));

    expect(input.value).toBe('alice');
  });

  it('allows choosing the edit permission', () => {
    const modal = createShareModal(PROMPT);
    document.body.appendChild(modal.element);
    modal.open();

    const select = getSelect(modal.element);
    expect(select.value).toBe('read');
    select.value = 'edit';
    select.dispatchEvent(new Event('change', { bubbles: true }));
    expect(select.value).toBe('edit');
  });

  it('submits successfully: calls grantShare, shows a success toast, and closes', async () => {
    grantShareMock.mockResolvedValue({
      prompt_id: 42,
      grantee: { id: 'u1', username: 'alice' },
      permission: 'read',
      granted_by: 'bob',
      created_at: '2026-08-04T12:00:00Z',
      updated_at: '2026-08-04T12:00:00Z',
    });

    const modal = createShareModal(PROMPT);
    document.body.appendChild(modal.element);
    modal.open();

    const input = getInput(modal.element);
    input.value = 'alice';
    input.dispatchEvent(new Event('input', { bubbles: true }));

    const { submit } = getButtons(modal.element);
    submit.click();
    await flushMicrotasks();

    expect(grantShareMock).toHaveBeenCalledWith(42, 'alice', 'read');
    expect(showNotificationMock).toHaveBeenCalledWith('sharing.grant', 'success');
    expect(modal.element.classList.contains('hidden')).toBe(true);
  });

  it('shows a generic error and keeps the modal open on failure (no user enumeration)', async () => {
    grantShareMock.mockRejectedValue(new Error('Bad Request'));

    const modal = createShareModal(PROMPT);
    document.body.appendChild(modal.element);
    modal.open();

    const input = getInput(modal.element);
    input.value = 'nobody';
    input.dispatchEvent(new Event('input', { bubbles: true }));

    const { submit } = getButtons(modal.element);
    submit.click();
    await flushMicrotasks();

    expect(grantShareMock).toHaveBeenCalledWith(42, 'nobody', 'read');
    const errorEl = modal.element.querySelector('[role="alert"]');
    expect(errorEl?.textContent).toBe('sharing.grant_failed');
    expect(showNotificationMock).toHaveBeenCalledWith('sharing.grant_failed', 'error');
    // Stays open on failure.
    expect(modal.element.classList.contains('hidden')).toBe(false);
  });

  it('does not submit when no identifier is entered', async () => {
    const modal = createShareModal(PROMPT);
    document.body.appendChild(modal.element);
    modal.open();

    const { submit } = getButtons(modal.element);
    submit.click();
    await flushMicrotasks();

    expect(grantShareMock).not.toHaveBeenCalled();
    const errorEl = modal.element.querySelector('[role="alert"]');
    expect(errorEl?.textContent).toBe('sharing.grant_failed');
  });

  it('cancel button resets the form and closes without submitting', () => {
    const modal = createShareModal(PROMPT);
    document.body.appendChild(modal.element);
    modal.open();

    const input = getInput(modal.element);
    input.value = 'someone';
    input.dispatchEvent(new Event('input', { bubbles: true }));

    const { cancel } = getButtons(modal.element);
    cancel.click();

    expect(grantShareMock).not.toHaveBeenCalled();
    expect(modal.element.classList.contains('hidden')).toBe(true);
    expect(input.value).toBe('');
  });

  it('loads and renders the current grants list on open', async () => {
    listSharesMock.mockResolvedValue({
      prompt_id: 42,
      shares: [
        {
          prompt_id: 42,
          grantee: { id: 'u1', username: 'alice' },
          permission: 'edit',
          granted_by: 'bob',
          created_at: '2026-08-04T12:00:00Z',
          updated_at: '2026-08-04T12:00:00Z',
        },
      ],
    });

    const modal = createShareModal(PROMPT);
    document.body.appendChild(modal.element);
    modal.open();
    await flushMicrotasks();

    expect(listSharesMock).toHaveBeenCalledWith(42);
    expect(modal.element.textContent).toContain('alice');
    const revokeButton = Array.from(modal.element.querySelectorAll('button')).find(
      (b) => b.textContent === 'sharing.revoke'
    );
    expect(revokeButton).toBeTruthy();
  });

  it('shows the no-shares message when the grant list is empty', async () => {
    listSharesMock.mockResolvedValue({ prompt_id: 42, shares: [] });

    const modal = createShareModal(PROMPT);
    document.body.appendChild(modal.element);
    modal.open();
    await flushMicrotasks();

    expect(modal.element.textContent).toContain('sharing.no_shares');
  });

  it('leaves the grants list empty when listShares fails (e.g. non-owner viewer)', async () => {
    listSharesMock.mockRejectedValue(new Error('Forbidden'));

    const modal = createShareModal(PROMPT);
    document.body.appendChild(modal.element);
    modal.open();
    await flushMicrotasks();

    expect(modal.element.textContent).toContain('sharing.no_shares');
  });

  it('revoking a grant calls revokeShare and removes the row', async () => {
    listSharesMock.mockResolvedValue({
      prompt_id: 42,
      shares: [
        {
          prompt_id: 42,
          grantee: { id: 'u1', username: 'alice' },
          permission: 'read',
          granted_by: 'bob',
          created_at: '2026-08-04T12:00:00Z',
          updated_at: '2026-08-04T12:00:00Z',
        },
      ],
    });
    revokeShareMock.mockResolvedValue({ message: 'Share revoked' });

    const modal = createShareModal(PROMPT);
    document.body.appendChild(modal.element);
    modal.open();
    await flushMicrotasks();

    const revokeButton = Array.from(modal.element.querySelectorAll('button')).find(
      (b) => b.textContent === 'sharing.revoke'
    ) as HTMLButtonElement;
    revokeButton.click();
    await flushMicrotasks();

    expect(revokeShareMock).toHaveBeenCalledWith(42, 'u1');
    expect(showNotificationMock).toHaveBeenCalledWith('sharing.revoked', 'success');
    expect(modal.element.textContent).not.toContain('alice');
  });

  it('shows a make-private button for a legacy_public prompt and un-grandfathers on confirm', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    unGrandfatherPromptMock.mockResolvedValue({ id: 42, legacy_public: false });

    const legacyPrompt = { ...PROMPT, legacy_public: true };
    const modal = createShareModal(legacyPrompt);
    document.body.appendChild(modal.element);
    modal.open();
    await flushMicrotasks();

    const makePrivateButton = Array.from(modal.element.querySelectorAll('button')).find(
      (b) => b.textContent === 'sharing.make_private'
    ) as HTMLButtonElement;
    expect(makePrivateButton).toBeTruthy();

    makePrivateButton.click();
    await flushMicrotasks();

    expect(confirmSpy).toHaveBeenCalledWith('sharing.make_private_confirm');
    expect(unGrandfatherPromptMock).toHaveBeenCalledWith(42);
    expect(showNotificationMock).toHaveBeenCalledWith('sharing.make_private', 'success');
    expect(
      Array.from(modal.element.querySelectorAll('button')).some(
        (b) => b.textContent === 'sharing.make_private'
      )
    ).toBe(false);

    confirmSpy.mockRestore();
  });

  it('does not show a make-private button for a non-legacy_public prompt', async () => {
    const modal = createShareModal({ ...PROMPT, legacy_public: false });
    document.body.appendChild(modal.element);
    modal.open();
    await flushMicrotasks();

    const makePrivateButton = Array.from(modal.element.querySelectorAll('button')).find(
      (b) => b.textContent === 'sharing.make_private'
    );
    expect(makePrivateButton).toBeFalsy();
  });

  it('cancels the make-private action when the confirm dialog is dismissed', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

    const legacyPrompt = { ...PROMPT, legacy_public: true };
    const modal = createShareModal(legacyPrompt);
    document.body.appendChild(modal.element);
    modal.open();
    await flushMicrotasks();

    const makePrivateButton = Array.from(modal.element.querySelectorAll('button')).find(
      (b) => b.textContent === 'sharing.make_private'
    ) as HTMLButtonElement;
    makePrivateButton.click();
    await flushMicrotasks();

    expect(unGrandfatherPromptMock).not.toHaveBeenCalled();

    confirmSpy.mockRestore();
  });
});
