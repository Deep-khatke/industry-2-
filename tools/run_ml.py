#!/usr/bin/env python3
"""Launcher for the FCS Phase 3 Machine Learning CLI."""

import sys
from pathlib import Path

# Add project root and package directories to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
ML_SRC = ROOT_DIR / "services" / "ml_training" / "src"
DATASET_SRC = ROOT_DIR / "services" / "dataset_pipeline" / "src"

for p in [str(ROOT_DIR), str(ML_SRC), str(DATASET_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fcs_ml.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
