#!/usr/bin/env python3
"""Memory Manager Skill Runner."""

import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from omni_video.skills.memory_manager import (
    add_memory_entry,
    get_memory_path,
    get_memory_summary,
    read_memory,
    record_run_memory,
)

__all__ = [
    "get_memory_path",
    "read_memory",
    "add_memory_entry",
    "record_run_memory",
    "get_memory_summary",
]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        note_arg = sys.argv[1]
        cat_arg = sys.argv[2] if len(sys.argv) > 2 else "feedback"
        res = add_memory_entry(category=cat_arg, note=note_arg, source="cli")
        print(f"Memory added to {res['path']}:\n{res['bullet']}")
    else:
        print(get_memory_summary())
        print("\n--- Current Memory ---")
        print(read_memory(max_chars=2000))
