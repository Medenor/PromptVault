// PromptVault Web App TypeScript

import './types';
import { Prompt, PromptData, CategoryData, TagData, FilterOptions } from './types';

// Initialize i18next
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
                initializeApp();
            });
        } else {
            // DOM is already loaded
            updateStaticTranslations();
            initializeApp();
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

function initializeApp(): void {
    // Event listeners
    setupEventListeners();

    // Load initial data
    loadPrompts();
    loadCategories();
    loadTags();
}

function setupEventListeners(): void {
    // Language selector
    const languageSelector: HTMLSelectElement | null = document.getElementById('language-selector') as HTMLSelectElement;
    if (languageSelector) {
        languageSelector.addEventListener('change', (event: Event): void => {
            handleLanguageChange(event);
        });
    }

    // New prompt button
    const newPromptBtn: HTMLElement | null = document.getElementById('new-prompt-btn');
    if (newPromptBtn) {
        newPromptBtn.addEventListener('click', showNewPromptForm);
    }

    // Import/Export button (navigates to import/export page)
    const importExportBtn: HTMLElement | null = document.getElementById('import-export-btn');
    if (importExportBtn) {
        importExportBtn.addEventListener('click', function(): void {
            window.location.href = '/import-export';
        });
    }

    // Form handling
    const promptForm: HTMLFormElement | null = document.getElementById('prompt-form') as HTMLFormElement;
    if (promptForm) {
        promptForm.addEventListener('submit', (event: Event): void => {
            handlePromptSubmit(event);
        });
    }

    const cancelBtn: HTMLElement | null = document.getElementById('cancel-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', hidePromptEditor);
    }

    // Category and tag filtering
    const categoriesList: HTMLElement | null = document.getElementById('categories-list');
    if (categoriesList) {
        categoriesList.addEventListener('click', (event: Event): void => {
            handleCategoryFilter(event);
        });
    }

    const tagsList: HTMLElement | null = document.getElementById('tags-list');
    if (tagsList) {
        tagsList.addEventListener('click', (event: Event): void => {
            handleTagFilter(event);
        });
    }

    const favoritesFilter: HTMLInputElement | null = document.getElementById('favorites-filter') as HTMLInputElement;
    if (favoritesFilter) {
        favoritesFilter.addEventListener('change', (event: Event): void => {
            handleFavoritesFilter(event);
        });
    }

    // Modal close
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

async function loadPrompts(): Promise<void> {
    try {
        console.log('Loading prompts...');
        const response: Response = await fetch('/api/prompts');
        const data: PromptData = await response.json();
        console.log('Loaded prompts data:', data);
        console.log('Number of prompts:', Object.keys(data.prompts || {}).length);
        renderPrompts(data.prompts);
    } catch (error: unknown) {
        console.error('Error loading prompts:', error);
    }
}

async function loadCategories(): Promise<void> {
    try {
        const response: Response = await fetch('/api/categories');
        const data: CategoryData = await response.json();
        renderCategories(data.categories);
    } catch (error: unknown) {
        console.error('Error loading categories:', error);
    }
}

async function loadTags(): Promise<void> {
    try {
        const response: Response = await fetch('/api/tags');
        const data: TagData = await response.json();
        renderTags(data.tags);
    } catch (error: unknown) {
        console.error('Error loading tags:', error);
    }
}

function renderPrompts(prompts: Record<string, Prompt>): void {
    const container: HTMLElement | null = document.getElementById('prompts-list');
    if (!container) return;

    container.innerHTML = '';

    for (const [id, prompt] of Object.entries(prompts)) {
        const promptElement: HTMLElement = createPromptElement(id, prompt);
        container.appendChild(promptElement);
    }
}

function createPromptElement(id: string, prompt: Prompt): HTMLElement {
    const div: HTMLDivElement = document.createElement('div');
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
    div.querySelectorAll('[data-i18n]').forEach((element: Element): void => {
        const key: string | null = element.getAttribute('data-i18n');
        if (key) {
            (element as HTMLElement).textContent = i18next.t(key);
        }
    });

    // Add event listeners
    const copyBtn: HTMLButtonElement | null = div.querySelector('.copy-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', (): void => {
            copyPrompt(id).catch((error: unknown): void => {
                console.error('Error copying prompt:', error);
            });
        });
    }

    const editBtn: HTMLButtonElement | null = div.querySelector('.edit-btn');
    if (editBtn) {
        editBtn.addEventListener('click', (): void => {
            editPrompt(id).catch((error: unknown): void => {
                console.error('Error editing prompt:', error);
            });
        });
    }

    const deleteBtn: HTMLButtonElement | null = div.querySelector('.delete-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', (): void => {
            deletePrompt(id).catch((error: unknown): void => {
                console.error('Error deleting prompt:', error);
            });
        });
    }

    const favoriteBtn: HTMLButtonElement | null = div.querySelector('.favorite-btn');
    if (favoriteBtn) {
        favoriteBtn.addEventListener('click', (): void => {
            toggleFavorite(id).catch((error: unknown): void => {
                console.error('Error toggling favorite:', error);
            });
        });
    }

    return div;
}

function renderCategories(categories: string[]): void {
    const list: HTMLElement | null = document.getElementById('categories-list');
    if (!list) return;

    // Clear existing categories except "All Prompts"
    const allPromptsItem: Element | null = list.querySelector('[data-category="all"]');
    list.innerHTML = '';
    if (allPromptsItem) {
        list.appendChild(allPromptsItem);
    }

    categories.forEach((category: string): void => {
        const li: HTMLLIElement = document.createElement('li');
        li.dataset.category = category;
        li.textContent = category;
        list.appendChild(li);
    });
}

function renderTags(tags: string[]): void {
    const list: HTMLElement | null = document.getElementById('tags-list');
    if (!list) return;

    // Clear existing tags except "All Tags"
    const allTagsItem: Element | null = list.querySelector('[data-tag="all"]');
    list.innerHTML = '';
    if (allTagsItem) {
        list.appendChild(allTagsItem);
    }

    tags.forEach((tag: string): void => {
        const li: HTMLLIElement = document.createElement('li');
        li.dataset.tag = tag;
        li.textContent = tag;
        list.appendChild(li);
    });
}

function showNewPromptForm(): void {
    const promptEditor: HTMLElement | null = document.getElementById('prompt-editor');
    if (promptEditor) {
        promptEditor.style.display = 'block';
    }

    const promptForm: HTMLFormElement | null = document.getElementById('prompt-form') as HTMLFormElement;
    if (promptForm) {
        promptForm.reset();
    }

    const promptsList: HTMLElement | null = document.getElementById('prompts-list');
    if (promptsList) {
        promptsList.style.display = 'none';
    }
}

function hidePromptEditor(): void {
    const promptEditor: HTMLElement | null = document.getElementById('prompt-editor');
    if (promptEditor) {
        promptEditor.style.display = 'none';
    }

    const promptsList: HTMLElement | null = document.getElementById('prompts-list');
    if (promptsList) {
        promptsList.style.display = 'flex';
    }
}

async function handlePromptSubmit(event: Event): Promise<void> {
    event.preventDefault();

    const form: HTMLFormElement = event.target as HTMLFormElement;
    const formData: FormData = new FormData(form);
    const isEditMode: boolean = form.dataset.mode === 'edit';
    const promptId: string | undefined = form.dataset.id;

    // Debug logging
    console.log('Form submission:', { isEditMode, promptId });
    for (const [key, value] of formData.entries()) {
        console.log(`${key}: ${value}`);
    }

    try {
        let url: string = '/api/prompts';
        let method: string = 'POST';

        if (isEditMode && promptId) {
            url = `/api/prompts/${promptId}`;
            method = 'PUT';
        }

        console.log(`Sending ${method} request to ${url}`);

        const response: Response = await fetch(url, {
            method: method,
            body: formData
        });

        console.log('Response status:', response.status);
        const responseData: any = await response.json();
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
    } catch (error: unknown) {
        console.error('Error saving prompt:', error);
        alert(i18next.t('messages.error'));
    }
}

async function copyPrompt(id: string): Promise<void> {
    try {
        const response: Response = await fetch(`/api/prompts/${id}`);
        const prompt: Prompt = await response.json();

        const textToCopy: string = prompt.prompt;

        // Try modern Clipboard API first
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(textToCopy);
            showCopyFeedback(id, 'Copied!');
        } else {
            // Fallback for older browsers or non-HTTPS
            fallbackCopyTextToClipboard(textToCopy, id);
        }
    } catch (error: unknown) {
        console.error('Error copying prompt:', error);
        showCopyFeedback(id, 'Copy failed');
    }
}

function fallbackCopyTextToClipboard(text: string, id: string): void {
    // Create a temporary textarea element
    const textArea: HTMLTextAreaElement = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);

    try {
        textArea.focus();
        textArea.select();

        const successful: boolean = document.execCommand('copy');
        if (successful) {
            showCopyFeedback(id, 'Copied!');
        } else {
            showCopyFeedback(id, 'Copy failed');
        }
    } catch (error: unknown) {
        console.error('Fallback copy failed:', error);
        showCopyFeedback(id, 'Copy failed');
    } finally {
        document.body.removeChild(textArea);
    }
}

function showCopyFeedback(id: string, message: string): void {
    const btn: HTMLButtonElement | null = document.querySelector(`.copy-btn[data-id="${id}"]`);
    if (btn) {
        const originalText: string = btn.textContent || '';
        // Use translated message if it's a key, otherwise use as-is
        const translatedMessage: string = i18next.t(message) !== message ? i18next.t(message) : message;
        btn.textContent = translatedMessage;
        setTimeout((): void => {
            btn.textContent = originalText;
        }, 2000);
    }
}

async function editPrompt(id: string): Promise<void> {
    try {
        const response: Response = await fetch(`/api/prompts/${id}`);
        const prompt: Prompt = await response.json();

        console.log('Editing prompt:', prompt); // Debug log

        // Show editor without resetting form
        const promptEditor: HTMLElement | null = document.getElementById('prompt-editor');
        if (promptEditor) {
            promptEditor.style.display = 'block';
        }

        const promptsList: HTMLElement | null = document.getElementById('prompts-list');
        if (promptsList) {
            promptsList.style.display = 'none';
        }

        // Populate form
        const titleInput: HTMLInputElement | null = document.getElementById('prompt-title') as HTMLInputElement;
        if (titleInput) {
            titleInput.value = prompt.title || '';
        }

        const contentInput: HTMLTextAreaElement | null = document.getElementById('prompt-content') as HTMLTextAreaElement;
        if (contentInput) {
            contentInput.value = prompt.prompt || '';
        }

        const categoryInput: HTMLInputElement | null = document.getElementById('prompt-category') as HTMLInputElement;
        if (categoryInput) {
            categoryInput.value = prompt.category || '';
        }

        const tagsInput: HTMLInputElement | null = document.getElementById('prompt-tags') as HTMLInputElement;
        if (tagsInput) {
            tagsInput.value = prompt.tags ? prompt.tags.join(', ') : '';
        }

        // Change form to update mode
        const form: HTMLFormElement | null = document.getElementById('prompt-form') as HTMLFormElement;
        if (form) {
            form.dataset.mode = 'edit';
            form.dataset.id = id;
        }

    } catch (error: unknown) {
        console.error('Error loading prompt for edit:', error);
    }
}

async function deletePrompt(id: string): Promise<void> {
    if (!confirm(i18next.t('messages.confirmDelete'))) {
        return;
    }

    try {
        const response: Response = await fetch(`/api/prompts/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadPrompts(); // Refresh the list
        } else {
            alert(i18next.t('messages.error'));
        }
    } catch (error: unknown) {
        console.error('Error deleting prompt:', error);
        alert(i18next.t('messages.error'));
    }
}

async function toggleFavorite(id: string): Promise<void> {
    // This would need a specific endpoint for toggling favorite
    // For now, we'll implement a basic version
    alert(i18next.t('messages.favoriteNotImplemented'));
}

function handleCategoryFilter(event: Event): void {
    const target: HTMLElement = event.target as HTMLElement;
    if (target.tagName === 'LI') {
        // Update active state
        const categoriesList: HTMLElement | null = document.getElementById('categories-list');
        if (categoriesList) {
            categoriesList.querySelectorAll('li').forEach((li: Element): void => {
                li.classList.remove('active');
            });
            target.classList.add('active');
        }

        // Filter prompts (simplified - would need backend filtering)
        const category: string = target.dataset.category || '';
        filterPrompts({ category });
    }
}

function handleTagFilter(event: Event): void {
    const target: HTMLElement = event.target as HTMLElement;
    if (target.tagName === 'LI') {
        // Update active state
        const tagsList: HTMLElement | null = document.getElementById('tags-list');
        if (tagsList) {
            tagsList.querySelectorAll('li').forEach((li: Element): void => {
                li.classList.remove('active');
            });
            target.classList.add('active');
        }

        // Filter prompts
        const tag: string = target.dataset.tag || '';
        filterPrompts({ tag });
    }
}

function handleFavoritesFilter(event: Event): void {
    const target: HTMLInputElement = event.target as HTMLInputElement;
    filterPrompts({ favorites: target.checked });
}

function filterPrompts(filters: FilterOptions): void {
    // This is a simplified client-side filter
    // In a real app, you'd want server-side filtering
    const promptItems: NodeListOf<Element> = document.querySelectorAll('.prompt-item');

    promptItems.forEach((item: Element): void => {
        let show: boolean = true;

        if (filters.category && filters.category !== 'all') {
            const categoryElement: HTMLElement | null = item.querySelector('.category');
            if (categoryElement) {
                const category: string = categoryElement.textContent || '';
                if (category !== filters.category) {
                    show = false;
                }
            }
        }

        if (filters.tag && filters.tag !== 'all') {
            const tagsElement: HTMLElement | null = item.querySelector('.tags');
            if (!tagsElement || !tagsElement.textContent || !tagsElement.textContent.includes(filters.tag)) {
                show = false;
            }
        }

        if (filters.favorites) {
            const favoriteBtn: HTMLButtonElement | null = item.querySelector('.favorite-btn');
            if (favoriteBtn && favoriteBtn.textContent !== '★') {
                show = false;
            }
        }

        (item as HTMLElement).style.display = show ? 'block' : 'none';
    });
}

function handleLanguageChange(event: Event): void {
    const target: HTMLSelectElement = event.target as HTMLSelectElement;
    const selectedLanguage: string = target.value;
    i18next.changeLanguage(selectedLanguage, (err: any, t: any): void => {
        if (err) {
            console.error('Error changing language:', err);
            return;
        }
        // Update all translations on the page
        updateStaticTranslations();
        // Re-render prompts to update dynamic content
        loadPrompts().catch((error: unknown): void => {
            console.error('Error reloading prompts after language change:', error);
        });
    });
}

function handleImport(): void {
    // Create file input
    const input: HTMLInputElement = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,.csv,.md';
    input.onchange = async (event: Event): Promise<void> => {
        const target: HTMLInputElement = event.target as HTMLInputElement;
        const file: File | null = target.files ? target.files[0] : null;
        if (file) {
            // Handle file upload
            alert('Import functionality not yet implemented');
        }
    };
    input.click();
}

function handleExport(): void {
    // Simple export - in real app, would call backend
    alert('Export functionality not yet implemented');
}

function hideModal(): void {
    const modal: HTMLElement | null = document.getElementById('prompt-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function truncateText(text: string | null | undefined, maxLength: number): string {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}
