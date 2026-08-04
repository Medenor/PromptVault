import { defineConfig } from 'vitest/config';
import path from 'node:path';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['src/web/static/ts/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/web/static/ts/utils/**/*.ts'],
      thresholds: {
        lines: 85,
        branches: 85,
        functions: 85,
        statements: 85,
      },
    },
  },
  resolve: {
    alias: {
      '@components': path.resolve(__dirname, 'src/web/static/ts/components/index.ts'),
      '@': path.resolve(__dirname, 'src/web/static/ts'),
    },
  },
});
