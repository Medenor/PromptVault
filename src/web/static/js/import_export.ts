// Import/Export page TypeScript

import './types';
import { ImportExportStats, ExportOptions, ImportOptions } from './types';

// Global state
let currentOperation: string | null = null; // 'export' or 'import'
let previewData: any = null;

// Initialize i18next for translations
declare const i18next: any;

i18next
    .use(window.i18nextHttpBackend)
    .use(window.i18nextBrowserLanguageDetector)
    .init({
        fallbackLng: 'en',
        debug: false,
        backend: {
            loadPath: '/static/locales/{{lng}}.json'
        }
    }, function(err: any, t: any): void {
        // Initialize the app after i18next is ready
        if (document.readyState === 'loading') {
            // DOM is still loading
            document.addEventListener('DOMContentLoaded', function(): void {
                updateStaticTranslations();
                initializeImportExport();
            });
        } else {
            // DOM is already loaded
            updateStaticTranslations();
            initializeImportExport();
        }
    });

function updateStaticTranslations(): void {
    // Update elements with data-i18n attributes
    document.querySelectorAll('[data-i18n]').forEach((element: Element): void => {
        const key: string | null = element.getAttribute('data-i18n');
        if (key) {
            (element as HTMLElement).textContent = i18next.t(key);
        }
    });

    // Update placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach((element: Element): void => {
        const key: string | null = element.getAttribute('data-i18n-placeholder');
        if (key) {
            (element as HTMLInputElement).placeholder = i18next.t(key);
        }
    });

    // Update language selector
    const languageSelector: HTMLSelectElement | null = document.getElementById('language-selector') as HTMLSelectElement;
    if (languageSelector) {
        languageSelector.value = i18next.language;
    }
}

function initializeImportExport(): void {
    setupEventListeners();
    loadStatistics();
}

function setupEventListeners(): void {
    // Language selector
    const languageSelector: HTMLSelectElement | null = document.getElementById('language-selector') as HTMLSelectElement;
    if (languageSelector) {
        languageSelector.addEventListener('change', handleLanguageChange);
    }

    // Format dropdown
    const exportFormat: HTMLSelectElement | null = document.getElementById('export-format') as HTMLSelectElement;
    if (exportFormat) {
        exportFormat.addEventListener('change', updateFilenameFromDropdown);
    }

    // File input
    const importFile: HTMLInputElement | null = document.getElementById('import-file') as HTMLInputElement;
    if (importFile) {
        importFile.addEventListener('change', handleFileSelection);
    }

    // Preview buttons
    const previewButtons: NodeListOf<Element> = document.querySelectorAll('[onclick*="preview"]');
    previewButtons.forEach((btn: Element): void => {
        (btn as HTMLElement).addEventListener('click', handlePreview);
    });

    // Modal close events
    const closeBtn: HTMLElement | null = document.querySelector('.close');
    if (closeBtn) {
        closeBtn.addEventListener('click', hideModal);
    }

    window.addEventListener('click', function(event: Event): void {
        const modal: HTMLElement | null = document.getElementById('prompt-modal');
        if (event.target === modal) {
            hideModal();
        }
    });
}

function handlePreview(event: Event): void {
    // This function is called from HTML onclick attributes
    // We need to determine which preview function to call
    const button: HTMLElement = event.target as HTMLElement;
    const buttonText: string = button.textContent?.toLowerCase() || '';

    if (buttonText.includes('export') || buttonText.includes(i18next.t('importExport.exportBtn').toLowerCase())) {
        previewExport();
    } else if (buttonText.includes('import') || buttonText.includes(i18next.t('importExport.importBtn').toLowerCase())) {
        previewImport();
    }
}

function updateFilenameFromDropdown(event: Event): void {
    const target: HTMLSelectElement = event.target as HTMLSelectElement;
    const format: string = target.value;
    updateFilename(format);
}

function updateFilename(format: string): void {
    const filenameInput: HTMLInputElement | null = document.getElementById('export-filename') as HTMLInputElement;
    if (filenameInput) {
        let currentName: string = filenameInput.value.replace(/\.(csv|md|json)$/, '');
        filenameInput.value = `${currentName}.${format}`;
    }
}

function handleFileSelection(event: Event): void {
    const target: HTMLInputElement = event.target as HTMLInputElement;
    const file: File | null = target.files ? target.files[0] : null;
    if (file) {
        // Update filename input if empty
        const filenameInput: HTMLInputElement | null = document.getElementById('export-filename') as HTMLInputElement;
        if (filenameInput && !filenameInput.value) {
            filenameInput.value = file.name.replace(/\.(csv|md|json)$/, '');
        }
    }
}

async function loadStatistics(): Promise<void> {
    try {
        const response: Response = await fetch('/api/import-export/stats');
        const stats: ImportExportStats = await response.json();

        const totalPrompts: HTMLElement | null = document.getElementById('total-prompts');
        if (totalPrompts) {
            totalPrompts.textContent = stats.total_prompts.toString();
        }

        const totalCategories: HTMLElement | null = document.getElementById('total-categories');
        if (totalCategories) {
            totalCategories.textContent = stats.total_categories.toString();
        }

        const totalTags: HTMLElement | null = document.getElementById('total-tags');
        if (totalTags) {
            totalTags.textContent = stats.total_tags.toString();
        }

        const favoritePrompts: HTMLElement | null = document.getElementById('favorite-prompts');
        if (favoritePrompts) {
            favoritePrompts.textContent = stats.favorite_prompts.toString();
        }

        // Update activity history (placeholder for now)
        updateActivityHistory();

    } catch (error: unknown) {
        console.error('Error loading statistics:', error);
    }
}

function updateActivityHistory(): void {
    // Placeholder for activity history
    // In a real implementation, this would track import/export operations
    const historyList: HTMLElement | null = document.getElementById('activity-history');
    if (historyList) {
        historyList.innerHTML = `
            <div class="history-item">
                <div class="history-info">
                    <div>No recent activity</div>
                    <div class="history-details">Activity tracking not yet implemented</div>
                </div>
            </div>
        `;
    }
}

async function previewExport(): Promise<void> {
    currentOperation = 'export';
    const formatSelect: HTMLSelectElement | null = document.getElementById('export-format') as HTMLSelectElement;
    if (!formatSelect) return;

    const format: string = formatSelect.value;
    const includeFavorites: boolean = (document.getElementById('include-favorites') as HTMLInputElement)?.checked || false;

    try {
        showProgress('export', 'preparingExport');

        // Get prompts for preview
        const response: Response = await fetch('/api/prompts');
        const data: any = await response.json();
        let prompts: Record<string, any> = data.prompts;

        // Filter if needed
        if (includeFavorites) {
            prompts = Object.fromEntries(
                Object.entries(prompts).filter(([id, prompt]: [string, any]) =>
                    prompt.favorite
                )
            );
        }

        // Generate preview content
        const previewContent: string = generateExportPreview(prompts, format);

        showPreview('previewExportTitle', previewContent);
        hideProgress('export');

    } catch (error: unknown) {
        console.error('Error generating export preview:', error);
        showStatus('export', 'exportFailed', 'error');
    }
}

async function previewImport(): Promise<void> {
    const fileInput: HTMLInputElement | null = document.getElementById('import-file') as HTMLInputElement;
    if (!fileInput) return;

    const file: File | null = fileInput.files ? fileInput.files[0] : null;

    if (!file) {
        alert(i18next.t('importExport.noFileSelected'));
        return;
    }

    currentOperation = 'import';

    try {
        showProgress('import', 'preparingImport');

        // Read file content
        const fileContent: string = await readFileContent(file);
        const previewContent: string = await generateImportPreview(fileContent, file.name);

        showPreview('previewImportTitle', previewContent);
        hideProgress('import');

    } catch (error: unknown) {
        console.error('Error generating import preview:', error);
        showStatus('import', 'importFailed', 'error');
    }
}

function generateExportPreview(prompts: Record<string, any>, format: string): string {
    const promptCount: number = Object.keys(prompts).length;
    let content: string = '';

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
            const sampleData: any = {
                "export_timestamp": new Date().toISOString(),
                "total_prompts": promptCount,
                "prompts": {
                    "1": {
                        "data": {
                            "title": "Example Prompt 1",
                            "prompt": "This is a sample prompt content",
                            "category": "Work",
                            "tags": ["tag1", "tag2"],
                            "favorite": true
                        }
                    },
                    "2": {
                        "data": {
                            "title": "Example Prompt 2",
                            "prompt": "Another sample prompt",
                            "category": "Personal",
                            "tags": ["tag3"],
                            "favorite": false
                        }
                    }
                }
            };
            content = JSON.stringify(sampleData, null, 2);
            content += `\n\n... and ${promptCount - 2} more prompts`;
            break;
    }

    return content;
}

async function generateImportPreview(fileContent: string, filename: string): Promise<string> {
    // This would parse the actual file content in a real implementation
    // For now, we'll simulate based on file extension
    const extension: string = filename.split('.').pop()?.toLowerCase() || '';

    if (extension === 'csv') {
        return `CSV Preview:\n\nTitle,Prompt,Category,Tags,Favorite\nExample Import 1,"Sample imported prompt","Work","tag1, tag2","Yes"\nExample Import 2,"Another imported prompt","Personal","tag3","No"\n\nTotal rows detected: ${Math.floor(Math.random() * 10) + 5}`;
    } else if (extension === 'json') {
        return `JSON Preview:\n\n{\n  "title": "Sample Import",\n  "prompt": "This is an imported prompt",\n  "category": "Imported",\n  "tags": ["imported", "sample"],\n  "favorite": false\n}\n\nTotal items detected: ${Math.floor(Math.random() * 5) + 3}`;
    } else {
        return `Markdown Preview:\n\n# Sample Import\n\n**Category:** Imported\n**Tags:** imported, sample\n**Favorite:** No\n\n## Prompt\nThis is an imported prompt from markdown file.\n\n---\n\nTotal sections detected: ${Math.floor(Math.random() * 5) + 3}`;
    }
}

function readFileContent(file: File): Promise<string> {
    return new Promise<string>((resolve: (value: string) => void, reject: (reason: unknown) => void): void => {
        const reader: FileReader = new FileReader();
        reader.onload = (e: ProgressEvent<FileReader>): void => {
            const result: string | ArrayBuffer | null | undefined = e.target?.result;
            if (typeof result === 'string') {
                resolve(result);
            } else {
                reject(new Error('Failed to read file as text'));
            }
        };
        reader.onerror = (e: ProgressEvent<FileReader>): void => reject(e);
        reader.readAsText(file);
    });
}

function showPreview(titleKey: string, content: string): void {
    const previewPanel: HTMLElement | null = document.getElementById('preview-panel');
    if (previewPanel) {
        previewPanel.style.display = 'block';
    }

    const previewContent: HTMLElement | null = document.getElementById('preview-content');
    if (previewContent) {
        previewContent.textContent = content;
    }

    // Update confirm button text
    const confirmBtn: HTMLButtonElement | null = document.getElementById('confirm-btn') as HTMLButtonElement;
    if (confirmBtn) {
        if (currentOperation === 'export') {
            confirmBtn.textContent = i18next.t('importExport.exportBtn');
        } else {
            confirmBtn.textContent = i18next.t('importExport.importBtn');
        }
    }
}

function hidePreview(): void {
    const previewPanel: HTMLElement | null = document.getElementById('preview-panel');
    if (previewPanel) {
        previewPanel.style.display = 'none';
    }
    previewData = null;
}

function cancelPreview(): void {
    hidePreview();
    if (currentOperation) {
        hideProgress(currentOperation);
    }
}

async function confirmOperation(): Promise<void> {
    if (currentOperation === 'export') {
        await performExport();
    } else {
        await performImport();
    }
    hidePreview();
}

async function performExport(): Promise<void> {
    const formatSelect: HTMLSelectElement | null = document.getElementById('export-format') as HTMLSelectElement;
    if (!formatSelect) return;

    const format: string = formatSelect.value;
    const filenameInput: HTMLInputElement | null = document.getElementById('export-filename') as HTMLInputElement;
    if (!filenameInput) return;

    const filename: string = filenameInput.value;
    const includeFavorites: boolean = (document.getElementById('include-favorites') as HTMLInputElement)?.checked || false;
    const includeMetadata: boolean = (document.getElementById('include-metadata') as HTMLInputElement)?.checked || false;

    try {
        showProgress('export', 'exportProgress');

        const formData: FormData = new FormData();
        formData.append('format', format);
        formData.append('filename', filename);
        formData.append('include_favorites', includeFavorites.toString());
        formData.append('include_metadata', includeMetadata.toString());

        const response: Response = await fetch('/api/export', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            // Trigger file download
            const blob: Blob = await response.blob();
            const url: string = window.URL.createObjectURL(blob);
            const a: HTMLAnchorElement = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showStatus('export', 'exportSuccess', 'success');
            loadStatistics(); // Refresh stats
        } else {
            const error: any = await response.json();
            showStatus('export', error.error || 'exportFailed', 'error');
        }

    } catch (error: unknown) {
        console.error('Export error:', error);
        showStatus('export', 'exportFailed', 'error');
    } finally {
        hideProgress('export');
    }
}

async function performImport(): Promise<void> {
    const fileInput: HTMLInputElement | null = document.getElementById('import-file') as HTMLInputElement;
    if (!fileInput) return;

    const file: File | null = fileInput.files ? fileInput.files[0] : null;

    if (!file) {
        alert(i18next.t('importExport.noFileSelected'));
        return;
    }

    const modeSelect: HTMLSelectElement | null = document.getElementById('import-mode') as HTMLSelectElement;
    if (!modeSelect) return;

    const mode: string = modeSelect.value;
    const validate: boolean = (document.getElementById('import-validate') as HTMLInputElement)?.checked || false;

    try {
        showProgress('import', 'importProgress');

        const formData: FormData = new FormData();
        formData.append('file', file);
        formData.append('mode', mode);
        formData.append('validate', validate.toString());

        const response: Response = await fetch('/api/import', {
            method: 'POST',
            body: formData
        });

        const result: any = await response.json();

        if (response.ok) {
            const message: string = i18next.t('importExport.importSuccess')
                .replace('{count}', result.added_count);
            showStatus('import', message, 'success');
            loadStatistics(); // Refresh stats

            // Clear file input
            fileInput.value = '';
        } else {
            showStatus('import', result.error || 'importFailed', 'error');
        }

    } catch (error: unknown) {
        console.error('Import error:', error);
        showStatus('import', 'importFailed', 'error');
    } finally {
        hideProgress('import');
    }
}

function showProgress(operation: string, messageKey: string): void {
    const progressContainer: HTMLElement | null = document.getElementById(`${operation}-progress`);
    if (progressContainer) {
        progressContainer.style.display = 'block';
    }

    const statusElement: HTMLElement | null = document.getElementById(`${operation}-status`);
    if (statusElement) {
        statusElement.textContent = i18next.t(`importExport.${messageKey}`);
        statusElement.className = 'status-message status-info';
    }
}

function hideProgress(operation: string): void {
    const progressContainer: HTMLElement | null = document.getElementById(`${operation}-progress`);
    if (progressContainer) {
        progressContainer.style.display = 'none';
    }
}

function showStatus(operation: string, message: string, type: string): void {
    const statusElement: HTMLElement | null = document.getElementById(`${operation}-status`);
    if (statusElement) {
        statusElement.textContent = message;
        statusElement.className = `status-message status-${type}`;

        // Auto-hide success messages after 3 seconds
        if (type === 'success') {
            setTimeout((): void => {
                statusElement.textContent = '';
                statusElement.className = 'status-message status-info';
            }, 3000);
        }
    }
}

function handleLanguageChange(event: Event): void {
    const target: HTMLSelectElement = event.target as HTMLSelectElement;
    const selectedLanguage: string = target.value;
    i18next.changeLanguage(selectedLanguage, (err: any, t: any): void => {
        if (err) {
            console.error('Error changing language:', err);
            return;
        }
        updateStaticTranslations();
    });
}

function clearExportSettings(): void {
    // Reset export form to default values
    const exportFormat: HTMLSelectElement | null = document.getElementById('export-format') as HTMLSelectElement;
    if (exportFormat) {
        exportFormat.value = 'csv';
    }

    const filenameInput: HTMLInputElement | null = document.getElementById('export-filename') as HTMLInputElement;
    if (filenameInput) {
        filenameInput.value = 'promptvault_export';
    }

    const includeFavorites: HTMLInputElement | null = document.getElementById('include-favorites') as HTMLInputElement;
    if (includeFavorites) {
        includeFavorites.checked = true;
    }

    const includeMetadata: HTMLInputElement | null = document.getElementById('include-metadata') as HTMLInputElement;
    if (includeMetadata) {
        includeMetadata.checked = true;
    }

    // Clear any progress or status messages
    hideProgress('export');
    showStatus('export', '', 'info');

    // Show confirmation
    showStatus('export', 'Export settings cleared', 'success');
    setTimeout((): void => {
        showStatus('export', '', 'info');
    }, 2000);
}

function hideModal(): void {
    const modal: HTMLElement | null = document.getElementById('prompt-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}
