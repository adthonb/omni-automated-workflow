#!/usr/bin/env python3
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from omni_video.subagents.tts_generator import (
    extract_script_from_markdown,
    generate_text_to_speech,
)

if __name__ == "__main__":
    prod_name = sys.argv[1] if len(sys.argv) > 1 else "kai-nail-clipper"
    try:
        res = generate_text_to_speech(product_name=prod_name)
        print("=== Text-To-Speech Subagent Completed ===")
        print(f"Audio Output: {res['audioPath']}")
    except Exception as e:
        print(f"[TTSGenerator Error]: {e}", file=sys.stderr)
        sys.exit(1)
