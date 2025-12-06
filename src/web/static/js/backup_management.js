/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */
 
 // Backup Management JavaScript
let currentBackups = [];
let selectedBackupId = null;
const BACKUP_COMPONENT = 'backupManagement';

function reportBackupIssue(action, error, metadata = {}, severity = 'error') {
    const logger = window.FrontendLogger;
    if (logger && typeof logger.reportError === 'function') {
        logger.reportError(BACKUP_COMPONENT, action, error, metadata, severity);
    }
    const prefix = `[PromptVault][backup] ${action}`;
    if (severity === 'warning') {
        console.warn(prefix, error, metadata);
    } else {
        console.error(prefix, error, metadata);
    }
}

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    initializeI18n();
    setupEventListeners();
    checkAdminAccess();
    loadBackups();
    loadBackupStats();
});

// Initialize internationalization
function initializeI18n() {
    i18next
        .use(i18nextHttpBackend)
        .use(i18nextBrowserLanguageDetector)
        .init({
            fallbackLng: 'en',
            debug: false,
            backend: {
                loadPath: '/static/locales/{{lng}}.json'
            }
        }, function(err, t) {
            updateContent();
        });
}

// Update content with translations
function updateContent() {
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (key) {
            // Handle special syntax like [placeholder]key or [value]key
            if (key.includes('[') && key.includes(']')) {
                const match = key.match(/\[(\w+)\](.+)/);
                if (match) {
                    const attribute = match[1]; // e.g., 'placeholder'
                    const translationKey = match[2]; // e.g., 'backup.backupNamePlaceholder'
                    const translation = i18next.t(translationKey);
                    if (translation) {
                        element.setAttribute(attribute, translation);
                    }
                }
            } else {
                // Regular text content translation
                element.textContent = i18next.t(key);
            }
        }
    });

    // Update language selector
    const languageSelector = document.getElementById('language-selector');
    if (languageSelector) {
        languageSelector.value = i18next.language;
    }
}

// Load backups from server
async function loadBackups() {
    try {
        const response = await fetch('/api/backups');
        const data = await response.json();

        currentBackups = data.backups || [];
        renderBackupList(currentBackups);
    } catch (error) {
        reportBackupIssue('loadBackups', error);
        showStatus('backup-status', 'Error loading backups', 'error');
    }
}

// Load backup statistics
async function loadBackupStats() {
    try {
        const response = await fetch('/api/backups/stats');
        const stats = await response.json();

        updateStatsDisplay(stats);
    } catch (error) {
        reportBackupIssue('loadBackupStats', error);
    }
}

// Update statistics display
function updateStatsDisplay(stats) {
    document.getElementById('total-backups').textContent = stats.total_backups || 0;
    document.getElementById('total-size').textContent = formatBytes(stats.total_size || 0);
    document.getElementById('compressed-count').textContent = stats.compressed_count || 0;

    if (stats.newest_backup) {
        document.getElementById('newest-backup').textContent = new Date(stats.newest_backup).toLocaleString();
    } else {
        document.getElementById('newest-backup').textContent = 'None';
    }

    if (stats.oldest_backup) {
        document.getElementById('oldest-backup').textContent = new Date(stats.oldest_backup).toLocaleString();
    } else {
        document.getElementById('oldest-backup').textContent = 'None';
    }
}

// Render backup list
function renderBackupList(backups) {
    const container = document.getElementById('backup-list');

    if (backups.length === 0) {
        container.innerHTML = '<div class="no-backups">No backups found</div>';
        return;
    }

    const backupItems = backups.map(backup => createBackupItem(backup)).join('');
    container.innerHTML = backupItems;
}

// Create backup item HTML
function createBackupItem(backup) {
    const timestamp = new Date(backup.timestamp).toLocaleString();
    const size = formatBytes(backup.size_bytes);
    const isCompressed = backup.compressed ? ' (compressed)' : '';
    const compressionIcon = backup.compressed ? '🗜️' : '📄';

    return `
        <div class="backup-item" data-id="${backup.backup_id}">
            <div class="backup-info">
                <div class="backup-header">
                    <h4>${backup.backup_id}${isCompressed}</h4>
                    <div class="backup-actions">
                        <button class="btn btn-small btn-primary" onclick="showRestoreModal('${backup.backup_id}')">Restore</button>
                        <button class="btn btn-small btn-danger" onclick="showDeleteModal('${backup.backup_id}')">Delete</button>
                    </div>
                </div>
                <div class="backup-details">
                    <div class="backup-meta">
                        <span class="backup-timestamp">${timestamp}</span>
                        <span class="backup-size">${compressionIcon} ${size}</span>
                        <span class="backup-prompts">${backup.prompt_count} prompts</span>
                    </div>
                    <div class="backup-user">Created by: ${backup.created_by}</div>
                </div>
            </div>
        </div>
    `;
}

// Create backup
async function createBackup() {
    const backupName = document.getElementById('backup-name').value.trim();

    showProgress('backup-progress', 'Creating backup...');

    try {
        const formData = new FormData();
        formData.append('name', backupName);

        const response = await fetch('/api/backups', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            showStatus('backup-status', `Backup created successfully: ${result.backup_id}`, 'success');
            document.getElementById('backup-name').value = '';
            loadBackups();
            loadBackupStats();
        } else {
            showStatus('backup-status', 'Failed to create backup', 'error');
        }
    } catch (error) {
        reportBackupIssue('createBackup', error, { backupName });
        showStatus('backup-status', 'Error creating backup', 'error');
    } finally {
        hideProgress('backup-progress');
    }
}

// Show restore confirmation modal
function showRestoreModal(backupId) {
    selectedBackupId = backupId;
    const backup = currentBackups.find(b => b.backup_id === backupId);

    if (!backup) return;

    const infoDiv = document.getElementById('restore-backup-info');
    infoDiv.innerHTML = `
        <strong>Backup:</strong> ${backup.backup_id}<br>
        <strong>Created:</strong> ${new Date(backup.timestamp).toLocaleString()}<br>
        <strong>Size:</strong> ${formatBytes(backup.size_bytes)}<br>
        <strong>Prompts:</strong> ${backup.prompt_count}
    `;

    document.getElementById('restore-modal').classList.remove('is-hidden');
}

// Hide restore modal
function hideRestoreModal() {
    document.getElementById('restore-modal').classList.add('is-hidden');
    selectedBackupId = null;
}

// Confirm restore
async function confirmRestore() {
    if (!selectedBackupId) return;

    const backupIdToRestore = selectedBackupId; // Store the ID before hiding modal
    hideRestoreModal();
    showProgress('backup-progress', 'Restoring backup...');

    try {
        const response = await fetch(`/api/backups/${backupIdToRestore}/restore`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            showStatus('backup-status', 'Backup restored successfully', 'success');
            // Reload the page to show restored data
            setTimeout(() => {
                window.location.href = '/';
            }, 2000);
        } else {
            showStatus('backup-status', 'Failed to restore backup', 'error');
        }
    } catch (error) {
        reportBackupIssue('restoreBackup', error, { backupId: backupIdToRestore });
        showStatus('backup-status', 'Error restoring backup', 'error');
    } finally {
        hideProgress('backup-progress');
    }
}

// Show delete confirmation modal
function showDeleteModal(backupId) {
    selectedBackupId = backupId;
    const backup = currentBackups.find(b => b.backup_id === backupId);

    if (!backup) return;

    const infoDiv = document.getElementById('delete-backup-info');
    infoDiv.innerHTML = `
        <strong>Backup:</strong> ${backup.backup_id}<br>
        <strong>Created:</strong> ${new Date(backup.timestamp).toLocaleString()}<br>
        <strong>Size:</strong> ${formatBytes(backup.size_bytes)}
    `;

    document.getElementById('delete-modal').classList.remove('is-hidden');
}

// Hide delete modal
function hideDeleteModal() {
    document.getElementById('delete-modal').classList.add('is-hidden');
    selectedBackupId = null;
}

// Confirm delete
async function confirmDelete() {
    if (!selectedBackupId) return;

    const backupIdToDelete = selectedBackupId; // Store the ID before hiding modal
    hideDeleteModal();
    showProgress('backup-progress', 'Deleting backup...');

    try {
        const response = await fetch(`/api/backups/${backupIdToDelete}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            showStatus('backup-status', 'Backup deleted successfully', 'success');
            loadBackups();
            loadBackupStats();
        } else {
            showStatus('backup-status', 'Failed to delete backup', 'error');
        }
    } catch (error) {
        reportBackupIssue('deleteBackup', error, { backupId: backupIdToDelete });
        showStatus('backup-status', 'Error deleting backup', 'error');
    } finally {
        hideProgress('backup-progress');
    }
}

// Cleanup old backups
async function cleanupBackups() {
    const retentionDays = document.getElementById('retention-days').value;

    showProgress('maintenance-progress', 'Cleaning up old backups...');

    try {
        const formData = new FormData();
        formData.append('retention_days', retentionDays);

        const response = await fetch('/api/backups/cleanup', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            showStatus('maintenance-status', `Cleanup completed: ${result.removed_count} backups removed`, 'success');
            loadBackups();
            loadBackupStats();
        } else {
            showStatus('maintenance-status', 'Cleanup failed', 'error');
        }
    } catch (error) {
        reportBackupIssue('cleanupBackups', error, { retentionDays });
        showStatus('maintenance-status', 'Error cleaning up backups', 'error');
    } finally {
        hideProgress('maintenance-progress');
    }
}

// Compress old backups
async function compressBackups() {
    const compressDays = document.getElementById('compress-days').value;

    showProgress('maintenance-progress', 'Compressing old backups...');

    try {
        const formData = new FormData();
        formData.append('days_threshold', compressDays);

        const response = await fetch('/api/backups/compress', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            showStatus('maintenance-status', `Compression completed: ${result.compressed_count} backups compressed`, 'success');
            loadBackups();
            loadBackupStats();
        } else {
            showStatus('maintenance-status', 'Compression failed', 'error');
        }
    } catch (error) {
        reportBackupIssue('compressBackups', error, { daysThreshold: compressDays });
        showStatus('maintenance-status', 'Error compressing backups', 'error');
    } finally {
        hideProgress('maintenance-progress');
    }
}

// Refresh backups
function refreshBackups() {
    loadBackups();
    loadBackupStats();
}

// Clear backup form
function clearBackupForm() {
    document.getElementById('backup-name').value = '';
}

// Utility functions
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showProgress(containerId, message) {
    const container = document.getElementById(containerId);
    const fill = document.getElementById(containerId + '-fill');
    const status = document.getElementById(containerId.replace('-progress', '-status'));

    container.classList.remove('is-hidden');
    fill.style.width = '50%';
    status.textContent = message;
    status.className = 'status-message status-info';
}

function hideProgress(containerId) {
    document.getElementById(containerId).classList.add('is-hidden');
}

function showStatus(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `status-message status-${type}`;

    const container = element.closest('.progress-container');
    if (container) {
        container.classList.remove('is-hidden');
    }

    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            if (container) {
                container.classList.add('is-hidden');
            }
        }, 5000);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Language selector
    const languageSelector = document.getElementById('language-selector');
    if (languageSelector) {
        languageSelector.addEventListener('change', handleLanguageChange);
    }

    // Modal event listeners
    const confirmRestoreBtn = document.getElementById('confirm-restore-btn');
    if (confirmRestoreBtn) {
        confirmRestoreBtn.addEventListener('click', confirmRestore);
    }

    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', confirmDelete);
    }
}

// Handle language change
function handleLanguageChange(event) {
    const selectedLanguage = event.target.value;
    i18next.changeLanguage(selectedLanguage, (err, t) => {
        if (err) {
            reportBackupIssue('changeLanguage', err, { language: selectedLanguage });
            return;
        }
        // Update all translations on the page
        updateContent();
    });
}

// Check admin access and show admin button if user is admin
async function checkAdminAccess() {
    try {
        console.log('Checking authentication...');
        const response = await fetch('/api/auth/me', {
            credentials: 'include'
        });

        console.log('Response status:', response.status);
        if (response.ok) {
            const data = await response.json();
            console.log('User data:', data);
            console.log('User role:', data.role);

            if (data.role === 'admin') {
                console.log('User is admin, showing button');
                const adminBtn = document.getElementById('admin-btn');
                console.log('Admin button element:', adminBtn);
                if (adminBtn) {
                    adminBtn.style.display = '';
                    console.log('Admin button should now be visible');
                }
            } else {
                console.log('User is not admin, role is:', data.role);
            }
        } else if (response.status === 401) {
            // Session revoked or expired, redirect to login immediately
            console.log('Session invalid, redirecting to login');
            window.location.href = '/auth/login';
        } else {
            console.log('Response not OK:', response.statusText);
            // For other errors, also redirect to login for security
            window.location.href = '/auth/login';
        }
    } catch (error) {
        console.error('Failed to check authentication:', error);
        // On error, redirect to login for security
        window.location.href = '/auth/login';
    }
}
