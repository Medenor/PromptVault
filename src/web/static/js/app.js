// PromptVault Web App JavaScript

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
        // Initialize the app after i18next is ready
        if (document.readyState === 'loading') {
            // DOM is still loading
            document.addEventListener('DOMContentLoaded', function() {
                updateStaticTranslations();
                initializeApp();
            });
        } else {
            // DOM is already loaded
            updateStaticTranslations();
            initializeApp();
        }
    });

function updateStaticTranslations() {
    // Update elements with data-i18n attributes
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (key) {
            element.textContent = i18next.t(key);
        }
    });

    // Update placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
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

let promptCache = {};
let lastSelectedPromptId = null; // Track the last selected prompt for keyboard shortcuts

function initializeApp() {
    // Event listeners
    setupEventListeners();

    // Load initial data
    loadPrompts();
    loadCategories();
    loadTags();
}

function setupEventListeners() {
    // Language selector
    document.getElementById('language-selector').addEventListener('change', handleLanguageChange);

    // New prompt button
    document.getElementById('new-prompt-btn').addEventListener('click', showNewPromptForm);

    // Import/Export button (navigates to import/export page)
    document.getElementById('import-export-btn').addEventListener('click', function() {
        window.location.href = '/import-export';
    });

    // Form handling
    document.getElementById('prompt-form').addEventListener('submit', handlePromptSubmit);
    document.getElementById('cancel-btn').addEventListener('click', hidePromptEditor);

    // Category and tag filtering
    document.getElementById('categories-list').addEventListener('click', handleCategoryFilter);
    document.getElementById('tags-list').addEventListener('click', handleTagFilter);
    document.getElementById('favorites-filter').addEventListener('change', handleFavoritesFilter);

    // Modal close
    document.querySelector('.close').addEventListener('click', hideModal);
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('prompt-modal');
        if (event.target === modal) {
            hideModal();
        }
    });

    // Version history modal close
    const closeVersionHistoryBtn = document.getElementById('close-version-history-btn');
    if (closeVersionHistoryBtn) {
        closeVersionHistoryBtn.addEventListener('click', hideVersionHistoryModal);
    }

    // Diff modal close
    const closeDiffBtn = document.getElementById('close-diff-btn');
    if (closeDiffBtn) {
        closeDiffBtn.addEventListener('click', hideDiffModal);
    }

    // Revert confirmation modal close
    const cancelRevertBtn = document.getElementById('cancel-revert-btn');
    if (cancelRevertBtn) {
        cancelRevertBtn.addEventListener('click', hideRevertConfirmationModal);
    }

    // Compare versions button
    const compareVersionsBtn = document.getElementById('compare-versions-btn');
    if (compareVersionsBtn) {
        compareVersionsBtn.addEventListener('click', showDiffModal);
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);

    // Add tooltips
    addTooltips();
}

async function loadPrompts() {
    try {
        console.log('Loading prompts...');
        const response = await fetch('/api/prompts');
        const data = await response.json();
        console.log('Loaded prompts data:', data);
        console.log('Number of prompts:', Object.keys(data.prompts || {}).length);
        renderPrompts(data.prompts);
    } catch (error) {
        console.error('Error loading prompts:', error);
    }
}

async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();
        renderCategories(data.categories);
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

async function loadTags() {
    try {
        const response = await fetch('/api/tags');
        const data = await response.json();
        renderTags(data.tags);
    } catch (error) {
        console.error('Error loading tags:', error);
    }
}

function renderPrompts(prompts) {
    promptCache = { ...prompts };
    const container = document.getElementById('prompts-list');
    container.innerHTML = '';

    for (const [id, prompt] of Object.entries(prompts)) {
        const promptElement = createPromptElement(id, prompt);
        container.appendChild(promptElement);
    }
}

function createPromptElement(id, prompt) {
    const div = document.createElement('div');
    div.className = 'prompt-item';
    div.dataset.id = id;

    div.innerHTML = `
        <div class="prompt-header">
            <h4>${prompt.title}</h4>
            <div class="prompt-actions">
                <button class="favorite-btn" data-id="${id}">
                    ${prompt.favorite ? '★' : '☆'}
                </button>
                <button class="history-btn" data-id="${id}" data-i18n="version.history">History</button>
                <button class="copy-btn" data-id="${id}" data-i18n="actions.copy">Copy</button>
                <button class="edit-btn" data-id="${id}" data-i18n="actions.edit">Edit</button>
                <button class="delete-btn" data-id="${id}" data-i18n="actions.delete">Delete</button>
            </div>
        </div>
        <div class="prompt-meta">
            <span class="category">${prompt.category || i18next.t('categories.noCategory')}</span>
            ${prompt.tags ? `<span class="tags">${prompt.tags.join(', ')}</span>` : ''}
        </div>
        <div class="prompt-content">${truncateText(prompt.prompt, 100)}</div>
    `;

    // Update translations for dynamically created elements
    div.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (key) {
            element.textContent = i18next.t(key);
        }
    });

    // Add event listeners and tooltips
    const copyBtn = div.querySelector('.copy-btn');
    copyBtn.addEventListener('click', () => {
        lastSelectedPromptId = id;
        copyPrompt(id);
    });
    copyBtn.title = i18next.t('actions.copy');
    
    const editBtn = div.querySelector('.edit-btn');
    editBtn.addEventListener('click', () => {
        lastSelectedPromptId = id;
        editPrompt(id);
    });
    editBtn.title = i18next.t('actions.edit');
    
    const deleteBtn = div.querySelector('.delete-btn');
    deleteBtn.addEventListener('click', () => {
        lastSelectedPromptId = id;
        deletePrompt(id);
    });
    deleteBtn.title = i18next.t('actions.delete');
    
    const favoriteBtn = div.querySelector('.favorite-btn');
    favoriteBtn.addEventListener('click', () => {
        lastSelectedPromptId = id;
        toggleFavorite(id);
    });
    favoriteBtn.title = i18next.t('actions.favorite');
    
    const historyBtn = div.querySelector('.history-btn');
    historyBtn.addEventListener('click', () => {
        lastSelectedPromptId = id;
        showVersionHistoryModal(id);
    });
    historyBtn.title = i18next.t('version.history');
    
    // Track prompt selection on click
    div.addEventListener('click', () => {
        lastSelectedPromptId = id;
    });

    return div;
}

function renderCategories(categories) {
    const list = document.getElementById('categories-list');
    // Clear existing categories except "All Prompts"
    const allPromptsItem = list.querySelector('[data-category="all"]');
    list.innerHTML = '';
    list.appendChild(allPromptsItem);

    categories.forEach(category => {
        const li = document.createElement('li');
        li.dataset.category = category;
        li.textContent = category;
        list.appendChild(li);
    });
}

function renderTags(tags) {
    const list = document.getElementById('tags-list');
    // Clear existing tags except "All Tags"
    const allTagsItem = list.querySelector('[data-tag="all"]');
    list.innerHTML = '';
    list.appendChild(allTagsItem);

    tags.forEach(tag => {
        const li = document.createElement('li');
        li.dataset.tag = tag;
        li.textContent = tag;
        list.appendChild(li);
    });
}

function showNewPromptForm() {
    document.getElementById('prompt-editor').style.display = 'block';
    document.getElementById('prompt-form').reset();
    document.getElementById('prompts-list').style.display = 'none';
}

function hidePromptEditor() {
    document.getElementById('prompt-editor').style.display = 'none';
    document.getElementById('prompts-list').style.display = 'flex';
}

async function handlePromptSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const isEditMode = form.dataset.mode === 'edit';
    const promptId = form.dataset.id;

    // Debug logging
    console.log('Form submission:', { isEditMode, promptId });
    for (let [key, value] of formData.entries()) {
        console.log(`${key}: ${value}`);
    }

    try {
        let url = '/api/prompts';
        let method = 'POST';

        if (isEditMode && promptId) {
            url = `/api/prompts/${promptId}`;
            method = 'PUT';
        }

        console.log(`Sending ${method} request to ${url}`);

        const response = await fetch(url, {
            method: method,
            body: formData
        });

        console.log('Response status:', response.status);
        const responseData = await response.json();
        console.log('Response data:', responseData);

        if (response.ok) {
            hidePromptEditor();
            // Clear version cache for this prompt since a new version was created
            clearVersionCache(promptId);
            loadPrompts(); // Refresh the list
            // Reset form mode
            delete form.dataset.mode;
            delete form.dataset.id;
        } else {
            alert(`${i18next.t('messages.error')}: ${responseData.error || i18next.t('messages.unknownError')}`);
        }
    } catch (error) {
        console.error('Error saving prompt:', error);
        alert(i18next.t('messages.error'));
    }
}

function copyPrompt(id) {
    const cachedPrompt = promptCache[id];

    if (cachedPrompt && typeof cachedPrompt.prompt === 'string') {
        copyTextToClipboard(cachedPrompt.prompt, id);
        return;
    }

    fetch(`/api/prompts/${id}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to load prompt ${id}: ${response.status}`);
            }
            return response.json();
        })
        .then(prompt => {
            promptCache[id] = prompt;
            copyTextToClipboard(prompt.prompt, id);
        })
        .catch(error => {
            console.error('Error copying prompt:', error);
            showCopyFeedback(id, 'messages.copyFailed');
        });
}

function copyTextToClipboard(textToCopy, id) {
    if (typeof textToCopy !== 'string') {
        showCopyFeedback(id, 'messages.copyFailed');
        return;
    }

    // Try modern Clipboard API first
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        navigator.clipboard.writeText(textToCopy)
            .then(() => {
                showCopyFeedback(id, 'messages.copied');
            })
            .catch(error => {
                console.warn('Clipboard API write failed, falling back to execCommand.', error);
                fallbackCopyTextToClipboard(textToCopy, id);
            });
        return;
    }

    // Fallback for older browsers or non-HTTPS
    fallbackCopyTextToClipboard(textToCopy, id);
}

function fallbackCopyTextToClipboard(text, id) {
    // Create a temporary textarea element
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.setAttribute('readonly', '');
    textArea.style.position = 'fixed';
    textArea.style.top = '0';
    textArea.style.left = '0';
    textArea.style.width = '1px';
    textArea.style.height = '1px';
    textArea.style.opacity = '0';
    textArea.style.pointerEvents = 'none';
    document.body.appendChild(textArea);

    try {
        textArea.focus();
        textArea.select();
        textArea.setSelectionRange(0, textArea.value.length);

        const successful = document.execCommand('copy');
        if (successful) {
            showCopyFeedback(id, 'messages.copied');
        } else {
            showCopyFeedback(id, 'messages.copyFailed');
        }
    } catch (error) {
        console.error('Fallback copy failed:', error);
        showCopyFeedback(id, 'messages.copyFailed');
    } finally {
        document.body.removeChild(textArea);
    }
}

function showCopyFeedback(id, message) {
    const btn = document.querySelector(`.copy-btn[data-id="${id}"]`);
    if (btn) {
        const originalText = btn.textContent;
        // Use translated message if it's a key, otherwise use as-is
        const translatedMessage = i18next.t(message) !== message ? i18next.t(message) : message;
        btn.textContent = translatedMessage;
        setTimeout(() => btn.textContent = originalText, 2000);
    }
}

async function editPrompt(id) {
    try {
        const response = await fetch(`/api/prompts/${id}`);
        const prompt = await response.json();

        promptCache[id] = prompt;

        console.log('Editing prompt:', prompt); // Debug log

        // Show editor without resetting form
        document.getElementById('prompt-editor').style.display = 'block';
        document.getElementById('prompts-list').style.display = 'none';

        // Populate form
        document.getElementById('prompt-title').value = prompt.title || '';
        document.getElementById('prompt-content').value = prompt.prompt || '';
        document.getElementById('prompt-category').value = prompt.category || '';
        document.getElementById('prompt-tags').value = prompt.tags ? prompt.tags.join(', ') : '';
        document.getElementById('commit-message').value = ''; // Clear commit message for new edit

        // Change form to update mode
        const form = document.getElementById('prompt-form');
        form.dataset.mode = 'edit';
        form.dataset.id = id;

    } catch (error) {
        console.error('Error loading prompt for edit:', error);
    }
}

async function deletePrompt(id) {
    if (!confirm(i18next.t('messages.confirmDelete'))) {
        return;
    }

    try {
        const response = await fetch(`/api/prompts/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadPrompts(); // Refresh the list
        } else {
            alert(i18next.t('messages.error'));
        }
    } catch (error) {
        console.error('Error deleting prompt:', error);
        alert(i18next.t('messages.error'));
    }
}

async function toggleFavorite(id) {
    try {
        // Optimistic update - immediately toggle the UI
        const favoriteBtn = document.querySelector(`.favorite-btn[data-id="${id}"]`);
        if (favoriteBtn) {
            const currentIcon = favoriteBtn.textContent;
            const newIcon = currentIcon === '★' ? '☆' : '★';
            favoriteBtn.textContent = newIcon;

            // Also update the cached prompt data
            if (promptCache[id]) {
                promptCache[id].favorite = !promptCache[id].favorite;
            }
        }

        // Make API call to persist the change
        const response = await fetch(`/api/prompts/${id}/favorite`, {
            method: 'PUT'
        });

        if (!response.ok) {
            // Revert optimistic update on error
            const favoriteBtn = document.querySelector(`.favorite-btn[data-id="${id}"]`);
            if (favoriteBtn) {
                const currentIcon = favoriteBtn.textContent;
                const revertedIcon = currentIcon === '★' ? '☆' : '★';
                favoriteBtn.textContent = revertedIcon;

                // Also revert the cached prompt data
                if (promptCache[id]) {
                    promptCache[id].favorite = !promptCache[id].favorite;
                }
            }

            const errorData = await response.json();
            alert(`${i18next.t('messages.error')}: ${errorData.error || i18next.t('messages.unknownError')}`);
        } else {
            const result = await response.json();
            console.log(`Favorite toggled for prompt ${id}: ${result.favorite}`);
        }
    } catch (error) {
        // Revert optimistic update on network error
        const favoriteBtn = document.querySelector(`.favorite-btn[data-id="${id}"]`);
        if (favoriteBtn) {
            const currentIcon = favoriteBtn.textContent;
            const revertedIcon = currentIcon === '★' ? '☆' : '★';
            favoriteBtn.textContent = revertedIcon;

            // Also revert the cached prompt data
            if (promptCache[id]) {
                promptCache[id].favorite = !promptCache[id].favorite;
            }
        }

        console.error('Error toggling favorite:', error);
        alert(i18next.t('messages.error'));
    }
}

function handleCategoryFilter(event) {
    if (event.target.tagName === 'LI') {
        // Update active state
        document.querySelectorAll('#categories-list li').forEach(li => li.classList.remove('active'));
        event.target.classList.add('active');

        // Filter prompts (simplified - would need backend filtering)
        const category = event.target.dataset.category;
        filterPrompts({ category });
    }
}

function handleTagFilter(event) {
    if (event.target.tagName === 'LI') {
        // Update active state
        document.querySelectorAll('#tags-list li').forEach(li => li.classList.remove('active'));
        event.target.classList.add('active');

        // Filter prompts
        const tag = event.target.dataset.tag;
        filterPrompts({ tag });
    }
}

function handleFavoritesFilter(event) {
    filterPrompts({ favorites: event.target.checked });
}

function filterPrompts(filters) {
    // This is a simplified client-side filter
    // In a real app, you'd want server-side filtering
    const promptItems = document.querySelectorAll('.prompt-item');

    promptItems.forEach(item => {
        let show = true;

        if (filters.category && filters.category !== 'all') {
            const category = item.querySelector('.category').textContent;
            if (category !== filters.category) {
                show = false;
            }
        }

        if (filters.tag && filters.tag !== 'all') {
            const tags = item.querySelector('.tags');
            if (!tags || !tags.textContent.includes(filters.tag)) {
                show = false;
            }
        }

        if (filters.favorites) {
            const favoriteBtn = item.querySelector('.favorite-btn');
            if (favoriteBtn.textContent !== '★') {
                show = false;
            }
        }

        item.style.display = show ? 'block' : 'none';
    });
}

function handleLanguageChange(event) {
    const selectedLanguage = event.target.value;
    i18next.changeLanguage(selectedLanguage, (err, t) => {
        if (err) {
            console.error('Error changing language:', err);
            return;
        }
        // Update all translations on the page
        updateStaticTranslations();
        // Update version history UI if modal is open
        updateVersionHistoryTranslations();
        // Re-render prompts to update dynamic content
        loadPrompts();
    });
}

function updateVersionHistoryTranslations() {
    // Update search placeholder
    const searchInput = document.getElementById('version-search');
    if (searchInput) {
        searchInput.placeholder = i18next.t('version.searchPlaceholder');
    }
    
    // Update version item buttons
    document.querySelectorAll('[data-i18n="version.select"]').forEach(element => {
        element.textContent = i18next.t('version.select');
    });
    
    document.querySelectorAll('[data-i18n="version.revert"]').forEach(element => {
        element.textContent = i18next.t('version.revert');
    });
}

function handleImport() {
    // Create file input
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,.csv,.md';
    input.onchange = async (event) => {
        const file = event.target.files[0];
        if (file) {
            // Handle file upload
            alert('Import functionality not yet implemented');
        }
    };
    input.click();
}

function handleExport() {
    // Simple export - in real app, would call backend
    alert('Export functionality not yet implemented');
}

function hideModal() {
    document.getElementById('prompt-modal').style.display = 'none';
}

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Version Control Functions
let currentVersionPromptId = null;
let selectedVersions = new Set();
let versionCache = {}; // Cache for version history
let diffCache = {}; // Cache for diff results
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

function showVersionHistoryModal(promptId) {
    currentVersionPromptId = promptId;
    selectedVersions.clear();
    document.getElementById('version-history-modal').style.display = 'block';
    // Update search placeholder with current language
    const searchInput = document.getElementById('version-search');
    if (searchInput) {
        searchInput.placeholder = i18next.t('version.searchPlaceholder');
    }
    loadVersionHistory(promptId);
}

function hideVersionHistoryModal() {
    document.getElementById('version-history-modal').style.display = 'none';
    currentVersionPromptId = null;
    selectedVersions.clear();
}

function hideDiffModal() {
    document.getElementById('diff-modal').style.display = 'none';
}

function hideRevertConfirmationModal() {
    document.getElementById('revert-confirmation-modal').style.display = 'none';
}

async function loadVersionHistory(promptId) {
    try {
        const versionList = document.getElementById('version-list');
        versionList.innerHTML = '<div class="loading">' + i18next.t('messages.loading') + '</div>';

        // Check cache first
        const cacheKey = `versions_${promptId}`;
        if (versionCache[cacheKey] && Date.now() - versionCache[cacheKey].timestamp < CACHE_DURATION) {
            const cachedData = versionCache[cacheKey].data;
            renderVersionHistory(cachedData.versions || []);
            updateCompareButton();
            return;
        }

        const response = await fetch(`/api/prompts/${promptId}/versions`);
        if (!response.ok) {
            throw new Error('Failed to load version history');
        }

        const data = await response.json();
        
        // Cache the result
        versionCache[cacheKey] = {
            data: data,
            timestamp: Date.now()
        };
        
        // Store all versions for diff operations
        allVersions = data.versions || [];
        
        renderVersionHistory(data.versions || []);
        updateCompareButton();
    } catch (error) {
        console.error('Error loading version history:', error);
        document.getElementById('version-list').innerHTML = '<div class="loading">Error loading versions</div>';
    }
}

function renderVersionHistory(versions) {
    const versionList = document.getElementById('version-list');
    
    if (versions.length === 0) {
        versionList.innerHTML = '<div class="loading">' + i18next.t('version.noVersions') + '</div>';
        return;
    }

    versionList.innerHTML = '';
    versions.forEach((version, index) => {
        const versionItem = createVersionItem(version, index, versions.length);
        versionList.appendChild(versionItem);
    });
}

function createVersionItem(version, index, totalVersions) {
    const div = document.createElement('div');
    div.className = 'version-item';
    div.dataset.versionId = version.version_id;

    // Format timestamp
    const timestamp = new Date(version.timestamp).toLocaleString();
    const isLatest = index === 0;

    div.innerHTML = `
        <div class="version-item-header">
            <span class="version-item-id">#${totalVersions - index} ${version.version_id.substring(0, 8)}...</span>
            <span class="version-item-timestamp">${timestamp}</span>
        </div>
        <div class="version-item-author">${i18next.t('version.author')}: ${version.author}</div>
        <div class="version-item-message">${version.message}</div>
        <div class="version-item-actions">
            ${!isLatest ? `<button class="btn btn-danger" onclick="showRevertConfirmation('${version.version_id}')" data-i18n="version.revert">` + i18next.t('version.revert') + `</button>` : ''}
            <button class="btn btn-secondary" onclick="selectVersionForComparison('${version.version_id}')" data-i18n="version.select">` + i18next.t('version.select') + `</button>
        </div>
    `;

    div.addEventListener('click', function(e) {
        if (!e.target.closest('button')) {
            toggleVersionSelection(version.version_id, div);
        }
    });

    return div;
}

function toggleVersionSelection(versionId, element) {
    if (selectedVersions.has(versionId)) {
        selectedVersions.delete(versionId);
        element.classList.remove('selected');
    } else {
        selectedVersions.add(versionId);
        element.classList.add('selected');
    }
    updateCompareButton();
}

function selectVersionForComparison(versionId) {
    toggleVersionSelection(versionId, document.querySelector(`[data-version-id="${versionId}"]`));
}

function updateCompareButton() {
    const compareBtn = document.getElementById('compare-versions-btn');
    if (compareBtn) {
        if (selectedVersions.size === 2) {
            compareBtn.style.display = 'inline-block';
        } else {
            compareBtn.style.display = 'none';
        }
    }
}

function showRevertConfirmation(versionId) {
    document.getElementById('revert-confirmation-modal').style.display = 'block';
    document.getElementById('confirm-revert-btn').onclick = function() {
        performRevert(versionId);
    };
}

async function performRevert(versionId) {
    try {
        const commitMessage = document.getElementById('revert-commit-message').value || 'Revert to previous version';
        
        const formData = new FormData();
        formData.append('commit_message', commitMessage);

        const response = await fetch(`/api/prompts/${currentVersionPromptId}/versions/${versionId}/revert`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Failed to revert version');
        }

        hideRevertConfirmationModal();
        showNotification(i18next.t('version.revertSuccess'), 'success');
        // Clear version cache since a new version was created
        clearVersionCache(currentVersionPromptId);
        loadVersionHistory(currentVersionPromptId);
        loadPrompts(); // Refresh main list
    } catch (error) {
        console.error('Error reverting version:', error);
        showNotification(i18next.t('version.revertError'), 'error');
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem;
        background-color: ${type === 'success' ? '#27ae60' : type === 'error' ? '#e74c3c' : '#3498db'};
        color: white;
        border-radius: 4px;
        z-index: 2000;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    `;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

// Diff Visualization Functions
let allVersions = [];

async function showDiffModal() {
    if (selectedVersions.size !== 2) {
        showNotification('Please select exactly 2 versions to compare', 'error');
        return;
    }

    document.getElementById('diff-modal').style.display = 'block';
    const versionIds = Array.from(selectedVersions);
    
    // Populate version selectors
    populateDiffSelectors(versionIds);
    
    // Load and display diff
    await loadAndDisplayDiff(versionIds[0], versionIds[1]);
}

function populateDiffSelectors(selectedIds) {
    const v1Selector = document.getElementById('diff-v1-selector');
    const v2Selector = document.getElementById('diff-v2-selector');
    
    v1Selector.innerHTML = '';
    v2Selector.innerHTML = '';
    
    allVersions.forEach((version, index) => {
        const option1 = document.createElement('option');
        option1.value = version.version_id;
        option1.textContent = `#${allVersions.length - index} - ${version.message}`;
        if (version.version_id === selectedIds[0]) option1.selected = true;
        v1Selector.appendChild(option1);
        
        const option2 = document.createElement('option');
        option2.value = version.version_id;
        option2.textContent = `#${allVersions.length - index} - ${version.message}`;
        if (version.version_id === selectedIds[1]) option2.selected = true;
        v2Selector.appendChild(option2);
    });
    
    // Add change listener
    v1Selector.addEventListener('change', () => updateDiff());
    v2Selector.addEventListener('change', () => updateDiff());
}

async function updateDiff() {
    const v1 = document.getElementById('diff-v1-selector').value;
    const v2 = document.getElementById('diff-v2-selector').value;
    
    if (v1 === v2) {
        document.getElementById('diff-view').innerHTML = '<div class="loading">Select different versions to compare</div>';
        return;
    }
    
    await loadAndDisplayDiff(v1, v2);
}

async function loadAndDisplayDiff(v1Id, v2Id) {
    try {
        document.getElementById('diff-view').innerHTML = '<div class="loading">' + i18next.t('messages.loading') + '</div>';
        
        // Check cache first
        const cacheKey = `diff_${currentVersionPromptId}_${v1Id}_${v2Id}`;
        if (diffCache[cacheKey] && Date.now() - diffCache[cacheKey].timestamp < CACHE_DURATION) {
            displayDiff(diffCache[cacheKey].data);
            return;
        }
        
        const response = await fetch(`/api/prompts/${currentVersionPromptId}/versions/compare?v1=${v1Id}&v2=${v2Id}`);
        if (!response.ok) {
            throw new Error('Failed to load diff');
        }
        
        const diff = await response.json();
        
        // Cache the result
        diffCache[cacheKey] = {
            data: diff,
            timestamp: Date.now()
        };
        
        displayDiff(diff);
    } catch (error) {
        console.error('Error loading diff:', error);
        document.getElementById('diff-view').innerHTML = '<div class="loading">Error loading diff</div>';
    }
}

function displayDiff(diff) {
    const diffView = document.getElementById('diff-view');
    diffView.innerHTML = '';
    
    if (!diff.changes || Object.keys(diff.changes).length === 0) {
        diffView.innerHTML = '<div class="loading">No changes between these versions</div>';
        return;
    }
    
    const section = document.createElement('div');
    section.className = 'diff-section';
    
    Object.entries(diff.changes).forEach(([field, change]) => {
        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'diff-field';
        
        const fieldName = document.createElement('div');
        fieldName.className = 'diff-field-name';
        fieldName.textContent = field.charAt(0).toUpperCase() + field.slice(1);
        fieldDiv.appendChild(fieldName);
        
        // Old value
        if (change.old !== null && change.old !== undefined) {
            const oldDiv = document.createElement('div');
            oldDiv.className = 'diff-old';
            oldDiv.innerHTML = `<strong>Old:</strong> ${escapeHtml(formatValue(change.old))}`;
            fieldDiv.appendChild(oldDiv);
        }
        
        // New value
        if (change.new !== null && change.new !== undefined) {
            const newDiv = document.createElement('div');
            newDiv.className = 'diff-new';
            newDiv.innerHTML = `<strong>New:</strong> ${escapeHtml(formatValue(change.new))}`;
            fieldDiv.appendChild(newDiv);
        }
        
        section.appendChild(fieldDiv);
    });
    
    diffView.appendChild(section);
}

function formatValue(value) {
    if (Array.isArray(value)) {
        return value.join(', ');
    }
    if (typeof value === 'object' && value !== null) {
        return JSON.stringify(value);
    }
    return String(value);
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Cache management functions
function clearVersionCache(promptId) {
    const cacheKey = `versions_${promptId}`;
    delete versionCache[cacheKey];
}

function clearDiffCache() {
    diffCache = {};
}

function clearAllCache() {
    versionCache = {};
    diffCache = {};
}

// Optimize diff calculation
function optimizeDiffCalculation(changes) {
    // Remove unchanged fields to reduce payload
    const optimized = {};
    Object.entries(changes).forEach(([field, change]) => {
        if (change.old !== change.new) {
            optimized[field] = change;
        }
    });
    return optimized;
}

// Keyboard Shortcuts (Phase 6)
function handleKeyboardShortcuts(event) {
    // Ctrl/Cmd + H: Open version history for last selected prompt
    if ((event.ctrlKey || event.metaKey) && event.key === 'h') {
        event.preventDefault();
        if (lastSelectedPromptId) {
            showVersionHistoryModal(lastSelectedPromptId);
        } else {
            showNotification('Please select a prompt first', 'info');
        }
    }

    // Ctrl/Cmd + N: New prompt
    if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
        event.preventDefault();
        showNewPromptForm();
    }

    // Escape: Close modals
    if (event.key === 'Escape') {
        hideVersionHistoryModal();
        hideDiffModal();
        hideRevertConfirmationModal();
        hidePromptEditor();
    }
}

// Loading States (Phase 6)
function setLoadingState(element, isLoading) {
    if (isLoading) {
        element.classList.add('loading-state');
        element.disabled = true;
        element.style.opacity = '0.6';
    } else {
        element.classList.remove('loading-state');
        element.disabled = false;
        element.style.opacity = '1';
    }
}

function showLoadingSpinner(container) {
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    spinner.innerHTML = '<div class="spinner"></div>';
    container.appendChild(spinner);
    return spinner;
}

function removeLoadingSpinner(spinner) {
    if (spinner && spinner.parentNode) {
        spinner.parentNode.removeChild(spinner);
    }
}

// Tooltips (Phase 6 & 8)
function addTooltips() {
    const tooltips = {
        '.history-btn': i18next.t('version.history') + ' - ' + i18next.t('version.searchPlaceholder'),
        '.copy-btn': i18next.t('actions.copy'),
        '.edit-btn': i18next.t('actions.edit'),
        '.delete-btn': i18next.t('actions.delete'),
        '.favorite-btn': 'Toggle favorite'
    };

    Object.entries(tooltips).forEach(([selector, title]) => {
        document.querySelectorAll(selector).forEach(element => {
            element.title = title;
            element.setAttribute('data-tooltip', title);
        });
    });
}

// Lazy Loading for Version List (Phase 9)
let versionListObserver = null;
const VERSIONS_PER_PAGE = 10;
let currentVersionPage = 0;

function initializeLazyLoading() {
    if ('IntersectionObserver' in window) {
        versionListObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    loadMoreVersions();
                }
            });
        }, { threshold: 0.1 });
    }
}

function loadMoreVersions() {
    const versionList = document.getElementById('version-list');
    if (!versionList) return;

    const items = versionList.querySelectorAll('.version-item');
    const totalItems = allVersions.length;
    const itemsToShow = (currentVersionPage + 1) * VERSIONS_PER_PAGE;

    if (items.length < totalItems && items.length < itemsToShow) {
        currentVersionPage++;
        const startIdx = currentVersionPage * VERSIONS_PER_PAGE;
        const endIdx = Math.min(startIdx + VERSIONS_PER_PAGE, totalItems);

        for (let i = startIdx; i < endIdx; i++) {
            const version = allVersions[i];
            const versionItem = createVersionItem(version, i, totalItems);
            versionList.appendChild(versionItem);
        }

        // Observe the last item for lazy loading
        const lastItem = versionList.lastChild;
        if (versionListObserver && lastItem) {
            versionListObserver.observe(lastItem);
        }
    }
}

// API Response Time Profiling (Phase 9)
const apiMetrics = {};

function recordApiCall(endpoint, duration) {
    if (!apiMetrics[endpoint]) {
        apiMetrics[endpoint] = {
            calls: 0,
            totalTime: 0,
            avgTime: 0,
            minTime: Infinity,
            maxTime: 0
        };
    }

    const metric = apiMetrics[endpoint];
    metric.calls++;
    metric.totalTime += duration;
    metric.avgTime = metric.totalTime / metric.calls;
    metric.minTime = Math.min(metric.minTime, duration);
    metric.maxTime = Math.max(metric.maxTime, duration);
}

function getApiMetrics() {
    return apiMetrics;
}

// Wrap fetch to track API performance
const originalFetch = window.fetch;
window.fetch = function(...args) {
    const startTime = performance.now();
    return originalFetch.apply(this, args).then(response => {
        const duration = performance.now() - startTime;
        const endpoint = args[0];
        recordApiCall(endpoint, duration);
        return response;
    });
};

// Initialize lazy loading on app start
initializeLazyLoading();
