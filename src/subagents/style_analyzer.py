#!/usr/bin/env python3
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from omni_video.subagents.style_analyzer import analyze_viral_seller_style

if __name__ == "__main__":
    sample_arg = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        res = analyze_viral_seller_style(video_path=sample_arg)
        print("\n=== Viral Seller Style Analysis Completed ===")
        print(f"Style Profile: {res['mdPath']}")
    except Exception as e:
        print(f"[StyleAnalyzer Error]: {e}", file=sys.stderr)
        sys.exit(1)
