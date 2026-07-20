/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  email_verified?: boolean;
  last_login?: string | null;
  created_at?: string | null;
  locked_until?: string | null;
  session_count?: number;
  failed_login_attempts?: number;
}

export interface UsersResponse {
  users?: AdminUser[];
  pages?: number;
  total?: number;
}

export interface PasswordChecks {
  length: boolean;
  uppercase: boolean;
  lowercase: boolean;
  digit: boolean;
  special: boolean;
}

export interface FormValidationError {
  inputId: string;
  message: string;
}
