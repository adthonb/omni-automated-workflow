#!/usr/bin/env python3
"""Orchestrator runner delegating to omni_video.orchestrator."""

import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from omni_video.orchestrator import (
    extract_caption_from_transcript,
    run_interactive_command,
    run_orchestration_pipeline,
)

__all__ = [
    "extract_caption_from_transcript",
    "run_orchestration_pipeline",
    "run_interactive_command",
]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prod_arg = sys.argv[1]
        detail_arg = sys.argv[2] if len(sys.argv) > 2 else ""
        try:
            is_url = prod_arg.startswith("http://") or prod_arg.startswith("https://") or "shopee.co.th" in prod_arg
            run_orchestration_pipeline(
                shopee_url=prod_arg if is_url else None,
                product_name=prod_arg if not is_url else None,
                product_details=detail_arg,
            )
        except Exception as e:
            print(f"[Orchestrator Error]: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        run_interactive_command()
