/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: 'src/web/static',
  base: '/static/',
  publicDir: false,

  build: {
    outDir: '../../../dist/static',
    emptyOutDir: true,
    manifest: true,
    sourcemap: true,
    rollupOptions: {
      input: {
        // Main application
        app: resolve(__dirname, 'src/web/static/ts/app.ts'),
        // Authentication pages
        auth: resolve(__dirname, 'src/web/static/ts/auth.ts'),
        profile: resolve(__dirname, 'src/web/static/ts/profile.ts'),
        passwordReset: resolve(__dirname, 'src/web/static/ts/password-reset.ts'),
        // Admin pages
        adminUsers: resolve(__dirname, 'src/web/static/ts/admin-users.ts'),
        adminSessions: resolve(__dirname, 'src/web/static/ts/admin-sessions.ts'),
        // Feature pages
        importExport: resolve(__dirname, 'src/web/static/ts/import-export.ts'),
        backupManagement: resolve(__dirname, 'src/web/static/ts/backup-management.ts'),
        'manage-categories': resolve(__dirname, 'src/web/static/ts/manage-categories.ts'),
        'manage-tags': resolve(__dirname, 'src/web/static/ts/manage-tags.ts'),
        // Shared telemetry (loaded on all pages)
        telemetry: resolve(__dirname, 'src/web/static/ts/telemetry.ts'),
      },
      output: {
        entryFileNames: 'js/[name].[hash].js',
        chunkFileNames: 'js/chunks/[name].[hash].js',
        assetFileNames: 'assets/[name].[hash][extname]',
      },
    },
  },

  resolve: {
    alias: {
      '@': resolve(__dirname, 'src/web/static/ts'),
      '@types': resolve(__dirname, 'src/web/static/ts/types'),
      '@components': resolve(__dirname, 'src/web/static/ts/components/index.ts'),
    },
  },

  css: {
    postcss: './postcss.config.js',
  },

  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/static/locales': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
    },
  },
});
