#!/usr/bin/env node
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const root = join(process.cwd(), 'tests', 'accessibility');
const specFiles = readdirSync(root)
  .filter((file) => file.endsWith('.spec.ts'))
  .map((file) => join(root, file));

const checks = [
  {
    name: 'hardcoded_local_url',
    pattern: /https?:\/\/(?:localhost|127\.0\.0\.1):\d+/g,
    message: 'Hardcoded local URL detected. Use fixtures/getBaseURL or ACCESSIBILITY_BASE_URL.',
  },
  {
    name: 'hardcoded_credentials',
    pattern: /test_(?:admin|user)_ui@example\.com|Test(?:Admin|User)@Pass\d+/g,
    message: 'Hardcoded credentials detected. Use ACCESSIBILITY_* env vars and auth fixtures.',
  },
  {
    name: 'arbitrary_sleep',
    pattern: /waitForTimeout\(/g,
    message: 'Arbitrary sleep detected. Replace with event/assertion-based waiting.',
  },
];

let hasFailure = false;

for (const file of specFiles) {
  const content = readFileSync(file, 'utf8');

  for (const check of checks) {
    const matches = content.match(check.pattern);
    if (matches && matches.length > 0) {
      hasFailure = true;
      console.error(`\n[${check.name}] ${file}`);
      console.error(`  ${check.message}`);
      console.error(
        `  Matches: ${matches.slice(0, 5).join(', ')}${matches.length > 5 ? ' ...' : ''}`
      );
    }
  }

  const testCount = (content.match(/\btest\(/g) || []).length;
  const expectCount = (content.match(/\bexpect\(/g) || []).length;
  if (testCount > 0 && expectCount === 0) {
    hasFailure = true;
    console.error(`\n[missing_expect] ${file}`);
    console.error('  File defines tests but has zero expect(...) assertions.');
  }

  const hasTag = content.includes('@regression-a11y') || content.includes('@smoke-a11y');
  if (!hasTag) {
    hasFailure = true;
    console.error(`\n[missing_tag] ${file}`);
    console.error('  File must include @regression-a11y or @smoke-a11y for CI filtering.');
  }
}

if (hasFailure) {
  process.exit(1);
}

console.log(`Accessibility spec hygiene passed for ${specFiles.length} spec files.`);
