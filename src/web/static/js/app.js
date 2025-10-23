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

    // Add event listeners
    div.querySelector('.copy-btn').addEventListener('click', () => copyPrompt(id));
    div.querySelector('.edit-btn').addEventListener('click', () => editPrompt(id));
    div.querySelector('.delete-btn').addEventListener('click', () => deletePrompt(id));
    div.querySelector('.favorite-btn').addEventListener('click', () => toggleFavorite(id));

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

async function copyPrompt(id) {
    try {
        const response = await fetch(`/api/prompts/${id}`);
        const prompt = await response.json();

        const textToCopy = prompt.prompt;

        // Try modern Clipboard API first
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(textToCopy);
            showCopyFeedback(id, 'Copied!');
        } else {
            // Fallback for older browsers or non-HTTPS
            fallbackCopyTextToClipboard(textToCopy, id);
        }
    } catch (error) {
        console.error('Error copying prompt:', error);
        showCopyFeedback(id, 'Copy failed');
    }
}

function fallbackCopyTextToClipboard(text, id) {
    // Create a temporary textarea element
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);

    try {
        textArea.focus();
        textArea.select();

        const successful = document.execCommand('copy');
        if (successful) {
            showCopyFeedback(id, 'Copied!');
        } else {
            showCopyFeedback(id, 'Copy failed');
        }
    } catch (error) {
        console.error('Fallback copy failed:', error);
        showCopyFeedback(id, 'Copy failed');
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

        console.log('Editing prompt:', prompt); // Debug log

        // Show editor without resetting form
        document.getElementById('prompt-editor').style.display = 'block';
        document.getElementById('prompts-list').style.display = 'none';

        // Populate form
        document.getElementById('prompt-title').value = prompt.title || '';
        document.getElementById('prompt-content').value = prompt.prompt || '';
        document.getElementById('prompt-category').value = prompt.category || '';
        document.getElementById('prompt-tags').value = prompt.tags ? prompt.tags.join(', ') : '';

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
    // This would need a specific endpoint for toggling favorite
    // For now, we'll implement a basic version
    alert(i18next.t('messages.favoriteNotImplemented'));
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
        // Re-render prompts to update dynamic content
        loadPrompts();
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
