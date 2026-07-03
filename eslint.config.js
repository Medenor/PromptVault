import js from '@eslint/js';
import tsParser from '@typescript-eslint/parser';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import prettierConfig from 'eslint-config-prettier';
import prettierPlugin from 'eslint-plugin-prettier';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import globals from 'globals';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default [
  {
    ignores: [
      'node_modules/**',
      'dist/**',
      'src/web/static/js/**',
      'src/web/static/vendor/**',
      '**/coverage/**',
      '**/*.min.*',
      '.venv/**',
      'venv/**',
      'htmlcov/**',
      'tests/htmlcov/**',
      'data/**',
      'tests/accessibility/**',
      'tests/e2e/**',
      'scripts/**',
      'playwright.config.ts',
      'tailwind.config.ts',
    ],
  },
  js.configs.recommended,
  {
    files: ['**/*.{js,mjs,cjs,ts,tsx}'],
    plugins: { prettier: prettierPlugin },
    rules: {
      'prettier/prettier': 'error',
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    ignores: ['tailwind.config.ts', 'vitest.config.ts'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        project: './tsconfig.json',
        tsconfigRootDir: __dirname,
        sourceType: 'module',
        ecmaVersion: 2022,
      },
      globals: {
        ...globals.browser,
        ...globals.es2022,
      },
    },
    plugins: { '@typescript-eslint': tsPlugin },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      '@typescript-eslint/no-unused-vars': [
        'error',
        { varsIgnorePattern: '^_', argsIgnorePattern: '^_' },
      ],
    },
  },
  {
    files: ['vite.config.ts', 'vitest.config.ts', 'tailwind.config.ts', 'postcss.config.js'],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },
  prettierConfig,
];
