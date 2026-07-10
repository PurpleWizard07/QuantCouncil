"""Pytest bootstrap for the API package.

Inserts the apps/api directory itself into sys.path so that ``import app``
works when pytest is executed from the repository root (root pytest.ini uses
``testpaths = apps/api packages``).
"""

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))
