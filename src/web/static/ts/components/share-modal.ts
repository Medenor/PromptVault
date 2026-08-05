/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Share modal (007-prompt-sharing).
 *
 * Composes `components/modal.ts` for the dialog chrome, a small
 * username/email typeahead (debounced via `utils/debounce.ts`, backed by
 * `searchUsers`) for picking the grantee, and a read/edit permission
 * `<select>`. Submitting calls `grantShare`; on success the modal closes and
 * a success toast is shown, on failure a generic error is shown inline (no
 * user enumeration, contracts §1) plus a toast.
 *
 * US3 additions: a current-grants list (fetched via `listShares` on open,
 * owner/admin only — a 403 for a non-owner caller just leaves the list
 * empty) with a per-row revoke button, and — for `legacy_public` prompts —
 * a "Make private" action that un-grandfathers the prompt (one-way).
 */

import type { PromptResponse, ShareResponse, UserSuggestion } from '@/types';
import { createModal } from './modal';
import { createSelectInput } from './form';
import { createButton } from './button';
import { grantShare, listShares, revokeShare, searchUsers, unGrandfatherPrompt } from '@/utils/api';
import { debounce } from '@/utils/debounce';
import { t } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';

const SEARCH_DEBOUNCE_MS = 250;
const MIN_QUERY_LENGTH = 2;

export interface ShareModalHandle {
  element: HTMLDivElement;
  open: () => void;
  close: () => void;
}

/**
 * Build and return a share modal for the given prompt. The modal is not
 * appended to the DOM automatically — callers should append `element` to
 * the document (typically once, lazily, on first open) and call `open()`.
 */
export function createShareModal(
  prompt: Pick<PromptResponse, 'id' | 'title' | 'legacy_public'>
): ShareModalHandle {
  let selectedUser: UserSuggestion | null = null;

  const body = document.createElement('div');
  body.className = 'flex flex-col gap-4';

  // --- Current grants list (US3) ----------------------------------------
  const grantsSection = document.createElement('div');
  const grantsHeading = document.createElement('h3');
  grantsHeading.className = 'font-medium text-gray-900 text-sm mb-1';
  grantsHeading.textContent = t('sharing.title');
  const grantsList = document.createElement('ul');
  grantsList.className = 'flex flex-col gap-1 mb-2';
  grantsSection.append(grantsHeading, grantsList);

  function renderGrant(share: ShareResponse): void {
    const row = document.createElement('li');
    row.className = 'flex items-center justify-between text-sm px-2 py-1 rounded bg-gray-50';

    const label = document.createElement('span');
    label.textContent = `${share.grantee.username} — ${t(`sharing.permission.${share.permission}`)}`;

    const revokeButton = createButton(t('sharing.revoke'), {
      variant: 'secondary',
      onClick: () => {
        void handleRevoke(share.grantee.id, row);
      },
    });
    revokeButton.classList.add('text-xs', 'px-2', 'py-1');

    row.append(label, revokeButton);
    grantsList.appendChild(row);
  }

  function renderGrants(shares: ShareResponse[]): void {
    // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
    grantsList.innerHTML = '';
    if (shares.length === 0) {
      const empty = document.createElement('li');
      empty.className = 'text-sm text-gray-500';
      empty.textContent = t('sharing.no_shares');
      grantsList.appendChild(empty);
      return;
    }
    shares.forEach(renderGrant);
  }

  async function loadGrants(): Promise<void> {
    try {
      const response = await listShares(prompt.id);
      renderGrants(response.shares);
    } catch {
      // Non-owner callers get 403/404 here — leave the list empty rather
      // than surfacing an error for what may be an expected permission gap.
      renderGrants([]);
    }
  }

  async function handleRevoke(granteeId: string, row: HTMLLIElement): Promise<void> {
    try {
      await revokeShare(prompt.id, granteeId);
      row.remove();
      showNotification(t('sharing.revoked'), 'success');
      if (grantsList.children.length === 0) {
        renderGrants([]);
      }
    } catch {
      showNotification(t('sharing.grant_failed'), 'error');
    }
  }

  // --- Make private (un-grandfather, US3) --------------------------------
  let makePrivateButton: HTMLButtonElement | null = null;
  if (prompt.legacy_public) {
    makePrivateButton = createButton(t('sharing.make_private'), {
      variant: 'secondary',
      onClick: () => {
        if (!window.confirm(t('sharing.make_private_confirm'))) {
          return;
        }
        void handleMakePrivate();
      },
    });
    makePrivateButton.classList.add('self-start');
    body.appendChild(makePrivateButton);
  }

  async function handleMakePrivate(): Promise<void> {
    if (makePrivateButton) {
      makePrivateButton.disabled = true;
    }
    try {
      await unGrandfatherPrompt(prompt.id);
      prompt.legacy_public = false;
      makePrivateButton?.remove();
      makePrivateButton = null;
      showNotification(t('sharing.make_private'), 'success');
    } catch {
      showNotification(t('sharing.grant_failed'), 'error');
      if (makePrivateButton) {
        makePrivateButton.disabled = false;
      }
    }
  }

  // --- User picker -----------------------------------------------------
  const pickerWrapper = document.createElement('div');
  pickerWrapper.className = 'relative';

  const pickerLabel = document.createElement('label');
  pickerLabel.className = 'block font-medium text-gray-900 text-sm mb-1';
  pickerLabel.textContent = t('sharing.picker_placeholder');
  const pickerInputId = 'share-modal-user-input';
  pickerLabel.htmlFor = pickerInputId;

  const pickerInput = document.createElement('input');
  pickerInput.type = 'text';
  pickerInput.id = pickerInputId;
  pickerInput.placeholder = t('sharing.picker_placeholder');
  pickerInput.autocomplete = 'off';
  pickerInput.className =
    'w-full px-3 py-2 rounded-md bg-gray-100 border-2 border-gray-100 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200';
  pickerInput.setAttribute('role', 'combobox');
  pickerInput.setAttribute('aria-expanded', 'false');
  pickerInput.setAttribute('aria-autocomplete', 'list');

  const resultsList = document.createElement('ul');
  const resultsListId = 'share-modal-user-results';
  resultsList.id = resultsListId;
  resultsList.className =
    'absolute z-10 mt-1 w-full max-h-48 overflow-y-auto rounded-md border border-gray-200 bg-white shadow-lg hidden';
  resultsList.setAttribute('role', 'listbox');
  pickerInput.setAttribute('aria-controls', resultsListId);

  const selectedHint = document.createElement('p');
  selectedHint.className = 'text-sm text-gray-500 mt-1 hidden';

  pickerWrapper.append(pickerLabel, pickerInput, resultsList, selectedHint);

  function clearSelection(): void {
    selectedUser = null;
    selectedHint.textContent = '';
    selectedHint.classList.add('hidden');
  }

  function selectUser(user: UserSuggestion): void {
    selectedUser = user;
    pickerInput.value = user.username;
    selectedHint.textContent = user.username;
    selectedHint.classList.remove('hidden');
    hideResults();
  }

  function hideResults(): void {
    resultsList.classList.add('hidden');
    // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
    resultsList.innerHTML = '';
    pickerInput.setAttribute('aria-expanded', 'false');
  }

  function renderResults(users: UserSuggestion[]): void {
    // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
    resultsList.innerHTML = '';

    if (users.length === 0) {
      const empty = document.createElement('li');
      empty.className = 'px-3 py-2 text-sm text-gray-500';
      empty.textContent = t('sharing.picker_no_results');
      resultsList.appendChild(empty);
      resultsList.classList.remove('hidden');
      pickerInput.setAttribute('aria-expanded', 'true');
      return;
    }

    users.forEach((user) => {
      const item = document.createElement('li');
      item.className = 'px-3 py-2 text-sm cursor-pointer hover:bg-gray-50';
      item.setAttribute('role', 'option');
      item.textContent = user.username;

      const choose = (event: Event) => {
        event.preventDefault();
        selectUser(user);
      };
      if ('PointerEvent' in window) {
        item.addEventListener('pointerdown', choose);
      } else {
        item.addEventListener('mousedown', choose);
      }

      resultsList.appendChild(item);
    });

    resultsList.classList.remove('hidden');
    pickerInput.setAttribute('aria-expanded', 'true');
  }

  const runSearch = debounce((query: string) => {
    if (query.length < MIN_QUERY_LENGTH) {
      hideResults();
      return;
    }
    searchUsers(query)
      .then((response) => {
        // Stale-response guard: only render if the input still matches.
        if (pickerInput.value.trim() === query) {
          renderResults(response.users);
        }
      })
      .catch(() => {
        hideResults();
      });
  }, SEARCH_DEBOUNCE_MS);

  pickerInput.addEventListener('input', () => {
    clearSelection();
    const query = pickerInput.value.trim();
    if (query.length < MIN_QUERY_LENGTH) {
      hideResults();
      return;
    }
    runSearch(query);
  });

  pickerInput.addEventListener('blur', () => {
    // Delay so a pending pointerdown/mousedown on a result can register first.
    setTimeout(hideResults, 150);
  });

  document.addEventListener('click', (event) => {
    if (
      !pickerWrapper.contains(event.target as Node) &&
      !resultsList.classList.contains('hidden')
    ) {
      hideResults();
    }
  });

  // --- Permission select -------------------------------------------------
  const permissionLabel = document.createElement('label');
  permissionLabel.className = 'block font-medium text-gray-900 text-sm mb-1';
  permissionLabel.textContent = t('sharing.grant');
  const permissionSelectId = 'share-modal-permission-select';
  permissionLabel.htmlFor = permissionSelectId;

  const permissionOptions = [
    { label: t('sharing.permission.read'), value: 'read' },
    { label: t('sharing.permission.edit'), value: 'edit' },
  ];
  const permissionSelect = createSelectInput(permissionOptions, {
    options: permissionOptions,
    id: permissionSelectId,
    name: 'permission',
    value: 'read',
  });

  const permissionWrapper = document.createElement('div');
  permissionWrapper.append(permissionLabel, permissionSelect);

  // --- Error area ---------------------------------------------------------
  const errorMessage = document.createElement('p');
  errorMessage.className = 'text-sm text-red-500 hidden';
  errorMessage.setAttribute('role', 'alert');

  // --- Footer buttons (built manually, not via ModalProps.actions: that
  // helper closes the modal unconditionally before invoking onClick, which
  // would prevent staying open on a failed async submit) -----------------
  const footer = document.createElement('div');
  footer.className = 'flex justify-end gap-2 mt-2';

  const cancelButton = createButton(t('actions.cancel'), {
    variant: 'secondary',
    onClick: () => {
      resetForm();
      modal.close();
    },
  });

  const submitButton = createButton(t('sharing.grant'), {
    variant: 'primary',
    onClick: () => {
      void handleSubmit();
    },
  });

  footer.append(cancelButton, submitButton);

  body.append(pickerWrapper, permissionWrapper, errorMessage, footer, grantsSection);

  function showError(message: string): void {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
  }

  function clearError(): void {
    errorMessage.textContent = '';
    errorMessage.classList.add('hidden');
  }

  let submitting = false;

  async function handleSubmit(): Promise<void> {
    if (submitting) {
      return;
    }
    clearError();

    const identifier = selectedUser?.username ?? pickerInput.value.trim();
    if (!identifier) {
      showError(t('sharing.grant_failed'));
      return;
    }
    const permission = (permissionSelect.value === 'edit' ? 'edit' : 'read') as 'read' | 'edit';

    submitting = true;
    submitButton.disabled = true;
    try {
      await grantShare(prompt.id, identifier, permission);
      showNotification(t('sharing.grant'), 'success');
      resetForm();
      void loadGrants();
      modal.close();
    } catch {
      // Generic error only — never distinguish unknown-user / inactive /
      // self-share / owner-as-grantee (contracts §1, SC-006).
      const message = t('sharing.grant_failed');
      showError(message);
      showNotification(message, 'error');
    } finally {
      submitting = false;
      submitButton.disabled = false;
    }
  }

  function resetForm(): void {
    pickerInput.value = '';
    clearSelection();
    hideResults();
    permissionSelect.value = 'read';
    clearError();
  }

  const modal = createModal({
    title: t('sharing.title'),
    content: body,
    size: 'md',
    ariaLabel: t('sharing.title'),
    onClose: () => {
      resetForm();
    },
  });

  return {
    ...modal,
    open: () => {
      void loadGrants();
      modal.open();
    },
  };
}
