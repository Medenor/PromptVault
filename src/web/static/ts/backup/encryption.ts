/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { reportError } from '@/telemetry';
import { t } from '@/utils/i18n';
import { apiFetch, apiGet } from '@/utils/api';
import { BACKUP_COMPONENT, type EncryptionConfig } from './types';
import { setEncryptionEnabled } from './list';

export async function loadEncryptionConfig(): Promise<void> {
  let encryptionEnabled = false;
  try {
    const config = await apiGet<EncryptionConfig>('/api/backup-encryption');
    const enabledEl = document.getElementById('encryption-enabled') as HTMLInputElement | null;
    const infoEl = document.getElementById('encryption-info');
    const rotationEl = document.getElementById('encryption-key-rotation');
    const rotateBtnEl = document.getElementById('encryption-rotate-btn');

    if (enabledEl) enabledEl.checked = config.is_enabled;
    if (infoEl) {
      infoEl.textContent = `Algorithm: ${config.algorithm} | KDF: ${config.kdf} | Key version: ${config.key_version}${config.rotated_at ? ` | Rotated: ${new Date(config.rotated_at).toLocaleString()}` : ''}`;
    }
    rotationEl?.classList.toggle('hidden', !config.is_enabled);
    rotateBtnEl?.classList.toggle('hidden', !config.is_enabled);
    encryptionEnabled = config.is_enabled;
  } catch {
    // Encryption not configured
    encryptionEnabled = false;
  }
  setEncryptionEnabled(encryptionEnabled);

  const createPassphraseContainer = document.getElementById('backup-create-passphrase-container');
  if (createPassphraseContainer) {
    createPassphraseContainer.classList.toggle('hidden', !encryptionEnabled);
  }
}

export async function saveEncryptionConfig(): Promise<void> {
  const enabledEl = document.getElementById('encryption-enabled') as HTMLInputElement | null;
  const passphraseEl = document.getElementById('encryption-passphrase') as HTMLInputElement | null;
  const statusEl = document.getElementById('encryption-status');

  const isEnabled = enabledEl?.checked ?? false;
  const body: Record<string, unknown> = { is_enabled: isEnabled };

  if (isEnabled) {
    const passphrase = passphraseEl?.value ?? '';
    if (!passphrase) {
      if (statusEl) {
        statusEl.textContent = t('backup.encryptionPassphraseRequiredToEnable');
        statusEl.className = 'text-sm text-red-600 mt-2';
      }
      return;
    }
    body.passphrase = passphrase;
  }

  try {
    await apiFetch<EncryptionConfig>('/api/backup-encryption', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (statusEl) {
      statusEl.textContent = isEnabled
        ? t('backup.encryptionEnabledStatus')
        : t('backup.encryptionDisabledStatus');
      statusEl.className = 'text-sm text-green-600 mt-2';
    }
    if (passphraseEl) passphraseEl.value = '';
    void loadEncryptionConfig();
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'saveEncryptionConfig', error);
    if (statusEl) {
      statusEl.textContent = t('backup.encryptionSaveFailed');
      statusEl.className = 'text-sm text-red-600 mt-2';
    }
  }
}

export async function rotateEncryptionKey(): Promise<void> {
  const oldPassphraseEl = document.getElementById(
    'encryption-old-passphrase'
  ) as HTMLInputElement | null;
  const newPassphraseEl = document.getElementById(
    'encryption-new-passphrase'
  ) as HTMLInputElement | null;
  const statusEl = document.getElementById('encryption-status');

  const oldPassphrase = oldPassphraseEl?.value ?? '';
  const newPassphrase = newPassphraseEl?.value ?? '';

  if (!oldPassphrase || !newPassphrase) {
    if (statusEl) {
      statusEl.textContent = t('backup.encryptionRotationPassphrasesRequired');
      statusEl.className = 'text-sm text-red-600 mt-2';
    }
    return;
  }

  try {
    await apiFetch<EncryptionConfig>('/api/backup-encryption', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rotate_key: true,
        old_passphrase: oldPassphrase,
        new_passphrase: newPassphrase,
      }),
    });
    if (statusEl) {
      statusEl.textContent = t('backup.encryptionRotationSuccess');
      statusEl.className = 'text-sm text-green-600 mt-2';
    }
    if (oldPassphraseEl) oldPassphraseEl.value = '';
    if (newPassphraseEl) newPassphraseEl.value = '';
    void loadEncryptionConfig();
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'rotateEncryptionKey', error);
    if (statusEl) {
      statusEl.textContent = t('backup.encryptionRotationFailed');
      statusEl.className = 'text-sm text-red-600 mt-2';
    }
  }
}
