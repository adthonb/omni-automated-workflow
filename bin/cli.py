#!/usr/bin/env python3
"""CLI executable entry point."""

import sys
from pathlib import Path

# Add src to sys.path
project_root = Path(__file__).resolve().parent.parent
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from omni_video.cli import main

if __name__ == "__main__":
    main()
