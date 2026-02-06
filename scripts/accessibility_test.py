#!/usr/bin/env python3
"""
Local accessibility test runner for PromptVault.

This script runs Playwright + axe-core accessibility scans against core pages.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Run accessibility tests with Playwright + axe-core."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8003",
        help="Base URL to scan (default: %(default)s).",
    )
    parser.add_argument(
        "--page",
        action="append",
        dest="pages",
        default=[],
        help="Page route to scan (repeatable), e.g. --page /auth/login",
    )
    parser.add_argument(
        "--project",
        default="chromium",
        help="Playwright project name (default: %(default)s).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Use verbose list reporter output.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of Playwright workers (default: %(default)s).",
    )
    return parser.parse_args()


def run_accessibility_tests(args: argparse.Namespace) -> int:
    """Execute Playwright accessibility tests and return process exit code."""
    env = os.environ.copy()
    env["ACCESSIBILITY_BASE_URL"] = args.base_url
    # Use an already running dev environment instead of launching run_web.py
    env["ACCESSIBILITY_EXTERNAL_SERVER"] = "1"
    if args.pages:
        env["ACCESSIBILITY_PAGES"] = ",".join(args.pages)

    command = [
        "npx",
        "playwright",
        "test",
        "scripts/playwright_accessibility_tests.ts",
        "--project",
        args.project,
        "--workers",
        str(args.workers),
    ]

    if args.verbose:
        command.extend(["--reporter", "list"])
    if args.headed:
        command.append("--headed")

    print("Running accessibility tests...")
    print(f"Base URL: {env['ACCESSIBILITY_BASE_URL']}")
    if args.pages:
        print(f"Pages: {', '.join(args.pages)}")
    print(f"Project: {args.project}")
    print(f"Workers: {args.workers}")
    print("Command:", " ".join(command))

    result = subprocess.run(command, env=env, check=False)
    return result.returncode


def main() -> int:
    """Entry point."""
    args = parse_args()
    return run_accessibility_tests(args)


if __name__ == "__main__":
    sys.exit(main())
