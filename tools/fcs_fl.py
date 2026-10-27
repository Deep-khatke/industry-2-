"""FCS-PFL CLI wrapper."""

import sys
from pathlib import Path

# Add services/federated-learning/src to sys.path
src_dir = Path(__file__).resolve().parent.parent / "services" / "federated-learning" / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from fcs_pfl.cli import main

if __name__ == "__main__":
    main()
