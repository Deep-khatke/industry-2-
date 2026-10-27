#!/usr/bin/env python3
"""Convenience executable entry point for FCS-UDIP CLI."""

import sys
from pathlib import Path

# Add root and services/dataset_pipeline/src to path
root_dir = Path(__file__).resolve().parent.parent
pipeline_src = root_dir / "services" / "dataset_pipeline" / "src"
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(pipeline_src) not in sys.path:
    sys.path.insert(0, str(pipeline_src))

from fcs_udip.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
