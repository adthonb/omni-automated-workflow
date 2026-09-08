#!/usr/bin/env python3
"""Skill: Memory & Continuous Self-Improvement Manager.

Loads persistent memory from MEMORY.md and records new learnings, tone nuances,
scraper quirks, and user feedback after each run to improve subsequent prompts.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from ..config import CONFIG
except (ImportError, ValueError):
    from omni_video.config import CONFIG


def get_memory_path() -> Path:
    """Return the absolute path to MEMORY.md."""
    if "PATHS" in CONFIG and "MEMORY_FILE" in CONFIG["PATHS"]:
        return Path(CONFIG["PATHS"]["MEMORY_FILE"])
    root = Path(CONFIG.get("PROJECT_ROOT", Path(__file__).resolve().parent.parent.parent.parent))
    return root / "MEMORY.md"


def read_memory(max_chars: int = 5000) -> str:
    """Read contents of MEMORY.md for inclusion in subagent prompts."""
    mem_path = get_memory_path()
    if not mem_path.exists():
        return ""
    try:
        content = mem_path.read_text(encoding="utf-8").strip()
        if len(content) > max_chars:
            # Keep top overview and the most recent entries
            return content[:max_chars] + "\n\n...[Memory truncated for length]..."
        return content
    except Exception as err:
        print(f"[MemoryManager] Warning: failed to read memory at {mem_path}: {err}")
        return ""


CATEGORY_HEADERS = {
    "copywriting": "## 1. High-Converting Copywriting Rules (Learned)",
    "audio": "## 2. Audio & Voiceover Nuances (TTS)",
    "tts": "## 2. Audio & Voiceover Nuances (TTS)",
    "niche": "## 3. Product & Niche Insights",
    "product": "## 3. Product & Niche Insights",
    "platform": "## 4. Platform & Scraper Quirks",
    "scraper": "## 4. Platform & Scraper Quirks",
    "feedback": "## 5. User Feedback & Evolution Log",
}


def add_memory_entry(category: str, note: str, source: str = "user") -> dict[str, Any]:
    """
    Append a new memory note or rule to the designated section in MEMORY.md.
    """
    mem_path = get_memory_path()
    cat_key = category.lower().strip()
    target_header = CATEGORY_HEADERS.get(cat_key, "## 5. User Feedback & Evolution Log")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    bullet = f"- **[{timestamp}] ({source})**: {note.strip()}"

    if not mem_path.exists():
        content = f"# Omni Video Memory & Continuous Self-Improvement\n\n{target_header}\n{bullet}\n"
        mem_path.write_text(content, encoding="utf-8")
        return {"status": "created", "path": str(mem_path), "bullet": bullet}

    existing = mem_path.read_text(encoding="utf-8")

    # Find the target section and append the bullet
    if target_header in existing:
        pattern = re.compile(rf"({re.escape(target_header)}[\s\S]*?)(?=\n---\n|\n## |\Z)", re.IGNORECASE)
        match = pattern.search(existing)
        if match:
            section_content = match.group(1).rstrip()
            updated_section = f"{section_content}\n{bullet}"
            updated_all = existing[:match.start()] + updated_section + existing[match.end():]
        else:
            updated_all = existing.rstrip() + f"\n\n{bullet}\n"
    else:
        updated_all = existing.rstrip() + f"\n\n---\n\n{target_header}\n{bullet}\n"

    mem_path.write_text(updated_all, encoding="utf-8")
    return {"status": "updated", "path": str(mem_path), "bullet": bullet}


def record_run_memory(
    product_name: str,
    product_title: str | None = None,
    url: str | None = None,
    transcript_path: str | None = None,
    audio_path: str | None = None,
    feedback: str | None = None,
    learnings: list[str] | None = None,
) -> dict[str, Any]:
    """
    Record completed run metadata and learnings into MEMORY.md to improve subsequent prompts.
    """
    mem_path = get_memory_path()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    clean_title = (product_title or product_name).strip()

    lines = [f"- **[{timestamp}] Pipeline Run: `{product_name}`**"]
    if url:
        lines.append(f"  - Source URL: {url}")
    if clean_title != product_name:
        lines.append(f"  - Title: {clean_title}")
    if transcript_path:
        lines.append(f"  - Transcript: `{Path(transcript_path).name}`")
    if audio_path:
        lines.append(f"  - Audio: `{Path(audio_path).name}`")
    if learnings:
        for item in learnings:
            lines.append(f"  - Learned: {item}")
    if feedback:
        lines.append(f"  - User Feedback / Correction: {feedback.strip()}")

    log_entry = "\n".join(lines)

    target_header = "## 5. User Feedback & Evolution Log"
    if not mem_path.exists():
        mem_path.write_text(f"# Omni Video Memory & Continuous Self-Improvement\n\n{target_header}\n{log_entry}\n", encoding="utf-8")
        return {"status": "created", "path": str(mem_path), "summary": log_entry}

    existing = mem_path.read_text(encoding="utf-8")
    if target_header in existing:
        pattern = re.compile(rf"({re.escape(target_header)}[\s\S]*?)(?=\n---\n|\n## |\Z)", re.IGNORECASE)
        match = pattern.search(existing)
        if match:
            section_content = match.group(1).rstrip()
            updated_section = f"{section_content}\n{log_entry}"
            updated_all = existing[:match.start()] + updated_section + existing[match.end():]
        else:
            updated_all = existing.rstrip() + f"\n\n{log_entry}\n"
    else:
        updated_all = existing.rstrip() + f"\n\n---\n\n{target_header}\n{log_entry}\n"

    mem_path.write_text(updated_all, encoding="utf-8")
    return {"status": "updated", "path": str(mem_path), "summary": log_entry}


def get_memory_summary() -> str:
    """Return a short summary of memory entries."""
    mem_path = get_memory_path()
    if not mem_path.exists():
        return "No memory file found."
    content = mem_path.read_text(encoding="utf-8")
    rules_count = len(re.findall(r"^\s*-\s+", content, re.MULTILINE))
    sections = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)
    return f"Memory File: {mem_path.name} | {len(sections)} sections | {rules_count} learned rules & logs"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        note_arg = sys.argv[1]
        cat_arg = sys.argv[2] if len(sys.argv) > 2 else "feedback"
        res = add_memory_entry(category=cat_arg, note=note_arg, source="cli")
        print(f"Memory added to {res['path']}:\n{res['bullet']}")
    else:
        print(get_memory_summary())
        print("\n--- Current Memory ---")
        print(read_memory(max_chars=2000))
