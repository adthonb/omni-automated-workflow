#!/usr/bin/env python3
"""CLI interface for Shopee Affiliate Video & Facebook Reels Pipeline."""

import sys
from pathlib import Path

# Ensure src is importable
src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from omni_video.cli import main

if __name__ == "__main__":
    main()
