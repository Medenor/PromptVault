// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/**
 * Accessibility Test Summary Generator
 * Analyzes test files and generates summary statistics and markdown report
 */

import * as fs from 'fs';
import * as path from 'path';
import * as glob from 'glob';

interface TestStats {
  file: string;
  name: string;
  testCount: number;
  describeCount: number;
  wcagCriteria: string[];
}

interface SummaryStats {
  totalTests: number;
  totalFiles: number;
  totalDescribeBlocks: number;
  wcagCriteriaCovered: Set<string>;
  fileStats: TestStats[];
}

/**
 * Count test cases in a file
 */
function countTestsInFile(content: string): number {
  const testMatches = content.match(/test\s*\(/g);
  return testMatches ? testMatches.length : 0;
}

/**
 * Count describe blocks in a file
 */
function countDescribeBlocks(content: string): number {
  const describeMatches = content.match(/test\.describe\s*\(/g);
  return describeMatches ? describeMatches.length : 0;
}

/**
 * Extract WCAG criteria from test file
 */
function extractWCAGCriteria(content: string): string[] {
  const criteria = new Set<string>();
  const wcagPattern = /WCAG\s+(\d+\.\d+\.\d+)/gi;
  let match: RegExpExecArray | null;

  while ((match = wcagPattern.exec(content)) !== null) {
    const captured = match[1];
    if (captured) {
      criteria.add(captured);
    }
  }

  return Array.from(criteria).sort();
}

/**
 * Get test files
 */
function getTestFiles(dir: string): string[] {
  const pattern = path.join(dir, '**/*.spec.ts');
  return glob.sync(pattern);
}

/**
 * Analyze test files
 */
function analyzeTestFiles(testDir: string): SummaryStats {
  const files = getTestFiles(testDir);
  const stats: SummaryStats = {
    totalTests: 0,
    totalFiles: files.length,
    totalDescribeBlocks: 0,
    wcagCriteriaCovered: new Set(),
    fileStats: [],
  };

  files.forEach((file) => {
    const content = fs.readFileSync(file, 'utf-8');
    const testCount = countTestsInFile(content);
    const describeCount = countDescribeBlocks(content);
    const wcagCriteria = extractWCAGCriteria(content);
    const fileName = path.basename(file);

    stats.fileStats.push({
      file: fileName,
      name: fileName.replace('.spec.ts', ''),
      testCount,
      describeCount,
      wcagCriteria,
    });

    stats.totalTests += testCount;
    stats.totalDescribeBlocks += describeCount;

    wcagCriteria.forEach((c) => stats.wcagCriteriaCovered.add(c));
  });

  return stats;
}

/**
 * Generate markdown summary
 */
function generateMarkdownSummary(stats: SummaryStats): string {
  const wcagArray = Array.from(stats.wcagCriteriaCovered).sort();

  let markdown = `# Accessibility Test Summary

Generated: ${new Date().toLocaleString()}

## Overview

| Metric | Value |
|--------|-------|
| **Total Test Files** | ${stats.totalFiles} |
| **Total Test Cases** | ${stats.totalTests} |
| **Total Test Suites** | ${stats.totalDescribeBlocks} |
| **WCAG Criteria Covered** | ${wcagArray.length} |

## Test Files

| File | Tests | Suites | WCAG Criteria |
|------|-------|--------|---------------|
${stats.fileStats.map((f) => `| ${f.name} | ${f.testCount} | ${f.describeCount} | ${f.wcagCriteria.join(', ') || 'N/A'} |`).join('\n')}

## WCAG 2.1 AA Criteria Coverage

### Covered Criteria (${wcagArray.length})

\`\`\`
${wcagArray.join('\n')}
\`\`\`

### Coverage by Category

#### Perceivable
- 1.3.1 - Info and Relationships
- 1.4.3 - Contrast (Minimum)

#### Operable
- 2.1.1 - Keyboard
- 2.1.2 - No Keyboard Trap
- 2.4.1 - Bypass Blocks
- 2.4.2 - Page Titled
- 2.4.3 - Focus Order
- 2.4.4 - Link Purpose
- 2.4.7 - Focus Visible

#### Understandable
- 3.3.2 - Labels or Instructions

#### Robust
- 4.1.2 - Name, Role, Value

## Quick Commands

### Run All Tests
\`\`\`bash
npm run test:ui:accessibility
\`\`\`

### Run Specific File
\`\`\`bash
npx playwright test ${stats.fileStats[0]?.name || 'main-page'}.spec.ts
\`\`\`

### View Report
\`\`\`bash
open playwright-report/index.html
\`\`\`

### Debug Mode
\`\`\`bash
HEADED=1 npm run test:ui:accessibility
\`\`\`

## Documentation

- **RUN_TESTS.md** - Comprehensive guide for running tests
- **COVERAGE.md** - Detailed coverage breakdown
- **CONTRIBUTING.md** - Guide for adding new tests
- **README.md** - Full utility documentation
- **QUICK_START.md** - Quick reference guide

## Latest Results

Run \`npm run test:ui:accessibility:report\` to generate the latest HTML report with detailed results.

---

For more information, see the documentation files in the \`tests/accessibility/\` directory.
`;

  return markdown;
}

/**
 * Generate JSON summary
 */
function generateJsonSummary(stats: SummaryStats): object {
  return {
    timestamp: new Date().toISOString(),
    summary: {
      totalTestFiles: stats.totalFiles,
      totalTestCases: stats.totalTests,
      totalTestSuites: stats.totalDescribeBlocks,
      wcagCriteriaCovered: Array.from(stats.wcagCriteriaCovered).sort(),
    },
    files: stats.fileStats.map((f) => ({
      name: f.name,
      path: f.file,
      testCount: f.testCount,
      describeCount: f.describeCount,
      wcagCriteria: f.wcagCriteria,
    })),
  };
}

/**
 * Update README with summary
 */
function updateReadme(testDir: string, stats: SummaryStats): void {
  const readmePath = path.join(testDir, 'README.md');

  if (!fs.existsSync(readmePath)) {
    console.warn('README.md not found, skipping update');
    return;
  }

  let content = fs.readFileSync(readmePath, 'utf-8');

  // Update test statistics section
  const statsSection = `
## Test Statistics

- **Total Tests**: ${stats.totalFiles} files with ${stats.totalTests} test cases
- **Test Suites**: ${stats.totalDescribeBlocks} test suites
- **WCAG Criteria**: ${Array.from(stats.wcagCriteriaCovered).length} criteria covered
- **Last Updated**: ${new Date().toLocaleString()}
`;

  // Replace or insert statistics
  if (content.includes('## Test Statistics')) {
    content = content.replace(
      /## Test Statistics[\s\S]*?(?=##|\Z)/,
      statsSection + '\n'
    );
  } else {
    // Insert after first section
    const firstSectionEnd = content.indexOf('\n## ', 10);
    if (firstSectionEnd > 0) {
      content = content.slice(0, firstSectionEnd) + '\n' + statsSection + content.slice(firstSectionEnd);
    }
  }

  fs.writeFileSync(readmePath, content, 'utf-8');
  console.log('Updated README.md with test statistics');
}

/**
 * Main function
 */
function main(): void {
  const testDir = path.join(__dirname, '..');

  console.log('Analyzing accessibility test files...');

  const stats = analyzeTestFiles(testDir);

  console.log(`\nFound ${stats.totalFiles} test files with ${stats.totalTests} tests`);
  console.log(`Covering ${Array.from(stats.wcagCriteriaCovered).length} WCAG criteria\n`);

  // Generate markdown summary
  const markdown = generateMarkdownSummary(stats);
  const summaryPath = path.join(testDir, 'SUMMARY.md');
  fs.writeFileSync(summaryPath, markdown, 'utf-8');
  console.log(`Created: ${summaryPath}`);

  // Generate JSON summary
  const json = generateJsonSummary(stats);
  const jsonPath = path.join(testDir, 'summary.json');
  fs.writeFileSync(jsonPath, JSON.stringify(json, null, 2), 'utf-8');
  console.log(`Created: ${jsonPath}`);

  // Update README
  updateReadme(testDir, stats);

  // Print summary
  console.log('\n' + '='.repeat(50));
  console.log('ACCESSIBILITY TEST SUMMARY');
  console.log('='.repeat(50));
  console.log(`Test Files: ${stats.totalFiles}`);
  console.log(`Total Tests: ${stats.totalTests}`);
  console.log(`Test Suites: ${stats.totalDescribeBlocks}`);
  console.log(`WCAG Criteria: ${Array.from(stats.wcagCriteriaCovered).length}`);
  console.log('='.repeat(50));

  // Print file breakdown
  console.log('\nBREAKDOWN BY FILE:');
  stats.fileStats.forEach((f) => {
    console.log(
      `  ${f.name}: ${f.testCount} tests in ${f.describeCount} suites`
    );
  });

  console.log('\nSummary files generated successfully!');
}

// Run if executed directly
if (require.main === module) {
  main();
}

export { analyzeTestFiles, generateMarkdownSummary, generateJsonSummary };
