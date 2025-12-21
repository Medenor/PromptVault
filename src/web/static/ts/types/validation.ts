/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { ValidationState } from './api/enums';

export interface ValidationResult<T> {
  valid: boolean;
  error: string | null;
  sanitized: T;
}

export interface FileValidationResult {
  valid: boolean;
  error: string | null;
}

export interface PasswordStrengthResult {
  strength: number;
  checks: {
    length: boolean;
    uppercase: boolean;
    lowercase: boolean;
    digit: boolean;
    special: boolean;
  };
}

export interface FieldValidationState {
  state: ValidationState;
  message?: string;
}
