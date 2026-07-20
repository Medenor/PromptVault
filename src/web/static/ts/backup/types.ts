/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

export interface CloudProvider {
  id: string;
  name: string;
  provider_type: string;
  endpoint_url: string | null;
  bucket_name: string;
  prefix: string;
  region: string | null;
  enabled: boolean;
}

export interface EncryptionConfig {
  is_enabled: boolean;
  algorithm: string;
  kdf: string;
  key_version: number;
  rotated_at: string | null;
}

export interface BackupSchedule {
  id: string;
  enabled: boolean;
  frequency: string;
  hour: number;
  minute: number;
  day_of_week: number | null;
  day_of_month: number | null;
  retention_days: number;
  cloud_provider_id: string | null;
  last_run_at: string | null;
  last_run_status: string | null;
}

export interface BackupItem {
  backup_id: string;
  timestamp: string;
  size_bytes: number;
  compressed: boolean;
  prompt_count: number;
  created_by?: string | null;
  storage_path?: string | null;
  cloud_provider_id?: string | null;
  cloud_path?: string | null;
  is_encrypted?: boolean;
}

export interface BackupStats {
  total_backups?: number;
  total_size?: number;
  compressed_count?: number;
  newest_backup?: string | null;
  oldest_backup?: string | null;
}

export interface BackupResponse {
  success: boolean;
  backup_id?: string;
}

export interface RestoreResponse {
  success: boolean;
}

export interface DeleteResponse {
  success: boolean;
}

export interface CleanupResponse {
  success: boolean;
  dry_run?: boolean;
  removed_count?: number;
}

export interface CompressResponse {
  success: boolean;
  compressed_count?: number;
}

export interface FormValidationError {
  inputId: string;
  message: string;
}

export const BACKUP_COMPONENT = 'backupManagement';
