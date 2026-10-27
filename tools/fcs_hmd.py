#!/usr/bin/env python3
"""Convenience executable wrapper for fcs-hmd CLI."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ML_SRC = ROOT_DIR / "services" / "ml_training" / "src"
API_SRC = ROOT_DIR / "services" / "api" / "src"

for p in [str(ROOT_DIR), str(ML_SRC), str(API_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fcs_ml.hmd.cli import main

if __name__ == "__main__":
    sys.exit(main())
