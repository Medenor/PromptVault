/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { reportError } from '@/telemetry';
import { t, updateStaticTranslations } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';
import { APIRequestError } from '@/utils/api';
import { createUser } from './api';
import {
  addFieldError,
  clearLiveFieldError,
  getLiveValidationState,
  renderErrorSummary,
  resetFormAccessibilityState,
  setLiveFieldError,
  showFieldError,
} from './a11y';
import {
  hideModal,
  mapCreateUserField,
  normalizeErrorDetail,
  resetPasswordRequirements,
  setupPasswordToggle,
  showModal,
  updatePasswordRequirements,
} from './modals';
import type { FormValidationError } from './types';

export interface CreateUserFormCallbacks {
  onUserCreated: () => Promise<void>;
}

let createUserModalTrigger: HTMLElement | null = null;
let refreshCallbacks: CreateUserFormCallbacks | null = null;

export function setCreateUserFormCallbacks(callbacks: CreateUserFormCallbacks): void {
  refreshCallbacks = callbacks;
}

export function setupCreateUserForm(): void {
  const addUserBtn = document.getElementById('add-user-btn');
  if (addUserBtn) {
    addUserBtn.addEventListener('click', openCreateUserModal);
  }

  const cancelBtn = document.getElementById('create-user-cancel-btn');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', closeCreateUserModal);
  }

  const submitBtn = document.getElementById('create-user-submit-btn');
  if (submitBtn) {
    submitBtn.addEventListener('click', submitCreateUserForm);
  }

  const passwordInput = document.getElementById('create-password') as HTMLInputElement | null;
  if (passwordInput) {
    passwordInput.addEventListener('input', updatePasswordRequirements);
  }

  setupPasswordToggle('toggle-password-create', 'create-password');
  setupPasswordToggle('toggle-confirm-password-create', 'create-confirm-password');

  // Live validation (T-ACC025) for create modal fields.
  const usernameInput = document.getElementById('create-username') as HTMLInputElement | null;
  const emailInput = document.getElementById('create-email') as HTMLInputElement | null;
  const createPasswordInput = document.getElementById('create-password') as HTMLInputElement | null;
  const confirmInput = document.getElementById(
    'create-confirm-password'
  ) as HTMLInputElement | null;

  const requiredMessage = t('validation.required') || 'This field is required.';

  const attachRequired = (
    input: HTMLInputElement | null,
    inputId: string,
    errorId: string,
    message: string
  ) => {
    if (!input) return;
    input.addEventListener('blur', () => {
      if (!input.value.trim()) {
        setLiveFieldError(inputId, errorId, message);
      } else {
        clearLiveFieldError(inputId, errorId);
      }
    });
    input.addEventListener('input', () => {
      if (!getLiveValidationState(inputId)) return;
      if (input.value.trim()) {
        clearLiveFieldError(inputId, errorId);
      }
    });
  };

  attachRequired(usernameInput, 'create-username', 'create-username-error', requiredMessage);
  attachRequired(emailInput, 'create-email', 'create-email-error', requiredMessage);
  attachRequired(createPasswordInput, 'create-password', 'create-password-error', requiredMessage);
  attachRequired(
    confirmInput,
    'create-confirm-password',
    'create-confirm-password-error',
    requiredMessage
  );

  emailInput?.addEventListener('blur', () => {
    if (!emailInput.value.trim()) return;
    if (!emailInput.checkValidity()) {
      setLiveFieldError(
        'create-email',
        'create-email-error',
        t('auth.register.emailInvalid') || 'Invalid email address'
      );
    }
  });

  const passwordConfirmCheck = () => {
    const password = createPasswordInput?.value ?? '';
    const confirm = confirmInput?.value ?? '';
    if (!confirm.trim()) return;
    if (password && confirm && password !== confirm) {
      setLiveFieldError(
        'create-confirm-password',
        'create-confirm-password-error',
        t('auth.register.passwordMismatch') || 'Passwords do not match'
      );
    } else if (password && confirm) {
      clearLiveFieldError('create-confirm-password', 'create-confirm-password-error');
    }
  };
  createPasswordInput?.addEventListener('input', passwordConfirmCheck);
  confirmInput?.addEventListener('input', passwordConfirmCheck);
}

export function openCreateUserModal(): void {
  // Store trigger element for focus return
  createUserModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  showModal('create-user-modal');
  clearCreateUserForm();
  updateStaticTranslations();
}

export function closeCreateUserModal(): void {
  hideModal('create-user-modal', createUserModalTrigger);
  clearCreateUserForm();
}

function clearCreateUserForm(): void {
  const form = document.getElementById('create-user-form') as HTMLFormElement | null;
  if (form) {
    form.reset();
  }
  clearAllCreateUserErrors();
  resetPasswordRequirements();
}

function clearAllCreateUserErrors(): void {
  const errorIds = [
    'create-user-error-summary',
    'create-username-error',
    'create-email-error',
    'create-password-error',
    'create-confirm-password-error',
    'create-form-error',
  ];
  errorIds.forEach((id) => {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = '';
      // Inline field errors are toggled via `.hidden`; the summary uses inline style (CSS default is `display:none`).
      if (id === 'create-user-error-summary') {
        (element as HTMLElement).style.display = 'none';
      }
      element.classList.add('hidden');
    }
  });
}

export async function submitCreateUserForm(): Promise<void> {
  const form = document.getElementById('create-user-form') as HTMLFormElement | null;
  resetFormAccessibilityState(
    form,
    ['create-username', 'create-email', 'create-password', 'create-confirm-password'],
    'create-user-error-summary'
  );
  clearAllCreateUserErrors();
  const validationErrors: FormValidationError[] = [];

  const username =
    (document.getElementById('create-username') as HTMLInputElement | null)?.value.trim() ?? '';
  const email =
    (document.getElementById('create-email') as HTMLInputElement | null)?.value.trim() ?? '';
  const password =
    (document.getElementById('create-password') as HTMLInputElement | null)?.value ?? '';
  const confirmPassword =
    (document.getElementById('create-confirm-password') as HTMLInputElement | null)?.value ?? '';
  const role = (document.getElementById('create-role') as HTMLSelectElement | null)?.value ?? '';
  const emailVerified =
    (document.getElementById('create-email-verified') as HTMLInputElement | null)?.checked ?? false;

  let hasErrors = false;

  if (!username) {
    addFieldError(
      validationErrors,
      'create-username',
      'create-username-error',
      t('validation.required') || 'Username is required'
    );
    hasErrors = true;
  }

  if (!email) {
    addFieldError(
      validationErrors,
      'create-email',
      'create-email-error',
      t('validation.required') || 'Email is required'
    );
    hasErrors = true;
  }

  if (!password) {
    addFieldError(
      validationErrors,
      'create-password',
      'create-password-error',
      t('validation.required') || 'Password is required'
    );
    hasErrors = true;
  }

  if (!confirmPassword) {
    addFieldError(
      validationErrors,
      'create-confirm-password',
      'create-confirm-password-error',
      t('validation.required') || 'Confirm password is required'
    );
    hasErrors = true;
  }

  if (password && confirmPassword && password !== confirmPassword) {
    addFieldError(
      validationErrors,
      'create-confirm-password',
      'create-confirm-password-error',
      t('auth.register.passwordMismatch') || 'Passwords do not match'
    );
    hasErrors = true;
  }

  if (hasErrors) {
    renderErrorSummary('create-user-error-summary', validationErrors);
    return;
  }

  const submitBtn = document.getElementById('create-user-submit-btn') as HTMLButtonElement | null;
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = t('messages.loading') || 'Creating...';
  }

  try {
    await createUser({
      username,
      email,
      password,
      confirm_password: confirmPassword,
      role,
      email_verified: emailVerified,
    });

    showNotification(t('admin.users.userCreated') || 'User created successfully', 'success');
    closeCreateUserModal();
    await refreshCallbacks?.onUserCreated();
  } catch (error) {
    if (error instanceof APIRequestError) {
      if (error.status === 422 && Array.isArray(error.error.detail)) {
        const apiErrors: FormValidationError[] = [];
        error.error.detail.forEach((err) => {
          if (err.loc && err.loc.length > 1) {
            const errorMsg = err.msg || 'Validation error';
            const field = String(err.loc[1]);
            const mapping = mapCreateUserField(field);
            if (mapping) {
              addFieldError(apiErrors, mapping.inputId, mapping.errorId, errorMsg);
            } else {
              showFieldError('create-form-error', errorMsg);
            }
          }
        });
        renderErrorSummary('create-user-error-summary', apiErrors);
      } else if (error.status === 409) {
        const detailMessage = normalizeErrorDetail(error.error.detail);
        showFieldError(
          'create-form-error',
          detailMessage || t('admin.users.userExists') || 'User already exists'
        );
      } else {
        const detailMessage = normalizeErrorDetail(error.error.detail);
        showFieldError(
          'create-form-error',
          detailMessage || t('messages.error') || 'Failed to create user'
        );
      }
    } else {
      reportError('admin-users', 'createUser', error);
      showFieldError('create-form-error', t('messages.error') || 'Failed to create user');
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = t('actions.create') || 'Create User';
    }
  }
}
