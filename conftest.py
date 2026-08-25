"""
Put the repo root on sys.path so `from src.schemas import ...` resolves in tests.

This exists because `python -m pytest` and `pytest` do not agree. The first puts
the working directory on sys.path; the second does not. Tests written against
the first pass locally and fail in CI, which runs the second -- which is exactly
what happened here, and is the same class of bug as everything else in this
repo: a thing that looked verified because the check ran under conditions the
real invocation does not reproduce.

pytest imports the root conftest.py before collecting anything, so this applies
under either invocation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
