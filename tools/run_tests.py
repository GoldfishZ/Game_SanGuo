"""Run this project's dependency-free, pytest-style function tests."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import inspect
import io
from pathlib import Path
import sys
import traceback


def run_tests(verbose: bool = False) -> int:
    root = Path(__file__).resolve().parents[1]
    tests_dir = root / "tests"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    passed = failed = skipped = 0
    failures = []
    for path in sorted(tests_dir.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(f"_project_test_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        try:
            with contextlib.redirect_stdout(io.StringIO() if not verbose else sys.stdout):
                spec.loader.exec_module(module)
        except Exception:
            failed += 1
            failures.append((path.name, "<import>", traceback.format_exc()))
            continue

        for name, function in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            if inspect.signature(function).parameters:
                skipped += 1
                continue
            try:
                with contextlib.redirect_stdout(io.StringIO() if not verbose else sys.stdout):
                    function()
                passed += 1
            except Exception:
                failed += 1
                failures.append((path.name, name, traceback.format_exc()))

    print(f"tests: {passed} passed, {failed} failed, {skipped} skipped")
    for filename, name, details in failures:
        print(f"\nFAIL {filename}::{name}\n{details}")
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run_tests(args.verbose))
