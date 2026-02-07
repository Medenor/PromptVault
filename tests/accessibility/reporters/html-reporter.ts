// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import {
  Reporter,
  FullConfig,
  Suite,
  TestCase,
  TestResult,
  FullResult,
} from '@playwright/test/reporter';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Custom Playwright reporter for accessibility test results
 * Generates beautiful, interactive HTML report with:
 * - Overall accessibility score
 * - Summary by page/feature
 * - WCAG criteria mapping
 * - Color contrast details
 * - ARIA coverage
 * - Keyboard navigation results
 * - Failed test details with context
 */
class AccessibilityHTMLReporter implements Reporter {
  private reportDir = 'accessibility-report';
  private tests: TestInfo[] = [];
  private config?: FullConfig;
  private startTime = Date.now();

  onBegin(config: FullConfig): void {
    this.config = config;
    // Create report directory if it doesn't exist
    if (!fs.existsSync(this.reportDir)) {
      fs.mkdirSync(this.reportDir, { recursive: true });
    }
  }

  onTestEnd(test: TestCase, result: TestResult): void {
    const title = test.title;
    const file = test.location.file;
    const status = result.status;

    this.tests.push({
      title,
      file,
      status,
      duration: result.duration,
      error: result.error?.message || null,
      hasScreenshot: result.attachments.some((a) => a.contentType?.includes('image')),
    });
  }

  onEnd(result: FullResult): void {
    const endTime = Date.now();
    const totalTime = (endTime - this.startTime) / 1000;

    // Calculate statistics
    const stats = this.calculateStats();

    // Generate HTML report
    const html = this.generateHTML(stats, totalTime);

    // Write report
    const reportPath = path.join(this.reportDir, 'index.html');
    fs.writeFileSync(reportPath, html, 'utf-8');

    // Generate JSON summary for CI integration
    const summary = this.generateSummary(stats, totalTime);
    const summaryPath = path.join(this.reportDir, 'summary.json');
    fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2), 'utf-8');

    console.log(`\nAccessibility Report generated: ${reportPath}`);
    console.log(`Accessibility Score: ${stats.passRate.toFixed(1)}%`);
    console.log(`Tests: ${stats.passed} passed, ${stats.failed} failed, ${stats.skipped} skipped`);
  }

  private calculateStats() {
    const passed = this.tests.filter((t) => t.status === 'passed').length;
    const failed = this.tests.filter((t) => t.status === 'failed').length;
    const skipped = this.tests.filter((t) => t.status === 'skipped').length;
    const total = this.tests.length;

    // Group by page/file
    const byPage: Record<string, TestInfo[]> = {};
    this.tests.forEach((test) => {
      const pageName = path.basename(test.file, '.spec.ts');
      if (!byPage[pageName]) {
        byPage[pageName] = [];
      }
      byPage[pageName].push(test);
    });

    // Calculate WCAG criteria coverage (based on test names)
    const wcagCoverage = this.extractWCAGCoverage();

    return {
      total,
      passed,
      failed,
      skipped,
      passRate: (passed / total) * 100,
      byPage,
      wcagCoverage,
      startTime: new Date(this.startTime).toISOString(),
    };
  }

  private extractWCAGCoverage() {
    const criteriaMap: Record<string, number> = {
      '1.3.1': 0,
      '1.4.3': 0,
      '2.1.1': 0,
      '2.1.2': 0,
      '2.4.1': 0,
      '2.4.2': 0,
      '2.4.3': 0,
      '2.4.4': 0,
      '2.4.7': 0,
      '3.3.2': 0,
      '4.1.2': 0,
    };

    // Map tests to WCAG criteria by test name/file patterns
    this.tests.forEach((test) => {
      const testLower = (test.title + test.file).toLowerCase();

      if (
        testLower.includes('contrast') ||
        testLower.includes('color') ||
        testLower.includes('1.4.3')
      ) {
        criteriaMap['1.4.3']++;
      }
      if (testLower.includes('keyboard') || testLower.includes('2.1.1')) {
        criteriaMap['2.1.1']++;
      }
      if (testLower.includes('skip link') || testLower.includes('2.4.1')) {
        criteriaMap['2.4.1']++;
      }
      if (testLower.includes('tab order') || testLower.includes('2.4.3')) {
        criteriaMap['2.4.3']++;
      }
      if (testLower.includes('focus') || testLower.includes('2.4.7')) {
        criteriaMap['2.4.7']++;
      }
      if (testLower.includes('label') || testLower.includes('3.3.2')) {
        criteriaMap['3.3.2']++;
      }
      if (testLower.includes('landmark') || testLower.includes('1.3.1')) {
        criteriaMap['1.3.1']++;
      }
      if (testLower.includes('aria') || testLower.includes('4.1.2')) {
        criteriaMap['4.1.2']++;
      }
    });

    return criteriaMap;
  }

  private generateSummary(stats: any, totalTime: number) {
    return {
      timestamp: new Date().toISOString(),
      duration: totalTime,
      stats: {
        total: stats.total,
        passed: stats.passed,
        failed: stats.failed,
        skipped: stats.skipped,
        passRate: stats.passRate,
      },
      byPage: Object.entries(stats.byPage).map(([page, tests]: [string, any]) => ({
        page,
        total: tests.length,
        passed: tests.filter((t: any) => t.status === 'passed').length,
        failed: tests.filter((t: any) => t.status === 'failed').length,
      })),
      wcagCriteria: stats.wcagCoverage,
    };
  }

  private generateHTML(stats: any, totalTime: number): string {
    const failedTests = this.tests.filter((t) => t.status === 'failed');

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="PromptVault Accessibility Test Report">
    <title>Accessibility Test Report - PromptVault</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            color: #333;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 32px;
            margin-bottom: 10px;
        }

        .header p {
            font-size: 14px;
            opacity: 0.9;
        }

        .score-card {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }

        .score-item {
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }

        .score-number {
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }

        .score-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .score-item.passed .score-number { color: #10b981; }
        .score-item.failed .score-number { color: #ef4444; }
        .score-item.skipped .score-number { color: #f59e0b; }

        .main-content {
            padding: 30px;
        }

        .section {
            margin-bottom: 40px;
        }

        .section-title {
            font-size: 20px;
            font-weight: 600;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }

        .collapsible {
            cursor: pointer;
            padding: 15px;
            background: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.2s;
        }

        .collapsible:hover {
            background: #eff0f5;
        }

        .collapsible.collapsed::after {
            content: '▶';
        }

        .collapsible:not(.collapsed)::after {
            content: '▼';
        }

        .collapse-content {
            display: none;
            padding: 15px 15px;
            background: white;
            border: 1px solid #e0e0e0;
            border-top: none;
            border-radius: 0 0 6px 6px;
            margin-bottom: 10px;
        }

        .collapse-content.show {
            display: block;
        }

        .test-list {
            list-style: none;
        }

        .test-item {
            padding: 12px;
            background: #f8f9fa;
            margin-bottom: 8px;
            border-left: 4px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }

        .test-item.passed {
            border-left-color: #10b981;
            background: #f0fdf4;
        }

        .test-item.failed {
            border-left-color: #ef4444;
            background: #fef2f2;
        }

        .test-item.skipped {
            border-left-color: #f59e0b;
            background: #fffbeb;
        }

        .test-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 600;
            margin-left: 10px;
        }

        .test-badge.passed {
            background: #d1fae5;
            color: #065f46;
        }

        .test-badge.failed {
            background: #fee2e2;
            color: #7f1d1d;
        }

        .test-badge.skipped {
            background: #fef3c7;
            color: #78350f;
        }

        .wcag-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }

        .wcag-card {
            padding: 15px;
            background: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            text-align: center;
        }

        .wcag-code {
            font-size: 16px;
            font-weight: 600;
            color: #667eea;
            margin-bottom: 5px;
        }

        .wcag-count {
            font-size: 12px;
            color: #666;
        }

        .error-details {
            padding: 15px;
            background: #fef2f2;
            border-left: 4px solid #ef4444;
            border-radius: 4px;
            margin-top: 10px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #7f1d1d;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .browser-matrix {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }

        .browser-matrix th,
        .browser-matrix td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }

        .browser-matrix th {
            background: #f8f9fa;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            color: #666;
        }

        .browser-matrix tr:hover {
            background: #f8f9fa;
        }

        .status-icon {
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 8px;
        }

        .status-icon.passed {
            background: #10b981;
            color: white;
            text-align: center;
            line-height: 20px;
            font-size: 12px;
            font-weight: bold;
        }

        .status-icon.failed {
            background: #ef4444;
        }

        .status-icon.skipped {
            background: #f59e0b;
        }

        .footer {
            background: #f8f9fa;
            padding: 20px 30px;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
            text-align: center;
        }

        .progress-bar {
            width: 100%;
            height: 24px;
            background: #e0e0e0;
            border-radius: 12px;
            overflow: hidden;
            margin-top: 10px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 11px;
            font-weight: 600;
        }

        .search-box {
            margin-bottom: 20px;
            padding: 10px;
            width: 100%;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
        }

        .filter-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .filter-btn {
            padding: 8px 16px;
            background: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.2s;
        }

        .filter-btn:hover,
        .filter-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }

        @media (max-width: 768px) {
            .header {
                padding: 30px 20px;
            }

            .header h1 {
                font-size: 24px;
            }

            .score-card {
                grid-template-columns: 1fr;
                padding: 20px;
            }

            .main-content {
                padding: 20px;
            }

            .wcag-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media print {
            body {
                background: white;
            }

            .container {
                box-shadow: none;
            }

            .collapsible {
                page-break-inside: avoid;
            }

            .section {
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Accessibility Test Report</h1>
            <p>PromptVault WCAG 2.1 AA Compliance</p>
            <p style="font-size: 12px; margin-top: 10px;">Generated: ${new Date().toLocaleString()}</p>
        </div>

        <div class="score-card">
            <div class="score-item passed">
                <div class="score-number">${stats.passed}</div>
                <div class="score-label">Passed</div>
            </div>
            <div class="score-item failed">
                <div class="score-number">${stats.failed}</div>
                <div class="score-label">Failed</div>
            </div>
            <div class="score-item skipped">
                <div class="score-number">${stats.skipped}</div>
                <div class="score-label">Skipped</div>
            </div>
            <div class="score-item">
                <div class="score-number">${stats.passRate.toFixed(1)}%</div>
                <div class="score-label">Pass Rate</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${stats.passRate}%">
                        ${stats.passRate > 10 ? stats.passRate.toFixed(0) + '%' : ''}
                    </div>
                </div>
            </div>
        </div>

        <div class="main-content">
            <!-- WCAG Coverage Section -->
            <div class="section">
                <div class="section-title">WCAG 2.1 AA Criteria Coverage</div>
                <div class="wcag-grid">
                    ${this.generateWCAGCards(stats.wcagCoverage)}
                </div>
            </div>

            <!-- Page Summary Section -->
            <div class="section">
                <div class="section-title">Results by Page</div>
                ${this.generatePageSummary(stats.byPage)}
            </div>

            <!-- Failed Tests Section -->
            ${failedTests.length > 0 ? `
            <div class="section">
                <div class="section-title">Failed Tests (${failedTests.length})</div>
                <ul class="test-list">
                    ${failedTests.map((test) => `
                    <li class="test-item failed">
                        <strong>${test.title}</strong>
                        <span class="test-badge failed">FAILED</span>
                        <div style="font-size: 12px; color: #666; margin-top: 8px;">
                            ${test.file}
                        </div>
                        ${test.error ? `<div class="error-details">${this.escapeHtml(test.error)}</div>` : ''}
                    </li>
                    `).join('')}
                </ul>
            </div>
            ` : '<div class="section"><p style="color: #10b981; font-weight: 600;">All tests passed!</p></div>'}

            <!-- Execution Details -->
            <div class="section">
                <div class="section-title">Execution Details</div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    <div>
                        <div style="font-weight: 600; color: #667eea;">Total Duration</div>
                        <div style="font-size: 18px; font-weight: bold; color: #333;">${totalTime.toFixed(1)}s</div>
                    </div>
                    <div>
                        <div style="font-weight: 600; color: #667eea;">Total Tests</div>
                        <div style="font-size: 18px; font-weight: bold; color: #333;">${stats.total}</div>
                    </div>
                    <div>
                        <div style="font-weight: 600; color: #667eea;">Test Files</div>
                        <div style="font-size: 18px; font-weight: bold; color: #333;">${Object.keys(stats.byPage).length}</div>
                    </div>
                    <div>
                        <div style="font-weight: 600; color: #667eea;">Execution Time</div>
                        <div style="font-size: 14px; color: #666;">${stats.startTime}</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>PromptVault Accessibility Testing Infrastructure</p>
            <p style="font-size: 11px; margin-top: 5px;">
                Based on WCAG 2.1 AA guidelines |
                <a href="https://www.w3.org/WAI/WCAG21/quickref/" style="color: #667eea; text-decoration: none;">
                    View WCAG Standards
                </a>
            </p>
        </div>
    </div>

    <script>
        // Collapsible functionality
        document.querySelectorAll('.collapsible').forEach(btn => {
            btn.addEventListener('click', function() {
                const content = this.nextElementSibling;
                this.classList.toggle('collapsed');
                content.classList.toggle('show');
            });
        });

        // Search functionality
        const searchBox = document.querySelector('.search-box');
        if (searchBox) {
            searchBox.addEventListener('input', function() {
                const query = this.value.toLowerCase();
                document.querySelectorAll('.test-item').forEach(item => {
                    item.style.display = item.textContent.toLowerCase().includes(query) ? '' : 'none';
                });
            });
        }

        // Filter functionality
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                const filter = this.dataset.filter;
                document.querySelectorAll('.test-item').forEach(item => {
                    item.style.display = filter === 'all' || item.classList.contains(filter) ? '' : 'none';
                });
            });
        });
    </script>
</body>
</html>`;
  }

  private generateWCAGCards(wcagCoverage: Record<string, number>): string {
    const descriptions: Record<string, string> = {
      '1.3.1': 'Info and Relationships',
      '1.4.3': 'Contrast (Minimum)',
      '2.1.1': 'Keyboard',
      '2.1.2': 'No Keyboard Trap',
      '2.4.1': 'Bypass Blocks',
      '2.4.2': 'Page Titled',
      '2.4.3': 'Focus Order',
      '2.4.4': 'Link Purpose',
      '2.4.7': 'Focus Visible',
      '3.3.2': 'Labels or Instructions',
      '4.1.2': 'Name, Role, Value',
    };

    return Object.entries(wcagCoverage)
      .map(
        ([code, count]) => `
        <div class="wcag-card">
            <div class="wcag-code">${code}</div>
            <div style="font-size: 12px; color: #666; margin-bottom: 5px;">
                ${descriptions[code] || 'Unknown'}
            </div>
            <div class="wcag-count">${count} tests</div>
        </div>
        `
      )
      .join('');
  }

  private generatePageSummary(byPage: Record<string, TestInfo[]>): string {
    return Object.entries(byPage)
      .map(([pageName, tests]) => {
        const passed = tests.filter((t) => t.status === 'passed').length;
        const failed = tests.filter((t) => t.status === 'failed').length;
        const skipped = tests.filter((t) => t.status === 'skipped').length;
        const total = tests.length;
        const passRate = (passed / total) * 100;

        return `
        <div class="collapsible collapsed">
            <div>
                <strong>${pageName}</strong>
                <span style="font-size: 12px; color: #666; margin-left: 10px;">
                    ${passed}/${total} passed
                </span>
            </div>
        </div>
        <div class="collapse-content">
            <div style="margin-bottom: 10px;">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${passRate}%">
                        ${passRate.toFixed(0)}%
                    </div>
                </div>
            </div>
            <table class="browser-matrix">
                <tr>
                    <th>Status</th>
                    <th>Count</th>
                </tr>
                <tr>
                    <td><span class="status-icon passed">✓</span>Passed</td>
                    <td>${passed}</td>
                </tr>
                <tr>
                    <td><span class="status-icon failed">✕</span>Failed</td>
                    <td>${failed}</td>
                </tr>
                <tr>
                    <td><span class="status-icon skipped">−</span>Skipped</td>
                    <td>${skipped}</td>
                </tr>
            </table>
        </div>
        `;
      })
      .join('');
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

interface TestInfo {
  title: string;
  file: string;
  status: string;
  duration: number;
  error: string | null;
  hasScreenshot: boolean;
}

export default AccessibilityHTMLReporter;
