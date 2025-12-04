/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */
 
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
            // Handle special syntax like [placeholder]key or [value]key
            if (key.includes('[') && key.includes(']')) {
                const match = key.match(/\[(\w+)\](.+)/);
                if (match) {
                    const attribute = match[1]; // e.g., 'placeholder'
                    const translationKey = match[2]; // e.g., 'nav.searchPlaceholder'
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

    // Update placeholders using legacy data-i18n-placeholder attribute
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
let selectedPromptIds = new Set(); // Track selected prompts for bulk operations

const HIDDEN_CLASS = 'is-hidden';
const ERROR_VISIBLE_CLASS = 'validation-error-visible';
const APP_COMPONENT = 'app';

function reportAppIssue(action, error, metadata = {}, severity = 'error') {
    const logger = window.FrontendLogger;
    if (logger && typeof logger.reportError === 'function') {
        logger.reportError(APP_COMPONENT, action, error, metadata, severity);
    }
    const message = `[PromptVault][app] ${action}`;
    if (severity === 'warning') {
        console.warn(message, error, metadata);
    } else {
        console.error(message, error, metadata);
    }
}

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

function clearPromptFormErrors() {
    const errorFields = [
        'prompt-title-error',
        'prompt-content-error',
        'prompt-tags-error',
        'commit-message-error'
    ];
    errorFields.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = '';
            delete el.dataset.errorKey;
            el.classList.remove(ERROR_VISIBLE_CLASS);
        }
    });
    const inputs = ['prompt-title', 'prompt-content', 'prompt-tags', 'commit-message'];
    inputs.forEach(id => {
        const field = document.getElementById(id);
        if (field) {
            field.classList.remove('field-error');
            field.removeAttribute('aria-invalid');
        }
    });
    const banner = document.getElementById('validation-error-banner');
    if (banner) {
        banner.style.display = 'none';
    }
}

function showPromptFieldError(fieldId, errorId, messageKey) {
    const errorEl = document.getElementById(errorId);
    const field = document.getElementById(fieldId);
    const message = i18next.t(messageKey);
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.dataset.errorKey = messageKey;
        errorEl.classList.add(ERROR_VISIBLE_CLASS);
    }
    if (field) {
        field.classList.add('field-error');
        field.setAttribute('aria-invalid', 'true');
        field.focus();
    }
}

function toggleElement(element, shouldShow) {
    if (element) {
        element.classList.toggle(HIDDEN_CLASS, !shouldShow);
    }
}

function initializeApp() {
    // Event listeners
    setupEventListeners();
    initializeBulkActions();

    // Load initial data
    loadPrompts();
    loadCategories();
    loadTags();
}

// Global search state
let searchState = {
    searchTerm: '',
    category: 'all',
    tag: 'all',
    favorites: false,
    caseSensitive: false,
    isLoading: false
};

function setupEventListeners() {
    // Language selector
    document.getElementById('language-selector').addEventListener('change', handleLanguageChange);

    // New prompt button
    document.getElementById('new-prompt-btn').addEventListener('click', showNewPromptForm);

    // Import/Export button (navigates to import/export page)
    document.getElementById('import-export-btn').addEventListener('click', function() {
        window.location.href = '/import-export';
    });

    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }

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

    // Search functionality
    setupSearchEventListeners();

    // Tag autocomplete
    setupTagAutocomplete();
}

async function loadPrompts() {
    try {
        const response = await fetch('/api/prompts');
        const data = await response.json();

        // Hide search results info when loading all prompts initially
        const searchResultsInfo = document.getElementById('search-results-info');
        if (searchResultsInfo) {
            hideElement(searchResultsInfo);
        }

        renderPrompts(data.prompts);
    } catch (error) {
        reportAppIssue('loadPrompts', error);
    }
}

async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();
        renderCategories(data.categories);
    } catch (error) {
        reportAppIssue('loadCategories', error);
    }
}

async function loadTags() {
    try {
        const response = await fetch('/api/tags');
        const data = await response.json();
        renderTags(data.tags);
    } catch (error) {
        reportAppIssue('loadTags', error);
    }
}

function renderPrompts(prompts) {
    promptCache = { ...prompts };
    const container = document.getElementById('prompts-list');
    const searchResultsInfo = document.getElementById('search-results-info');
    container.innerHTML = '';

    // Handle case when there are no prompts at all
    if (Object.keys(prompts).length === 0) {
        container.innerHTML = `<div class="no-results-message">${i18next.t('search.emptyState')}</div>`;
        if (searchResultsInfo) {
            hideElement(searchResultsInfo);
        }
        return;
    }

    for (const [id, prompt] of Object.entries(prompts)) {
        const promptElement = createPromptElement(id, prompt);
        container.appendChild(promptElement);
    }
}

function createPromptElement(id, prompt) {
    const div = document.createElement('div');
    div.className = 'prompt-item';
    div.dataset.id = id;

    // Add selected class if prompt is in selection
    if (selectedPromptIds.has(parseInt(id))) {
        div.classList.add('selected');
    }

    // Create checkbox for bulk selection
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'prompt-checkbox';
    checkbox.dataset.promptId = id;
    checkbox.checked = selectedPromptIds.has(parseInt(id));
    checkbox.addEventListener('change', (e) => {
        handleCheckboxChange(parseInt(id), e.target.checked);
        e.stopPropagation(); // Prevent triggering the div click event
    });

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

    // Insert checkbox before the favorite button in prompt-actions
    const promptActions = div.querySelector('.prompt-actions');
    const favBtn = promptActions.querySelector('.favorite-btn');
    promptActions.insertBefore(checkbox, favBtn);

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
        // Handle both old format (string) and new format (object with name and count)
        if (typeof tag === 'string') {
            li.dataset.tag = tag;
            li.textContent = tag;
        } else {
            li.dataset.tag = tag.name;
            li.textContent = `${tag.name} (${tag.count})`;
        }
        list.appendChild(li);
    });
}

function showNewPromptForm() {
    const promptEditor = document.getElementById('prompt-editor');
    const promptsList = document.getElementById('prompts-list');

    showElement(promptEditor);
    document.getElementById('prompt-form').reset();
    hideElement(promptsList);
}

function hidePromptEditor() {
    const promptEditor = document.getElementById('prompt-editor');
    const promptsList = document.getElementById('prompts-list');

    hideElement(promptEditor);
    showElement(promptsList);
}

async function handlePromptSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const isEditMode = form.dataset.mode === 'edit';
    const promptId = form.dataset.id;

    clearPromptFormErrors();

    // Client-side required checks to avoid native browser messages
    const title = formData.get('title') ? formData.get('title').trim() : '';
    const promptContent = formData.get('prompt') ? formData.get('prompt').trim() : '';
    let hasError = false;

    if (!title) {
        showPromptFieldError('prompt-title', 'prompt-title-error', 'validation.titleRequired');
        hasError = true;
    }

    if (!promptContent) {
        showPromptFieldError('prompt-content', 'prompt-content-error', 'validation.contentRequired');
        hasError = true;
    }

    if (hasError) {
        return;
    }

    try {
        let url = '/api/prompts';
        let method = 'POST';

        if (isEditMode && promptId) {
            url = `/api/prompts/${promptId}`;
            method = 'PUT';
        }

        const response = await fetch(url, {
            method: method,
            body: formData
        });

        const responseData = await response.json();

        if (response.ok) {
            hidePromptEditor();
            // Clear version cache for this prompt since a new version was created
            clearVersionCache(promptId);
            loadPrompts(); // Refresh the list
            loadAvailableTags(); // Refresh tag counts for autocomplete
            loadTags(); // Refresh sidebar tag list
            // Reset form mode
            delete form.dataset.mode;
            delete form.dataset.id;
        } else {
            alert(`${i18next.t('messages.error')}: ${responseData.error || i18next.t('messages.unknownError')}`);
        }
    } catch (error) {
        reportAppIssue('savePrompt', error, {
            mode: isEditMode ? 'edit' : 'create',
            promptId: promptId || null
        });
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
            reportAppIssue('copyPrompt', error, { promptId: id });
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
                reportAppIssue('clipboardWrite', error, { strategy: 'navigator.clipboard' }, 'warning');
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
    textArea.className = 'clipboard-helper';
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
        reportAppIssue('clipboardFallback', error, {}, 'warning');
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

        // Show editor without resetting form
        showElement(document.getElementById('prompt-editor'));
        hideElement(document.getElementById('prompts-list'));

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
        reportAppIssue('loadPromptForEdit', error, { promptId: id });
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
            loadAvailableTags(); // Refresh tag counts for autocomplete
            loadTags(); // Refresh sidebar tag list
        } else {
            alert(i18next.t('messages.error'));
        }
    } catch (error) {
        reportAppIssue('deletePrompt', error, { promptId: id });
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
            await response.json();
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

        reportAppIssue('toggleFavorite', error, { promptId: id });
        alert(i18next.t('messages.error'));
    }
}

function handleCategoryFilter(event) {
    if (event.target.tagName === 'LI') {
        // Update active state
        document.querySelectorAll('#categories-list li').forEach(li => li.classList.remove('active'));
        event.target.classList.add('active');

        // Update search state and trigger search
        searchState.category = event.target.dataset.category;
        performSearch();
    }
}

function handleTagFilter(event) {
    if (event.target.tagName === 'LI') {
        // Update active state
        document.querySelectorAll('#tags-list li').forEach(li => li.classList.remove('active'));
        event.target.classList.add('active');

        // Update search state and trigger search
        searchState.tag = event.target.dataset.tag;
        performSearch();
    }
}

function handleFavoritesFilter(event) {
    // Update search state and trigger search
    searchState.favorites = event.target.checked;
    performSearch();
}

function handleLanguageChange(event) {
    const selectedLanguage = event.target.value;
    i18next.changeLanguage(selectedLanguage, (err, t) => {
        if (err) {
            reportAppIssue('changeLanguage', err, { language: selectedLanguage });
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
    hideElement(document.getElementById('prompt-modal'));
}

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Search and Filter Functions
let searchTimeout = null;

function setupSearchEventListeners() {
    // Search input with debouncing
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearchInput);
        searchInput.addEventListener('keydown', function(event) {
            // Clear search on Escape
            if (event.key === 'Escape') {
                clearAllFilters();
            }
        });
    }

    // Clear search button
    const clearSearchBtn = document.getElementById('clear-search-btn');
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', function() {
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.value = '';
                searchState.searchTerm = '';
                toggleElement(clearSearchBtn, false);
                performSearch();
            }
        });
    }

    // Case sensitive toggle
    const caseSensitiveToggle = document.getElementById('case-sensitive-toggle');
    if (caseSensitiveToggle) {
        caseSensitiveToggle.addEventListener('change', function() {
            searchState.caseSensitive = this.checked;
            performSearch();
        });
    }

    // Clear all filters button
    const clearAllFiltersBtn = document.getElementById('clear-all-filters-btn');
    if (clearAllFiltersBtn) {
        clearAllFiltersBtn.addEventListener('click', clearAllFilters);
    }
}

function handleSearchInput(event) {
    const searchTerm = event.target.value;
    searchState.searchTerm = searchTerm;

    // Show/hide clear search button
    const clearSearchBtn = document.getElementById('clear-search-btn');
    if (clearSearchBtn) {
        toggleElement(clearSearchBtn, searchTerm.length > 0);
    }

    // Clear previous timeout
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }

    // Debounce search
    searchTimeout = setTimeout(() => {
        performSearch();
    }, 300);
}

async function performSearch() {
    if (searchState.isLoading) {
        return; // Don't start new search if one is already running
    }

    searchState.isLoading = true;

    try {
        // Show loading state
        const promptsList = document.getElementById('prompts-list');
        if (promptsList) {
            promptsList.style.opacity = '0.6';
            promptsList.style.pointerEvents = 'none';
        }

        // Build query parameters
        const params = new URLSearchParams();

        if (searchState.searchTerm) {
            params.append('search', searchState.searchTerm);
        }

        if (searchState.category && searchState.category !== 'all') {
            params.append('category', searchState.category);
        }

        if (searchState.tag && searchState.tag !== 'all') {
            params.append('tag', searchState.tag);
        }

        if (searchState.favorites) {
            params.append('favorites', 'true');
        }

        if (searchState.caseSensitive) {
            params.append('case_sensitive', 'true');
        }

        // Make API call
        const response = await fetch(`/api/prompts/search?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`Search failed: ${response.status}`);
        }

        const data = await response.json();

        // Update prompts list
        renderPrompts(data.prompts);

        // Update result count and handle empty results
        updateSearchResultsInfo(data.prompts);

    } catch (error) {
        reportAppIssue('searchPrompts', error, {
            filters: {
                searchTerm: searchState.searchTerm,
                category: searchState.category,
                tag: searchState.tag,
                favorites: searchState.favorites,
                caseSensitive: searchState.caseSensitive
            }
        });
        showNotification(i18next.t('search.error'), 'error');

        // Fallback to showing all prompts
        loadPrompts();
    } finally {
        searchState.isLoading = false;

        // Remove loading state
        const promptsList = document.getElementById('prompts-list');
        if (promptsList) {
            promptsList.style.opacity = '';
            promptsList.style.pointerEvents = '';
        }
    }
}

function updateSearchResultsInfo(prompts) {
    const resultCount = Object.keys(prompts || {}).length;
    const totalCount = Object.keys(promptCache).length;
    const searchResultsInfo = document.getElementById('search-results-info');
    const promptsList = document.getElementById('prompts-list');

    // Handle empty results
    if (resultCount === 0) {
        // Show "No results found" message
        if (searchResultsInfo) {
            searchResultsInfo.className = 'search-results-info no-results';
            searchResultsInfo.textContent = i18next.t('search.noResultsInfo');
            showElement(searchResultsInfo);
        }

        // Show empty state in prompts list
        if (promptsList) {
            promptsList.innerHTML = `<div class="no-results-message">${i18next.t('search.noResultsMessage')}</div>`;
        }

        // Hide clear filters button
        const clearAllFiltersBtn = document.getElementById('clear-all-filters-btn');
        if (clearAllFiltersBtn) {
            hideElement(clearAllFiltersBtn);
        }

        return;
    }

    // Show results count info
    if (searchResultsInfo) {
        searchResultsInfo.className = 'search-results-info';

        const hasAllResults = resultCount === totalCount;
        let infoText;

        if (hasAllResults) {
            infoText = i18next.t('search.resultsCount', { count: resultCount });
        } else {
            infoText = i18next.t('search.resultsCountWithTotal', { count: resultCount, total: totalCount });
        }

        // Add active filter indicators
        const activeFilters = [];
        if (searchState.searchTerm) {
            activeFilters.push(
                i18next.t('search.filter.search', {
                    term: searchState.searchTerm,
                    interpolation: { escapeValue: false }
                })
            );
        }
        if (searchState.category && searchState.category !== 'all') {
            activeFilters.push(
                i18next.t('search.filter.category', {
                    category: searchState.category,
                    interpolation: { escapeValue: false }
                })
            );
        }
        if (searchState.tag && searchState.tag !== 'all') {
            activeFilters.push(
                i18next.t('search.filter.tag', {
                    tag: searchState.tag,
                    interpolation: { escapeValue: false }
                })
            );
        }
        if (searchState.favorites) {
            activeFilters.push(i18next.t('search.filter.favorites'));
        }
        if (searchState.caseSensitive) {
            activeFilters.push(i18next.t('search.filter.caseSensitive'));
        }

        if (activeFilters.length > 0) {
            infoText += ` ${i18next.t('search.filteredBy', {
                filters: activeFilters.join(', '),
                interpolation: { escapeValue: false }
            })}`;
        }

        searchResultsInfo.textContent = infoText;
        showElement(searchResultsInfo);
    }

    // Update the clear filters button text to show result count
    const clearAllFiltersBtn = document.getElementById('clear-all-filters-btn');
    if (clearAllFiltersBtn) {
        if (resultCount !== totalCount || searchState.searchTerm || searchState.category !== 'all' ||
            searchState.tag !== 'all' || searchState.favorites || searchState.caseSensitive) {
            clearAllFiltersBtn.textContent = i18next.t('search.clearFiltersWithCount', { count: resultCount });
            showElement(clearAllFiltersBtn);
        } else {
            hideElement(clearAllFiltersBtn);
        }
    }
}

function clearAllFilters() {
    // Reset search state
    searchState = {
        searchTerm: '',
        category: 'all',
        tag: 'all',
        favorites: false,
        caseSensitive: false,
        isLoading: false
    };

    // Reset UI elements
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = '';
    }

    const clearSearchBtn = document.getElementById('clear-search-btn');
    if (clearSearchBtn) {
        hideElement(clearSearchBtn);
    }

    const caseSensitiveToggle = document.getElementById('case-sensitive-toggle');
    if (caseSensitiveToggle) {
        caseSensitiveToggle.checked = false;
    }

    const favoritesFilter = document.getElementById('favorites-filter');
    if (favoritesFilter) {
        favoritesFilter.checked = false;
    }

    // Reset active states in sidebar
    document.querySelectorAll('#categories-list li').forEach(li => li.classList.remove('active'));
    document.querySelector('[data-category="all"]').classList.add('active');

    document.querySelectorAll('#tags-list li').forEach(li => li.classList.remove('active'));
    document.querySelector('[data-tag="all"]').classList.add('active');

    // Hide clear filters button and search results info
    const clearAllFiltersBtn = document.getElementById('clear-all-filters-btn');
    if (clearAllFiltersBtn) {
        hideElement(clearAllFiltersBtn);
    }

    const searchResultsInfo = document.getElementById('search-results-info');
    if (searchResultsInfo) {
        hideElement(searchResultsInfo);
    }

    // Load all prompts
    loadPrompts();
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
    showElement(document.getElementById('version-history-modal'));
    // Update search placeholder with current language
    const searchInput = document.getElementById('version-search');
    if (searchInput) {
        searchInput.placeholder = i18next.t('version.searchPlaceholder');
    }
    loadVersionHistory(promptId);
}

function hideVersionHistoryModal() {
    hideElement(document.getElementById('version-history-modal'));
    currentVersionPromptId = null;
    selectedVersions.clear();
}

function hideDiffModal() {
    hideElement(document.getElementById('diff-modal'));
}

function hideRevertConfirmationModal() {
    hideElement(document.getElementById('revert-confirmation-modal'));
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
        reportAppIssue('loadVersionHistory', error, { promptId });
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

    // Format timestamp with fallback for invalid dates
    let timestamp;
    try {
        // Handle timestamps with microseconds by truncating to milliseconds
        const cleanTimestamp = version.timestamp.replace(/(\.\d{3})\d*/, '$1');
        const date = new Date(cleanTimestamp);
        if (isNaN(date.getTime())) {
            timestamp = 'Invalid Date';
        } else {
            timestamp = date.toLocaleString();
        }
    } catch (error) {
        timestamp = 'Invalid Date';
    }
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
        toggleElement(compareBtn, selectedVersions.size === 2);
    }
}

function showRevertConfirmation(versionId) {
    showElement(document.getElementById('revert-confirmation-modal'));
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
        loadAvailableTags(); // Refresh tag counts for autocomplete
        loadTags(); // Refresh sidebar tag list
    } catch (error){
        reportAppIssue('revertVersion', error, {
            promptId: currentVersionPromptId,
            versionId
        });
        showNotification(i18next.t('version.revertError'), 'error');
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
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

    showElement(document.getElementById('diff-modal'));
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
        reportAppIssue('loadDiff', error, {
            promptId: currentVersionPromptId,
            fromVersion: v1Id,
            toVersion: v2Id
        });
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
    } else {
        element.classList.remove('loading-state');
        element.disabled = false;
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

// Tag Autocomplete Implementation
let availableTags = [];
let tagAutocompleteState = {
    isOpen: false,
    highlightedIndex: -1,
    filteredTags: [],
    currentPartialTag: ''
};

async function loadAvailableTags() {
    try {
        const response = await fetch('/api/tags');
        const data = await response.json();
        // Store tags with counts
        availableTags = data.tags || [];
    } catch (error) {
        reportAppIssue('loadTagsAutocomplete', error);
        availableTags = [];
    }
}

function setupTagAutocomplete() {
    const tagInput = document.getElementById('prompt-tags');
    const autocompleteDiv = document.getElementById('tag-autocomplete');

    if (!tagInput || !autocompleteDiv) {
        return;
    }

    // Load available tags when setting up
    loadAvailableTags();

    // Input event - show suggestions as user types
    tagInput.addEventListener('input', function(event) {
        handleTagInput(event.target);
    });

    // Keydown event - handle keyboard navigation
    tagInput.addEventListener('keydown', function(event) {
        handleTagInputKeydown(event);
    });

    // Focus event - show suggestions if there's partial input
    tagInput.addEventListener('focus', function(event) {
        handleTagInput(event.target);
    });

    // Blur event - close dropdown with delay to allow clicks
    tagInput.addEventListener('blur', function(event) {
        setTimeout(() => {
            closeTagAutocomplete();
        }, 200);
    });

    // Click outside to close
    document.addEventListener('click', function(event) {
        if (!tagInput.contains(event.target) && !autocompleteDiv.contains(event.target)) {
            closeTagAutocomplete();
        }
    });
}

function handleTagInput(input) {
    const value = input.value;
    const cursorPosition = input.selectionStart;

    // Find the current tag being typed (based on cursor position)
    const beforeCursor = value.substring(0, cursorPosition);
    const lastCommaIndex = beforeCursor.lastIndexOf(',');
    const partialTag = beforeCursor.substring(lastCommaIndex + 1).trim();

    tagAutocompleteState.currentPartialTag = partialTag;

    // Get already entered tags to filter them out
    const enteredTags = getEnteredTags(input);

    // Filter available tags
    const filtered = filterTags(partialTag, enteredTags);
    tagAutocompleteState.filteredTags = filtered;
    tagAutocompleteState.highlightedIndex = -1;

    // Show or hide autocomplete
    if (filtered.length > 0 || partialTag.length > 0) {
        showTagAutocomplete(filtered);
    } else {
        closeTagAutocomplete();
    }
}

function getEnteredTags(input) {
    const value = input.value;
    const tags = value.split(',').map(tag => tag.trim().toLowerCase()).filter(tag => tag.length > 0);
    return new Set(tags);
}

function filterTags(partialTag, enteredTags) {
    if (!availableTags || availableTags.length === 0) {
        return [];
    }

    // Case-insensitive filtering
    const searchTerm = partialTag.toLowerCase();

    return availableTags
        .filter(tag => {
            const tagName = typeof tag === 'string' ? tag : tag.name;
            const tagLower = tagName.toLowerCase();
            // Don't suggest tags already entered
            if (enteredTags.has(tagLower)) {
                return false;
            }
            // Match tags that contain the search term
            return tagLower.includes(searchTerm);
        })
        .sort((a, b) => {
            // Sort by count (descending)
            const countA = typeof a === 'string' ? 0 : (a.count || 0);
            const countB = typeof b === 'string' ? 0 : (b.count || 0);
            return countB - countA;
        })
        .slice(0, 10); // Limit to 10 suggestions
}

function showTagAutocomplete(filteredTags) {
    const autocompleteDiv = document.getElementById('tag-autocomplete');
    if (!autocompleteDiv) {
        return;
    }

    autocompleteDiv.innerHTML = '';

    if (filteredTags.length === 0) {
        // Show "No matching tags" message
        const noResults = document.createElement('div');
        noResults.className = 'tag-autocomplete-no-results';
        noResults.textContent = 'No matching tags';
        autocompleteDiv.appendChild(noResults);
    } else {
        // Show tag suggestions
        filteredTags.forEach((tag, index) => {
            const tagName = typeof tag === 'string' ? tag : tag.name;
            const tagCount = typeof tag === 'string' ? null : tag.count;

            const item = document.createElement('div');
            item.className = 'tag-autocomplete-item';
            item.dataset.index = index;
            item.dataset.tagName = tagName;

            const nameSpan = document.createElement('span');
            nameSpan.className = 'tag-autocomplete-item-name';
            nameSpan.textContent = tagName;
            item.appendChild(nameSpan);

            if (tagCount !== null) {
                const countSpan = document.createElement('span');
                countSpan.className = 'tag-autocomplete-item-count';
                countSpan.textContent = `(${tagCount})`;
                item.appendChild(countSpan);
            }

            // Click handler
            item.addEventListener('click', function() {
                selectTag(tagName);
            });

            // Hover handler
            item.addEventListener('mouseenter', function() {
                highlightTagItem(index);
            });

            autocompleteDiv.appendChild(item);
        });
    }

    showElement(autocompleteDiv);
    tagAutocompleteState.isOpen = true;
}

function closeTagAutocomplete() {
    const autocompleteDiv = document.getElementById('tag-autocomplete');
    if (autocompleteDiv) {
        hideElement(autocompleteDiv);
    }
    tagAutocompleteState.isOpen = false;
    tagAutocompleteState.highlightedIndex = -1;
}

function handleTagInputKeydown(event) {
    if (!tagAutocompleteState.isOpen) {
        return;
    }

    const filteredTags = tagAutocompleteState.filteredTags;

    switch (event.key) {
        case 'ArrowDown':
            event.preventDefault();
            if (filteredTags.length > 0) {
                tagAutocompleteState.highlightedIndex =
                    (tagAutocompleteState.highlightedIndex + 1) % filteredTags.length;
                highlightTagItem(tagAutocompleteState.highlightedIndex);
            }
            break;

        case 'ArrowUp':
            event.preventDefault();
            if (filteredTags.length > 0) {
                tagAutocompleteState.highlightedIndex =
                    tagAutocompleteState.highlightedIndex <= 0
                        ? filteredTags.length - 1
                        : tagAutocompleteState.highlightedIndex - 1;
                highlightTagItem(tagAutocompleteState.highlightedIndex);
            }
            break;

        case 'Enter':
            if (tagAutocompleteState.highlightedIndex >= 0 &&
                tagAutocompleteState.highlightedIndex < filteredTags.length) {
                event.preventDefault();
                const selectedTag = filteredTags[tagAutocompleteState.highlightedIndex];
                const tagName = typeof selectedTag === 'string' ? selectedTag : selectedTag.name;
                selectTag(tagName);
            }
            break;

        case 'Escape':
            event.preventDefault();
            event.stopPropagation();
            closeTagAutocomplete();
            break;

        case 'Tab':
            if (tagAutocompleteState.highlightedIndex >= 0 &&
                tagAutocompleteState.highlightedIndex < filteredTags.length) {
                event.preventDefault();
                const selectedTag = filteredTags[tagAutocompleteState.highlightedIndex];
                const tagName = typeof selectedTag === 'string' ? selectedTag : selectedTag.name;
                selectTag(tagName);
            }
            break;
    }
}

function highlightTagItem(index) {
    const autocompleteDiv = document.getElementById('tag-autocomplete');
    if (!autocompleteDiv) {
        return;
    }

    // Remove previous highlight
    autocompleteDiv.querySelectorAll('.tag-autocomplete-item').forEach(item => {
        item.classList.remove('highlighted');
    });

    // Add new highlight
    const items = autocompleteDiv.querySelectorAll('.tag-autocomplete-item');
    if (items[index]) {
        items[index].classList.add('highlighted');
        // Scroll into view if needed
        items[index].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    tagAutocompleteState.highlightedIndex = index;
}

function selectTag(tagName) {
    const tagInput = document.getElementById('prompt-tags');
    if (!tagInput) {
        return;
    }

    const value = tagInput.value;
    const cursorPosition = tagInput.selectionStart;

    // Find the position of the last comma before cursor
    const beforeCursor = value.substring(0, cursorPosition);
    const lastCommaIndex = beforeCursor.lastIndexOf(',');

    // Build the new value
    let newValue;
    let newCursorPosition;

    if (lastCommaIndex === -1) {
        // No comma yet - replace entire input
        newValue = tagName + ', ';
        newCursorPosition = newValue.length;
    } else {
        // Replace text after last comma
        const beforeTag = value.substring(0, lastCommaIndex + 1);
        const afterCursor = value.substring(cursorPosition);
        // Remove any existing partial tag and add the selected tag
        newValue = beforeTag + ' ' + tagName + ', ' + afterCursor;
        newCursorPosition = (beforeTag + ' ' + tagName + ', ').length;
    }

    // Update input
    tagInput.value = newValue;
    tagInput.setSelectionRange(newCursorPosition, newCursorPosition);
    tagInput.focus();

    // Close autocomplete
    closeTagAutocomplete();

    // Trigger input event to potentially show new suggestions
    setTimeout(() => {
        handleTagInput(tagInput);
    }, 50);
}

// ============================================
// Bulk Actions & Selection Functions
// ============================================

function initializeBulkActions() {
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
    const clearSelectionBtn = document.getElementById('clear-selection-btn');
    const confirmBulkDeleteBtn = document.getElementById('confirm-bulk-delete-btn');
    const cancelBulkDeleteBtn = document.getElementById('cancel-bulk-delete-btn');

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', handleSelectAll);
    }

    if (bulkDeleteBtn) {
        bulkDeleteBtn.addEventListener('click', showBulkDeleteConfirmation);
    }

    if (clearSelectionBtn) {
        clearSelectionBtn.addEventListener('click', clearSelection);
    }

    if (confirmBulkDeleteBtn) {
        confirmBulkDeleteBtn.addEventListener('click', performBulkDelete);
    }

    if (cancelBulkDeleteBtn) {
        cancelBulkDeleteBtn.addEventListener('click', hideBulkDeleteModal);
    }
}

function handleCheckboxChange(promptId, isChecked) {
    if (isChecked) {
        selectedPromptIds.add(promptId);
    } else {
        selectedPromptIds.delete(promptId);
    }
    updateBulkActionsUI();
}

function handleSelectAll(event) {
    const isChecked = event.target.checked;
    const checkboxes = document.querySelectorAll('.prompt-checkbox');

    checkboxes.forEach(checkbox => {
        checkbox.checked = isChecked;
        const promptId = parseInt(checkbox.dataset.promptId);
        if (isChecked) {
            selectedPromptIds.add(promptId);
        } else {
            selectedPromptIds.delete(promptId);
        }
    });

    updateBulkActionsUI();
}

function updateBulkActionsUI() {
    const toolbar = document.getElementById('bulk-actions-toolbar');
    const countElement = document.getElementById('selected-count');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');

    if (selectedPromptIds.size > 0) {
        toolbar.style.display = 'block';
        countElement.textContent = i18next.t('bulkDelete.selectedCount', { count: selectedPromptIds.size });
    } else {
        toolbar.style.display = 'none';
    }

    // Update select all checkbox state
    const allCheckboxes = document.querySelectorAll('.prompt-checkbox');
    const allChecked = allCheckboxes.length > 0 &&
                       selectedPromptIds.size === allCheckboxes.length;
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = allChecked;
    }

    // Update selected styling on prompt items
    allCheckboxes.forEach(checkbox => {
        const promptId = parseInt(checkbox.dataset.promptId);
        const promptItem = checkbox.closest('.prompt-item');
        if (promptItem) {
            if (selectedPromptIds.has(promptId)) {
                promptItem.classList.add('selected');
            } else {
                promptItem.classList.remove('selected');
            }
        }
    });
}

function clearSelection() {
    selectedPromptIds.clear();
    const checkboxes = document.querySelectorAll('.prompt-checkbox');
    checkboxes.forEach(checkbox => checkbox.checked = false);
    updateBulkActionsUI();
}

function showBulkDeleteConfirmation() {
    if (selectedPromptIds.size === 0) return;

    const modal = document.getElementById('bulk-delete-modal');
    const countElement = document.getElementById('bulk-delete-count');
    countElement.textContent = selectedPromptIds.size;
    modal.classList.remove(HIDDEN_CLASS);
}

function hideBulkDeleteModal() {
    const modal = document.getElementById('bulk-delete-modal');
    modal.classList.add(HIDDEN_CLASS);
}

async function performBulkDelete() {
    if (selectedPromptIds.size === 0) return;

    const promptIdsArray = Array.from(selectedPromptIds);

    try {
        const response = await fetch('/api/prompts/bulk', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt_ids: promptIdsArray
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            hideBulkDeleteModal();
            clearSelection();

            // Show success message
            const message = i18next.t('bulkDelete.successMessage', {
                deleted: result.deleted_count,
                failed: result.failed_count
            });
            alert(message);

            // Refresh UI
            await loadPrompts();
            await loadAvailableTags();
            await loadTags();

            // Report errors if any
            if (result.failed_count > 0) {
                reportAppIssue(
                    'bulk-delete-partial-failure',
                    new Error(`${result.failed_count} prompts failed to delete`),
                    { failed_ids: result.failed_ids },
                    'warning'
                );
            }
        } else {
            throw new Error(result.detail || 'Bulk deletion failed');
        }
    } catch (error) {
        console.error('Bulk delete error:', error);
        alert(i18next.t('bulkDelete.errorMessage'));
        reportAppIssue('bulk-delete-failed', error, {
            prompt_ids: promptIdsArray
        });
    }
}

// Initialize lazy loading on app start
initializeLazyLoading();

// Logout function
async function logout() {
    try {
        const token = localStorage.getItem('access_token');
        if (token) {
            await fetch('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
        }
    } catch (error) {
        console.error('Logout error:', error);
        reportAppIssue('logout-error', error, {}, 'warning');
    } finally {
        // Always clear storage and redirect
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        sessionStorage.clear();
        
        window.location.href = '/auth/login';
    }
}

