"""
conftest.py — pytest configuration.

Pytest loads this file once, before collecting any test. Its only job is
to put the repo root on `sys.path`, so test modules anywhere in the tree
can do `from src.models.quiz import …` regardless of where they live.

Without this, pytest's `rootdir` detection alone does not guarantee `src`
is importable in CI, and each test file would have to compute the repo
root itself (which is exactly the bug that broke US01 and US02 in CI).

Keep this file minimal — the M4 marker reads it.
"""

import sys
from pathlib import Path

# Repo root = the directory that contains this conftest.py.
ROOT = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))