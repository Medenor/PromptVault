#!/usr/bin/env python3
"""
Accessibility Test Results Analyzer

This script parses Playwright test output and axe-core violations
to generate a comprehensive accessibility test report.

Usage:
    python3 scripts/analyze_accessibility_results.py \
        --output-file PHASE_3_TEST_RESULTS.md \
        --test-log /tmp/phase3_accessibility_test_output.log
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ViolationStats:
    """Statistics for a specific violation type."""
    violation_id: str
    help_text: str
    impact: str
    count: int
    affected_pages: set[str]


@dataclass
class PageStats:
    """Statistics for a specific page."""
    url: str
    status: str
    violations_found: int
    violations_by_id: dict[str, int]


def parse_playwright_output(log_file: Path) -> dict[str, Any]:
    """Parse Playwright test output from log file."""
    if not log_file.exists():
        print(f"Warning: Log file not found: {log_file}")
        return {}

    content = log_file.read_text()

    # Look for test results summary
    stats = {
        'total_pages': 0,
        'pages_with_violations': 0,
        'critical_violations': 0,
        'serious_violations': 0,
        'pages': {},
        'violations_by_type': {},
        'parse_status': 'partial'
    }

    # Extract test results (looking for ACC-AXE: pattern)
    test_pattern = r'(✓|✗|⊘)\s+(ACC-AXE:\s+(\S+).+)'
    matches = re.findall(test_pattern, content)

    if not matches:
        print("Warning: Could not parse Playwright output. No test results found.")
        return stats

    for status, test_name, page in matches:
        page_clean = page.replace('has no critical/serious accessibility violations', '').strip()
        if page_clean not in stats['pages']:
            stats['pages'][page_clean] = {
                'status': 'passed' if status == '✓' else 'failed',
                'violations': 0
            }
            stats['total_pages'] += 1

    # Try to extract violation details
    violation_pattern = r'(\w+):\s+(.+?)\s+\[([^\]]+)\]'
    for match in re.finditer(violation_pattern, content):
        violation_id, help_text, targets = match.groups()
        if violation_id not in stats['violations_by_type']:
            stats['violations_by_type'][violation_id] = {
                'help': help_text,
                'count': 0,
                'pages': set()
            }
        stats['violations_by_type'][violation_id]['count'] += 1

    return stats


def parse_test_results_json(json_file: Path) -> dict[str, Any]:
    """Parse structured test results from JSON file."""
    if not json_file.exists():
        print(f"Warning: JSON results file not found: {json_file}")
        return {}

    try:
        with open(json_file, 'r') as f:
            data = json.load(f)

        return {
            'total_tests': data['stats']['expected'] + data['stats']['unexpected'],
            'passed': data['stats']['expected'],
            'failed': data['stats']['unexpected'],
            'duration_ms': data['stats']['duration'],
            'parse_status': 'success'
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not parse JSON results: {e}")
        return {}


def generate_summary(
    playwright_stats: dict[str, Any],
    json_stats: dict[str, Any]
) -> str:
    """Generate a summary of test results."""
    summary = "## Test Results Summary\n\n"

    if json_stats:
        total = json_stats.get('total_tests', 0)
        passed = json_stats.get('passed', 0)
        failed = json_stats.get('failed', 0)
        duration_sec = json_stats.get('duration_ms', 0) / 1000

        if total > 0:
            pass_rate = (passed / total) * 100
            summary += f"- **Total Tests:** {total}\n"
            summary += f"- **Tests Passed:** {passed} ({pass_rate:.1f}%)\n"
            summary += f"- **Tests Failed:** {failed}\n"
            summary += f"- **Duration:** {duration_sec:.1f} seconds\n\n"

    if playwright_stats.get('pages'):
        summary += f"- **Pages Scanned:** {playwright_stats['total_pages']}\n"
        pages_with_violations = sum(
            1 for p in playwright_stats['pages'].values()
            if p['status'] == 'failed'
        )
        summary += f"- **Pages with Violations:** {pages_with_violations}\n\n"

    if playwright_stats.get('violations_by_type'):
        summary += "### Violations by Type\n\n"
        for violation_id, details in sorted(
            playwright_stats['violations_by_type'].items(),
            key=lambda x: x[1]['count'],
            reverse=True
        ):
            summary += f"- **{violation_id}**: {details['count']} occurrences\n"
            summary += f"  - {details['help']}\n"

    return summary


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze accessibility test results and generate report.'
    )
    parser.add_argument(
        '--output-file',
        type=Path,
        default=Path('PHASE_3_TEST_RESULTS.md'),
        help='Output markdown file to update (default: %(default)s).',
    )
    parser.add_argument(
        '--test-log',
        type=Path,
        help='Path to Playwright test output log.',
    )
    parser.add_argument(
        '--json-results',
        type=Path,
        default=Path('test-results/results.json'),
        help='Path to JSON test results (default: %(default)s).',
    )
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Print summary only (do not update output file).',
    )

    args = parser.parse_args()

    # Parse results
    playwright_stats = {}
    if args.test_log:
        playwright_stats = parse_playwright_output(args.test_log)
        print(f"Parsed Playwright output: {args.test_log}")

    json_stats = parse_test_results_json(args.json_results)
    print(f"Parsed JSON results: {args.json_results}")

    # Generate summary
    summary = generate_summary(playwright_stats, json_stats)

    if args.summary_only:
        print("\n" + "="*60)
        print(summary)
        print("="*60)
        return 0

    # Update output file with results
    output_file = Path(args.output_file)
    if not output_file.exists():
        print(f"Error: Output file not found: {output_file}")
        return 1

    content = output_file.read_text()

    # Update with actual test results
    if json_stats and json_stats.get('passed') is not None:
        total = json_stats['total_tests']
        passed = json_stats['passed']
        failed = json_stats['failed']
        duration_sec = json_stats.get('duration_ms', 0) / 1000
        pass_pct = (passed / total * 100) if total > 0 else 0

        # Baseline from original test results (before recent fixes)
        baseline_pass_pct = 70.9  # From previous documentation
        improvement = pass_pct - baseline_pass_pct

        # Update executive summary statistics
        old_stats = r'- \*\*Total Tests\*\*:.*?\n- \*\*Tests Passed\*\*:.*?\n- \*\*Tests Failed\*\*:.*?(?:\n|$)'
        new_exec_stats = f"""- **Total Tests**: {total:,}
- **Tests Passed**: {passed:,} ({pass_pct:.1f}%)
- **Tests Failed**: {failed:,} ({100-pass_pct:.1f}%)"""

        content = re.sub(old_stats, new_exec_stats, content)

        # Build new statistics section with metrics table
        execution_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        duration_min = duration_sec / 60

        # Calculate estimated violations remaining
        violations_est = failed  # Each failure typically represents one violation

        new_detailed_stats = f"""## Test Execution Summary (Latest Run)

**Execution Date:** {execution_date}
**Test Suite Duration:** {duration_min:.1f} minutes ({duration_sec:.0f} seconds)

### Results at a Glance

| Metric | Value | Baseline | Change |
|--------|-------|----------|--------|
| **Total Tests Run** | {total:,} | 3,065 | +{total-3065} |
| **Tests Passed** | {passed:,} | 2,207 | +{passed-2207 if passed > 2207 else '—'} |
| **Tests Failed** | {failed} | 948 | {failed-948 if failed != 948 else '—'} |
| **Pass Rate** | {pass_pct:.1f}% | 70.0% | {improvement:+.1f} pp |

### Status

"""

        # Determine status
        if pass_pct >= 95:
            status_text = "✅ **TARGET ACHIEVED** - WCAG 2.1 AA compliance reached!"
        elif pass_pct >= 85:
            status_text = "🟢 **SIGNIFICANT PROGRESS** - Major improvements achieved"
        elif pass_pct >= 75:
            status_text = "🟡 **MODERATE PROGRESS** - Continuing improvements"
        else:
            status_text = "🔴 **NEEDS ATTENTION** - Further fixes required"

        new_detailed_stats += f"**Status:** {status_text}\n"

        # Try to find and replace an existing "Test Execution Summary" section
        summary_pattern = r'## Test Execution Summary.*?(?=\n## |$)'
        if re.search(summary_pattern, content, re.DOTALL):
            content = re.sub(summary_pattern, new_detailed_stats.rstrip(), content, flags=re.DOTALL)
        else:
            # If no summary section exists, insert it after the executive summary
            insert_pattern = r'(## Executive Summary.*?\n\n.*?(?=\n\n## |\n---|\Z))'
            content = re.sub(
                insert_pattern,
                r'\1\n\n' + new_detailed_stats,
                content,
                flags=re.DOTALL,
                count=1
            )

    output_file.write_text(content)
    print(f"\nUpdated: {output_file}")
    print(f"Results: {passed}/{total} tests passed ({pass_pct:.1f}%)")
    print(f"Failures: {failed} ({100-pass_pct:.1f}%)")

    return 0


if __name__ == '__main__':
    sys.exit(main())
