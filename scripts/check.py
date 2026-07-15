"""Run the full local check suite: Ruff, pytest, and Playwright.

Usage:
    python scripts/check.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STEPS = [
    ("Ruff", [sys.executable, "-m", "ruff", "check", "."]),
    ("pytest", [sys.executable, "-m", "pytest", "tests/", "--ignore=tests/test_ui_playwright.py"]),
    ("Playwright", [sys.executable, "-m", "pytest", "tests/test_ui_playwright.py"]),
]


def main():
    failures = []
    for name, cmd in STEPS:
        print(f"\n=== {name} ===")
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            failures.append(name)

    print()
    if failures:
        print(f"FAILED: {', '.join(failures)}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
