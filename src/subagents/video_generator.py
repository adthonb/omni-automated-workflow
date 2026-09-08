#!/usr/bin/env python3
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from omni_video.subagents.video_generator import generate_video, read_learned_style

if __name__ == "__main__":
    prod_name = sys.argv[1] if len(sys.argv) > 1 else "kai-nail-clipper"
    date_arg = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        res = generate_video(product_name=prod_name, date_str=date_arg)
        print("=== Video Generation Completed ===")
        print(f"Output: {res['videoPath']}")
    except Exception as e:
        print(f"[VideoGenerator Error]: {e}", file=sys.stderr)
        sys.exit(1)
