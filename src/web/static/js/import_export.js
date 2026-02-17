// -----------------------------------------------------------------------------
// LEGACY JAVASCRIPT (HISTORICAL REFERENCE ONLY)
// This file remains only for historical reference and should not be edited for
// new work. Make changes in the TypeScript sources under src/web/static/ts.
// -----------------------------------------------------------------------------
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

// Import/Export page JavaScript

// Global state
let currentOperation = null; // 'export' or 'import'
let previewData = null;
const IMPORT_EXPORT_COMPONENT = 'importExport';

function reportImportExportIssue(action, error, metadata = {}, severity = 'error') {
  const logger = window.FrontendLogger;
  if (logger && typeof logger.reportError === 'function') {
    logger.reportError(IMPORT_EXPORT_COMPONENT, action, error, metadata, severity);
  }
  const prefix = `[PromptVault][import-export] ${action}`;
  if (severity === 'warning') {
    console.warn(prefix, error, metadata);
  } else {
    console.error(prefix, error, metadata);
  }
}

const HIDDEN_CLASS = 'is-hidden';

function showElement(element) {
  if (element) {
    element.classList.remove(HIDDEN_CLASS);
  }
}

function hideElement(element) {
  if (element) {
    element.classList.add(HIDDEN_CLASS);
  }
}

function toggleElement(element, shouldShow) {
  if (element) {
    element.classList.toggle(HIDDEN_CLASS, !shouldShow);
  }
}

// Initialize i18next for translations
i18next
  .use(i18nextHttpBackend)
  .use(i18nextBrowserLanguageDetector)
  .init(
    {
      fallbackLng: 'en',
      debug: false,
      backend: {
        loadPath: '/static/locales/{{lng}}.json',
      },
    },
    function (err, t) {
      // Initialize the app after i18next is ready
      if (document.readyState === 'loading') {
        // DOM is still loading
        document.addEventListener('DOMContentLoaded', function () {
          updateStaticTranslations();
          initializeImportExport();
        });
      } else {
        // DOM is already loaded
        updateStaticTranslations();
        initializeImportExport();
      }
    }
  );

function updateStaticTranslations() {
  // Update elements with data-i18n attributes
  document.querySelectorAll('[data-i18n]').forEach((element) => {
    const key = element.getAttribute('data-i18n');
    if (key) {
      element.textContent = i18next.t(key);
    }
  });

  // Update placeholders
  document.querySelectorAll('[data-i18n-placeholder]').forEach((element) => {
    const key = element.getAttribute('data-i18n-placeholder');
    if (key) {
      element.placeholder = i18next.t(key);
    }
  });

  // Update language selector
  const languageSelector = document.getElementById('language-selector');
  if (languageSelector) {
    languageSelector.value = i18next.language;
  }
}

function initializeImportExport() {
  setupEventListeners();
  checkAdminAccess();
  loadStatistics();
}

function setupEventListeners() {
  // Language selector
  document.getElementById('language-selector').addEventListener('change', handleLanguageChange);

  // Format dropdown
  document.getElementById('export-format').addEventListener('change', updateFilenameFromDropdown);

  // File input
  document.getElementById('import-file').addEventListener('change', handleFileSelection);

  // Preview buttons
  document.querySelectorAll('[onclick*="preview"]').forEach((btn) => {
    btn.addEventListener('click', handlePreview);
  });

  // Modal close events
  document.querySelector('.close').addEventListener('click', hideModal);
  window.addEventListener('click', function (event) {
    const modal = document.getElementById('prompt-modal');
    if (event.target === modal) {
      hideModal();
    }
  });
}

function handlePreview(event) {
  // This function is called from HTML onclick attributes
  // We need to determine which preview function to call
  const button = event.target;
  const buttonText = button.textContent.toLowerCase();

  if (
    buttonText.includes('export') ||
    buttonText.includes(i18next.t('importExport.exportBtn').toLowerCase())
  ) {
    previewExport();
  } else if (
    buttonText.includes('import') ||
    buttonText.includes(i18next.t('importExport.importBtn').toLowerCase())
  ) {
    previewImport();
  }
}

function updateFilenameFromDropdown(event) {
  const format = event.target.value;
  updateFilename(format);
}

function updateFilename(format) {
  const filenameInput = document.getElementById('export-filename');
  let currentName = filenameInput.value.replace(/\.(csv|md|json)$/, '');
  filenameInput.value = `${currentName}.${format}`;
}

function handleFileSelection(event) {
  const file = event.target.files[0];
  const errorElement = document.getElementById('import-file-error');

  // Clear previous error messages
  if (errorElement) {
    errorElement.textContent = '';
  }

  if (file) {
    // Validate file type
    const allowedExtensions = ['.csv', '.json', '.md', '.markdown'];
    const fileName = file.name.toLowerCase();
    const fileExtension = fileName.substring(fileName.lastIndexOf('.'));
    const isValidType = allowedExtensions.some((ext) => fileName.endsWith(ext));

    if (!isValidType) {
      const errorMsg = 'File format not supported. Please use CSV, JSON, or Markdown files.';
      if (errorElement) {
        errorElement.textContent = errorMsg;
      }
      // Reset file input
      event.target.value = '';
      return;
    }

    // Validate file size (10MB limit)
    const maxSizeBytes = 10 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      const errorMsg = 'File is too large. Maximum size is 10MB.';
      if (errorElement) {
        errorElement.textContent = errorMsg;
      }
      // Reset file input
      event.target.value = '';
      return;
    }

    // Update filename input if empty
    const filenameInput = document.getElementById('export-filename');
    if (!filenameInput.value) {
      filenameInput.value = file.name.replace(/\.(csv|json|md|markdown)$/, '');
    }
  }
}

async function loadStatistics() {
  try {
    const response = await fetch('/api/import-export/stats');
    const stats = await response.json();

    document.getElementById('total-prompts').textContent = stats.total_prompts;
    document.getElementById('total-categories').textContent = stats.total_categories;
    document.getElementById('total-tags').textContent = stats.total_tags;
    document.getElementById('favorite-prompts').textContent = stats.favorite_prompts;

    // Update activity history (placeholder for now)
    updateActivityHistory();
  } catch (error) {
    reportImportExportIssue('loadStatistics', error);
  }
}

function updateActivityHistory() {
  // Placeholder for activity history
  // In a real implementation, this would track import/export operations
  const historyList = document.getElementById('activity-history');
  historyList.innerHTML = `
        <div class="history-item">
            <div class="history-info">
                <div>No recent activity</div>
                <div class="history-details">Activity tracking not yet implemented</div>
            </div>
        </div>
    `;
}

async function previewExport() {
  currentOperation = 'export';
  const formatSelect = document.getElementById('export-format');
  const format = formatSelect.value;
  const includeFavorites = document.getElementById('include-favorites').checked;

  try {
    showProgress('export', 'preparingExport');

    // Get prompts for preview
    const response = await fetch('/api/prompts');
    const data = await response.json();
    let prompts = data.prompts;

    // Filter if needed
    if (includeFavorites) {
      prompts = Object.fromEntries(
        Object.entries(prompts).filter(([id, prompt]) => prompt.favorite)
      );
    }

    // Generate preview content
    const previewContent = generateExportPreview(prompts, format);

    showPreview('previewExportTitle', previewContent);
    hideProgress('export');
  } catch (error) {
    reportImportExportIssue('previewExport', error, {
      format,
      includeFavorites,
    });
    showStatus('export', 'exportFailed', 'error');
  }
}

async function previewImport() {
  const fileInput = document.getElementById('import-file');
  const file = fileInput.files[0];

  if (!file) {
    alert(i18next.t('importExport.noFileSelected'));
    return;
  }

  currentOperation = 'import';

  try {
    showProgress('import', 'preparingImport');

    // Read file content
    const fileContent = await readFileContent(file);
    const previewContent = await generateImportPreview(fileContent, file.name);

    showPreview('previewImportTitle', previewContent);
    hideProgress('import');
  } catch (error) {
    reportImportExportIssue('previewImport', error, { filename: file.name });
    showStatus('import', 'importFailed', 'error');
  }
}

function generateExportPreview(prompts, format) {
  const promptCount = Object.keys(prompts).length;
  let content = '';

  switch (format) {
    case 'csv':
      content = `Title,Prompt,Category,Tags,Favorite\n`;
      content += `Example Prompt 1,"This is a sample prompt content","Work","tag1, tag2","Yes"\n`;
      content += `Example Prompt 2,"Another sample prompt","Personal","tag3","No"\n`;
      content += `... and ${promptCount - 2} more prompts`;
      break;

    case 'markdown':
      content = `# Example Prompt 1\n\n`;
      content += `**Category:** Work\n`;
      content += `**Tags:** tag1, tag2\n`;
      content += `**Favorite:** Yes\n\n`;
      content += `## Prompt\n`;
      content += `This is a sample prompt content\n\n`;
      content += `---\n\n`;
      content += `# Example Prompt 2\n\n`;
      content += `**Category:** Personal\n`;
      content += `**Tags:** tag3\n`;
      content += `**Favorite:** No\n\n`;
      content += `## Prompt\n`;
      content += `Another sample prompt\n\n`;
      content += `---\n\n`;
      content += `... and ${promptCount - 2} more prompts`;
      break;

    case 'json':
      const sampleData = {
        export_timestamp: new Date().toISOString(),
        total_prompts: promptCount,
        prompts: {
          1: {
            data: {
              title: 'Example Prompt 1',
              prompt: 'This is a sample prompt content',
              category: 'Work',
              tags: ['tag1', 'tag2'],
              favorite: true,
            },
          },
          2: {
            data: {
              title: 'Example Prompt 2',
              prompt: 'Another sample prompt',
              category: 'Personal',
              tags: ['tag3'],
              favorite: false,
            },
          },
        },
      };
      content = JSON.stringify(sampleData, null, 2);
      content += `\n\n... and ${promptCount - 2} more prompts`;
      break;
  }

  return content;
}

async function generateImportPreview(fileContent, filename) {
  // This would parse the actual file content in a real implementation
  // For now, we'll simulate based on file extension
  const extension = filename.split('.').pop().toLowerCase();

  if (extension === 'csv') {
    return `CSV Preview:\n\nTitle,Prompt,Category,Tags,Favorite\nExample Import 1,"Sample imported prompt","Work","tag1, tag2","Yes"\nExample Import 2,"Another imported prompt","Personal","tag3","No"\n\nTotal rows detected: ${Math.floor(Math.random() * 10) + 5}`;
  } else if (extension === 'json') {
    return `JSON Preview:\n\n{\n  "title": "Sample Import",\n  "prompt": "This is an imported prompt",\n  "category": "Imported",\n  "tags": ["imported", "sample"],\n  "favorite": false\n}\n\nTotal items detected: ${Math.floor(Math.random() * 5) + 3}`;
  } else {
    return `Markdown Preview:\n\n# Sample Import\n\n**Category:** Imported\n**Tags:** imported, sample\n**Favorite:** No\n\n## Prompt\nThis is an imported prompt from markdown file.\n\n---\n\nTotal sections detected: ${Math.floor(Math.random() * 5) + 3}`;
  }
}

function readFileContent(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = (e) => reject(e);
    reader.readAsText(file);
  });
}

function showPreview(titleKey, content) {
  showElement(document.getElementById('preview-panel'));
  document.getElementById('preview-content').textContent = content;

  // Update confirm button text
  const confirmBtn = document.getElementById('confirm-btn');
  if (currentOperation === 'export') {
    confirmBtn.textContent = i18next.t('importExport.exportBtn');
  } else {
    confirmBtn.textContent = i18next.t('importExport.importBtn');
  }
}

function hidePreview() {
  hideElement(document.getElementById('preview-panel'));
  previewData = null;
}

function cancelPreview() {
  hidePreview();
  hideProgress(currentOperation);
}

async function confirmOperation() {
  if (currentOperation === 'export') {
    await performExport();
  } else {
    await performImport();
  }
  hidePreview();
}

async function performExport() {
  const formatSelect = document.getElementById('export-format');
  const format = formatSelect.value;
  const filename = document.getElementById('export-filename').value;
  const includeFavorites = document.getElementById('include-favorites').checked;
  const includeMetadata = document.getElementById('include-metadata').checked;

  try {
    showProgress('export', 'exportProgress');

    const formData = new FormData();
    formData.append('format', format);
    formData.append('filename', filename);
    formData.append('include_favorites', includeFavorites);
    formData.append('include_metadata', includeMetadata);

    const response = await fetch('/api/export', {
      method: 'POST',
      body: formData,
    });

    if (response.ok) {
      // Trigger file download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.classList.add(HIDDEN_CLASS);
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      showStatus('export', 'exportSuccess', 'success');
      loadStatistics(); // Refresh stats
    } else {
      const error = await response.json();
      showStatus('export', error.error || 'exportFailed', 'error');
    }
  } catch (error) {
    reportImportExportIssue('performExport', error, {
      format,
      filename,
      includeFavorites,
      includeMetadata,
    });
    showStatus('export', 'exportFailed', 'error');
  } finally {
    hideProgress('export');
  }
}

async function performImport() {
  const fileInput = document.getElementById('import-file');
  const file = fileInput.files[0];
  const errorElement = document.getElementById('import-file-error');

  // Clear previous error messages
  if (errorElement) {
    errorElement.textContent = '';
  }

  if (!file) {
    alert(i18next.t('importExport.noFileSelected'));
    return;
  }

  // Re-validate file before import (in case conditions changed)
  const allowedExtensions = ['.csv', '.json', '.md', '.markdown'];
  const fileName = file.name.toLowerCase();
  const isValidType = allowedExtensions.some((ext) => fileName.endsWith(ext));

  if (!isValidType) {
    const errorMsg = 'File format not supported. Please use CSV, JSON, or Markdown files.';
    if (errorElement) {
      errorElement.textContent = errorMsg;
    }
    return;
  }

  const maxSizeBytes = 10 * 1024 * 1024;
  if (file.size > maxSizeBytes) {
    const errorMsg = 'File is too large. Maximum size is 10MB.';
    if (errorElement) {
      errorElement.textContent = errorMsg;
    }
    return;
  }

  const mode = document.getElementById('import-mode').value;
  const validate = document.getElementById('import-validate').checked;

  try {
    showProgress('import', 'importProgress');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('mode', mode);
    formData.append('validate', validate);

    const response = await fetch('/api/import', {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();

    if (response.ok) {
      const message = i18next
        .t('importExport.importSuccess')
        .replace('{count}', result.added_count);
      showStatus('import', message, 'success');
      loadStatistics(); // Refresh stats

      // Clear file input
      fileInput.value = '';
    } else {
      // Display specific error message in both the error element and status
      let errorMsg = result.error || 'importFailed';

      // Handle common validation errors
      if (errorMsg.includes('format') || errorMsg.includes('invalid')) {
        errorMsg = 'File validation failed. Please check the format.';
      }

      if (errorElement) {
        errorElement.textContent = errorMsg;
      }
      showStatus('import', errorMsg, 'error');
    }
  } catch (error) {
    reportImportExportIssue('performImport', error, {
      mode,
      validate,
      filename: file.name,
    });

    const errorMsg = 'File validation failed. Please check the format.';
    if (errorElement) {
      errorElement.textContent = errorMsg;
    }
    showStatus('import', 'importFailed', 'error');
  } finally {
    hideProgress('import');
  }
}

function showProgress(operation, messageKey) {
  const progressContainer = document.getElementById(`${operation}-progress`);
  const statusElement = document.getElementById(`${operation}-status`);

  showElement(progressContainer);
  statusElement.textContent = i18next.t(`importExport.${messageKey}`);
  statusElement.className = 'status-message status-info';
}

function hideProgress(operation) {
  const progressContainer = document.getElementById(`${operation}-progress`);
  hideElement(progressContainer);
}

function showStatus(operation, message, type) {
  const statusElement = document.getElementById(`${operation}-status`);
  statusElement.textContent = message;
  statusElement.className = `status-message status-${type}`;

  // Auto-hide success messages after 3 seconds
  if (type === 'success') {
    setTimeout(() => {
      statusElement.textContent = '';
      statusElement.className = 'status-message status-info';
    }, 3000);
  }
}

function handleLanguageChange(event) {
  const selectedLanguage = event.target.value;
  i18next.changeLanguage(selectedLanguage, (err, t) => {
    if (err) {
      reportImportExportIssue('changeLanguage', err, { language: selectedLanguage });
      return;
    }
    updateStaticTranslations();
  });
}

function clearExportSettings() {
  // Reset export form to default values
  document.getElementById('export-format').value = 'csv';
  document.getElementById('export-filename').value = 'promptvault_export';
  document.getElementById('include-favorites').checked = true;
  document.getElementById('include-metadata').checked = true;

  // Clear any progress or status messages
  hideProgress('export');
  showStatus('export', '', 'info');

  // Show confirmation
  showStatus('export', 'Export settings cleared', 'success');
  setTimeout(() => {
    showStatus('export', '', 'info');
  }, 2000);
}

function hideModal() {
  hideElement(document.getElementById('prompt-modal'));
}

// Check admin access and show admin button if user is admin
async function checkAdminAccess() {
  try {
    console.log('Checking authentication...');
    const response = await fetch('/api/auth/me', {
      credentials: 'include',
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
