/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { apiGet, apiPost, apiPut, apiDelete } from '@/utils/api';
import type { AdminUser, UsersResponse } from './types';

export const API_BASE = '/api/admin';

export interface UserListFilters {
  page: number;
  search: string;
  role: string;
  status: string;
}

export function fetchUsers(filters: UserListFilters): Promise<UsersResponse> {
  const params = new URLSearchParams({
    page: String(filters.page),
    limit: '20',
    search: filters.search,
  });

  if (filters.role !== 'all') {
    params.append('role', filters.role);
  }

  if (filters.status !== 'all') {
    if (filters.status === 'active') {
      params.append('is_active', 'true');
    } else if (filters.status === 'inactive') {
      params.append('is_active', 'false');
    } else if (filters.status === 'locked') {
      params.append('is_locked', 'true');
    }
  }

  return apiGet<UsersResponse>(`${API_BASE}/users?${params.toString()}`);
}

export function fetchUser(userId: string): Promise<AdminUser> {
  return apiGet<AdminUser>(`${API_BASE}/users/${userId}`);
}

export function updateUser(
  userId: string,
  payload: { role: string; is_active: boolean; email_verified: boolean }
): Promise<unknown> {
  return apiPut(`${API_BASE}/users/${userId}`, payload);
}

export function deleteUserRequest(userId: string): Promise<unknown> {
  return apiDelete(`${API_BASE}/users/${userId}?hard_delete=true`);
}

export function createUser(payload: {
  username: string;
  email: string;
  password: string;
  confirm_password: string;
  role: string;
  email_verified: boolean;
}): Promise<unknown> {
  return apiPost(`${API_BASE}/users`, payload);
}
