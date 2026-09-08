#!/usr/bin/env python3
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from omni_video.subagents.transcript_generator import (
    generate_transcript,
    read_tone_reference,
    read_viral_style_profile,
)

if __name__ == "__main__":
    prod_name = sys.argv[1] if len(sys.argv) > 1 else "kai-nail-clipper"
    details = sys.argv[2] if len(sys.argv) > 2 else ""
    try:
        res = generate_transcript(product_name=prod_name, product_details=details)
        print("\n=== Transcript Generated ===")
        print(f"File: {res['outputPath']}")
    except Exception as e:
        print(f"[TranscriptGenerator Error]: {e}", file=sys.stderr)
        sys.exit(1)
