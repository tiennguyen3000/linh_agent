#!/usr/bin/env python3
"""Linh process entry point (invoked by bin/linh on Linh's venv)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "core"), str(ROOT)]  # core runtime first, then the Linh package

from linh.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
