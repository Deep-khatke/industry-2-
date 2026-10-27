#!/usr/bin/env python3
"""
Top-level operational script for FCS Consortium Governance (fcs-gov).
FCS Architecture v1.2 | Phase 7 Consortium Governance.
"""

import sys
from pathlib import Path

# Add governance service package to path
project_root = Path(__file__).resolve().parent.parent
gov_src = project_root / "services" / "governance" / "src"
if str(gov_src) not in sys.path:
    sys.path.insert(0, str(gov_src))

from fcs_governance.cli import main

if __name__ == "__main__":
    sys.exit(main())
