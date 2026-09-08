#!/usr/bin/env python3
import json
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from omni_video.skills.fb_reels_publisher import (
    finish_and_publish_reel,
    get_reel_status,
    publish_facebook_reel,
    start_reel_upload_session,
    upload_reel_video_binary,
)

__all__ = [
    "start_reel_upload_session",
    "upload_reel_video_binary",
    "finish_and_publish_reel",
    "get_reel_status",
    "publish_facebook_reel",
]

if __name__ == "__main__":
    target_video = sys.argv[1] if len(sys.argv) > 1 else ""
    target_desc = sys.argv[2] if len(sys.argv) > 2 else "รีวิวสินค้า Shopee ยอดฮิต พิกัดในคอมเมนต์ 👇"

    if not target_video:
        print("Usage: python fb_reels_publisher.py <path-to-video.mp4> [description]", file=sys.stderr)
        sys.exit(1)

    try:
        res = publish_facebook_reel(video_path=target_video, description=target_desc)
        print("\n=== Reel Publishing Process Finished ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[FBReelsSkill Error]: {e}", file=sys.stderr)
        sys.exit(1)
