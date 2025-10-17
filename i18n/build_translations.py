#!/usr/bin/env python3
"""
Build script to generate .qm files from .ts translation files.
Run this script to compile translations before packaging or distribution.
"""

import os
import subprocess
import sys
from pathlib import Path

def build_translations():
    """Generate .qm files from all .ts files in the i18n directory."""
    i18n_dir = Path(__file__).resolve().parent

    if not i18n_dir.exists():
        print(f"Error: {i18n_dir} directory not found!")
        return False

    # Find all .ts files
    ts_files = [f for f in i18n_dir.iterdir() if f.suffix == '.ts']

    if not ts_files:
        print(f"No .ts files found in {i18n_dir}")
        return False

    success_count = 0

    for ts_file in ts_files:
        ts_path = ts_file
        qm_file = ts_file.with_suffix('.qm').name
        qm_path = i18n_dir / qm_file

        print(f"Compiling {ts_file.name} -> {qm_file}...")

        try:
            # Run lrelease to compile the translation
            result = subprocess.run(
                ['lrelease', str(ts_path), '-qm', str(qm_path)],
                capture_output=True,
                text=True,
                check=True
            )

            if result.returncode == 0:
                print(f"✓ Successfully compiled {qm_file}")
                success_count += 1
            else:
                print(f"✗ Failed to compile {ts_file}: {result.stderr}")

        except subprocess.CalledProcessError as e:
            print(f"✗ Error compiling {ts_file}: {e.stderr}")
        except FileNotFoundError:
            print("✗ Error: lrelease command not found. Please install Qt development tools.")
            return False

    print(f"\nCompilation complete: {success_count}/{len(ts_files)} files compiled successfully")
    return success_count == len(ts_files)

if __name__ == "__main__":
    print("Building Qt translations...")
    success = build_translations()
    sys.exit(0 if success else 1)
