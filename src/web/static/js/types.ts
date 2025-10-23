// Type definitions for PromptVault application

export interface Prompt {
  title: string;
  prompt: string;
  category?: string;
  tags?: string[];
  favorite?: boolean;
}

export interface PromptData {
  prompts: Record<string, Prompt>;
}

export interface CategoryData {
  categories: string[];
}

export interface TagData {
  tags: string[];
}

export interface ImportExportStats {
  total_prompts: number;
  total_categories: number;
  total_tags: number;
  favorite_prompts: number;
}

export interface FilterOptions {
  category?: string;
  tag?: string;
  favorites?: boolean;
}

export interface ExportOptions {
  format: 'csv' | 'json' | 'markdown';
  filename: string;
  include_favorites: boolean;
  include_metadata: boolean;
}

export interface ImportOptions {
  mode: 'append' | 'replace';
  validate: boolean;
}

// i18next module declarations
declare global {
  interface Window {
    i18next: any;
    i18nextHttpBackend: any;
    i18nextBrowserLanguageDetector: any;
  }
}

// DOM element extensions
declare global {
  interface HTMLElement {
    dataset: DOMStringMap;
  }
}
