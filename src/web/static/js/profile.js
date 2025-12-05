/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

// Profile Management JavaScript

// Initialize i18next
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
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initProfilePage);
        } else {
            initProfilePage();
        }
    });

// Constants
const API_BASE = '/api/auth';
const HIDDEN_CLASS = 'is-hidden';

// Utility Functions
function getAuthHeaders() {
    // With HTTP-only cookies, credentials are sent automatically
    return {
        'Content-Type': 'application/json'
    };
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function showError(element, message) {
    if (element) {
        element.textContent = message;
        element.classList.add('validation-error-visible');
    }
}

function clearError(element) {
    if (element) {
        element.textContent = '';
        element.classList.remove('validation-error-visible');
    }
}

function clearAllErrors() {
    document.querySelectorAll('.validation-error').forEach(el => clearError(el));
}

function updateTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (key) {
            if (key.includes('[') && key.includes(']')) {
                const match = key.match(/\[(\w+)\](.+)/);
                if (match) {
                    const attribute = match[1];
                    const translationKey = match[2];
                    const translation = i18next.t(translationKey);
                    if (translation) {
                        element.setAttribute(attribute, translation);
                    }
                }
            } else {
                element.textContent = i18next.t(key);
            }
        }
    });

    const languageSelector = document.getElementById('language-selector');
    if (languageSelector) {
        languageSelector.value = i18next.language;
    }
}

function formatDate(dateString) {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Password Strength Checker
function checkPasswordStrength(password) {
    const checks = {
        length: password.length >= 12,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        digit: /[0-9]/.test(password),
        special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
    };

    let strength = Object.values(checks).filter(v => v).length;
    return { strength, checks };
}

function updatePasswordStrength(password) {
    const { strength, checks } = checkPasswordStrength(password);
    const strengthBar = document.getElementById('strength-bar-fill');
    const strengthText = document.getElementById('strength-text');

    if (!strengthBar || !strengthText) return;

    strengthBar.className = 'strength-bar-fill';
    if (strength >= 5) {
        strengthBar.classList.add('strength-strong');
        strengthText.textContent = i18next.t('auth.register.strengthStrong') || 'Strong password';
        strengthText.className = 'strength-text strength-strong';
    } else if (strength >= 3) {
        strengthBar.classList.add('strength-medium');
        strengthText.textContent = i18next.t('auth.register.strengthMedium') || 'Medium password';
        strengthText.className = 'strength-text strength-medium';
    } else if (password.length > 0) {
        strengthBar.classList.add('strength-weak');
        strengthText.textContent = i18next.t('auth.register.strengthWeak') || 'Weak password';
        strengthText.className = 'strength-text strength-weak';
    } else {
        strengthText.textContent = '';
    }

    updatePolicyRequirements(checks);
}

function updatePolicyRequirements(checks) {
    const policyMap = {
        length: 'policy-length',
        uppercase: 'policy-uppercase',
        lowercase: 'policy-lowercase',
        digit: 'policy-digit',
        special: 'policy-special'
    };

    Object.entries(checks).forEach(([check, met]) => {
        const element = document.getElementById(policyMap[check]);
        if (element) {
            if (met) {
                element.classList.add('met');
            } else {
                element.classList.remove('met');
            }
        }
    });
}

function setupPasswordToggle(toggleButtonId, passwordInputId) {
    const toggleButton = document.getElementById(toggleButtonId);
    const passwordInput = document.getElementById(passwordInputId);

    if (toggleButton && passwordInput) {
        toggleButton.addEventListener('click', () => {
            const type = passwordInput.type === 'password' ? 'text' : 'password';
            passwordInput.type = type;
        });
    }
}

// Load User Info
async function loadUserInfo() {
    try {
        const response = await fetch(`${API_BASE}/me`, {
            credentials: 'include',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            const user = await response.json();

            // Update profile info
            document.getElementById('user-username').textContent = user.username;
            document.getElementById('user-email').textContent = user.email;
            document.getElementById('user-role').textContent = user.role.toUpperCase();

            // Set avatar initial
            const avatar = document.getElementById('user-avatar');
            avatar.textContent = user.username.charAt(0).toUpperCase();

            // Update stats
            document.getElementById('user-created').textContent = formatDate(user.created_at);
            document.getElementById('user-last-login').textContent = formatDate(user.last_login);

            // Show admin button if user is admin
            if (user.role === 'admin') {
                const adminBtn = document.getElementById('admin-btn');
                if (adminBtn) {
                    adminBtn.style.display = '';
                }
            }

            // Load sessions
            await loadSessions();
        } else if (response.status === 401) {
            // Token expired, redirect to login
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/auth/login';
        }
    } catch (error) {
        console.error('Error loading user info:', error);
        showNotification(i18next.t('messages.error') || 'Failed to load user info', 'error');
    }
}

// Load Sessions
async function loadSessions() {
    const sessionsList = document.getElementById('sessions-list');
    sessionsList.innerHTML = '<div class="loading" data-i18n="messages.loading">Loading...</div>';

    try {
        const response = await fetch(`${API_BASE}/sessions`, {
            credentials: 'include',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            const data = await response.json();
            const sessions = data.sessions || [];

            // Update session count
            document.getElementById('session-count').textContent = sessions.length;

            // Render sessions
            if (sessions.length === 0) {
                sessionsList.innerHTML = '<p>No active sessions</p>';
            } else {
                sessionsList.innerHTML = sessions.map(session => `
                    <div class="session-item ${session.is_current ? 'current-session' : ''}" data-session-id="${session.id}">
                        <div class="session-info">
                            <div class="session-device">${session.user_agent || 'Unknown Device'}</div>
                            <div class="session-details">
                                IP: ${session.ip_address || 'Unknown'} |
                                Last used: ${formatDate(session.last_used_at)}
                                ${session.is_current ? ' | <strong>Current Session</strong>' : ''}
                            </div>
                        </div>
                        <div class="session-actions">
                            <button onclick="revokeSession('${session.id}')" ${session.is_current ? 'disabled' : ''}>
                                ${i18next.t('auth.profile.revokeSession') || 'Revoke'}
                            </button>
                        </div>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Error loading sessions:', error);
        sessionsList.innerHTML = '<p class="error">Failed to load sessions</p>';
    }
}

// Revoke Session
window.revokeSession = async function(sessionId) {
    if (!confirm(i18next.t('auth.profile.confirmRevokeSession') || 'Are you sure you want to revoke this session?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
            credentials: 'include',
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            showNotification(i18next.t('auth.profile.sessionRevoked') || 'Session revoked successfully', 'success');
            await loadSessions();
        } else {
            showNotification(i18next.t('messages.error') || 'Failed to revoke session', 'error');
        }
    } catch (error) {
        console.error('Error revoking session:', error);
        showNotification(i18next.t('messages.error') || 'Failed to revoke session', 'error');
    }
};

// Change Password Form
function setupChangePasswordForm() {
    const form = document.getElementById('change-password-form');
    if (!form) return;

    setupPasswordToggle('toggle-current-password', 'current-password');
    setupPasswordToggle('toggle-new-password', 'new-password');
    setupPasswordToggle('toggle-confirm-new-password', 'confirm-new-password');

    const newPasswordInput = document.getElementById('new-password');
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', () => {
            updatePasswordStrength(newPasswordInput.value);
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        clearAllErrors();

        const currentPassword = document.getElementById('current-password').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmNewPassword = document.getElementById('confirm-new-password').value;

        // Validation
        let hasErrors = false;

        if (!currentPassword) {
            showError(document.getElementById('current-password-error'), i18next.t('auth.profile.currentPasswordRequired') || 'Current password is required');
            hasErrors = true;
        }

        const { checks } = checkPasswordStrength(newPassword);
        if (!Object.values(checks).every(v => v)) {
            showError(document.getElementById('new-password-error'), i18next.t('auth.register.passwordPolicy') || 'Password does not meet requirements');
            hasErrors = true;
        }

        if (newPassword !== confirmNewPassword) {
            showError(document.getElementById('confirm-new-password-error'), i18next.t('auth.register.passwordMismatch') || 'Passwords do not match');
            hasErrors = true;
        }

        if (hasErrors) return;

        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.textContent = i18next.t('messages.loading') || 'Loading...';

        try {
            const response = await fetch(`${API_BASE}/change-password`, {
                credentials: 'include',
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    old_password: currentPassword,
                    new_password: newPassword,
                    confirm_new_password: confirmNewPassword
                })
            });

            const data = await response.json();

            if (response.ok) {
                showNotification(i18next.t('auth.profile.passwordChanged') || 'Password changed successfully', 'success');
                form.reset();
                clearAllErrors();
            } else {
                if (response.status === 401) {
                    showError(document.getElementById('current-password-error'), data.detail || i18next.t('auth.profile.incorrectPassword') || 'Incorrect current password');
                } else {
                    showNotification(data.detail || i18next.t('messages.error') || 'Failed to change password', 'error');
                }
            }
        } catch (error) {
            console.error('Error changing password:', error);
            showNotification(i18next.t('messages.error') || 'Failed to change password', 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = i18next.t('auth.profile.updatePassword') || 'Update Password';
        }
    });
}

// Logout
function setupLogout() {
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            try {
                const refreshToken = localStorage.getItem('refresh_token');
                if (refreshToken) {
                    await fetch(`${API_BASE}/logout`, {
                        credentials: 'include',
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ refresh_token: refreshToken })
                    });
                }
            } catch (error) {
                console.error('Logout error:', error);
            } finally {
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                window.location.href = '/auth/login';
            }
        });
    }
}

// Initialize Page
function initProfilePage() {
    updateTranslations();

    const languageSelector = document.getElementById('language-selector');
    if (languageSelector) {
        languageSelector.addEventListener('change', (e) => {
            i18next.changeLanguage(e.target.value, () => {
                updateTranslations();
            });
        });
    }

    loadUserInfo();
    setupChangePasswordForm();
    setupLogout();
}
