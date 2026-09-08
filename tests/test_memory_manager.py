"""Unit tests for Phase 1 Active Skill: Memory Manager & Continuous Improvement."""

from pathlib import Path
import pytest

from omni_video.skills.memory_manager import (
    add_memory_entry,
    get_memory_path,
    get_memory_summary,
    read_memory,
    record_run_memory,
)


class TestMemoryManager:
    """Tests for memory reading, writing, and log recording."""

    def test_get_memory_path(self, temp_workspace):
        path = get_memory_path()
        assert path == temp_workspace["memory_file"]

    def test_read_memory_empty_when_file_not_exist(self, temp_workspace):
        # File has not been created yet
        content = read_memory()
        assert content == ""

    def test_read_memory_existing_file(self, temp_workspace):
        mem_file = temp_workspace["memory_file"]
        mem_file.write_text("# Test Memory\n- Rule 1: Always highlight crispiness", encoding="utf-8")

        content = read_memory()
        assert "- Rule 1: Always highlight crispiness" in content

    def test_read_memory_truncation(self, temp_workspace):
        mem_file = temp_workspace["memory_file"]
        long_text = "A" * 6000
        mem_file.write_text(long_text, encoding="utf-8")

        truncated = read_memory(max_chars=100)
        assert len(truncated) < 200
        assert "...[Memory truncated for length]..." in truncated

    def test_add_memory_entry_creates_new_file(self, temp_workspace):
        mem_file = temp_workspace["memory_file"]
        assert not mem_file.exists()

        res = add_memory_entry(category="copywriting", note="Keep the hook under 5 seconds", source="test")
        assert res["status"] == "created"
        assert mem_file.exists()

        saved_text = mem_file.read_text(encoding="utf-8")
        assert "## 1. High-Converting Copywriting Rules" in saved_text
        assert "Keep the hook under 5 seconds" in saved_text
        assert "(test)" in saved_text

    def test_add_memory_entry_appends_to_existing_category(self, temp_workspace):
        mem_file = temp_workspace["memory_file"]
        initial_content = """# Omni Video Memory & Continuous Self-Improvement

## 1. High-Converting Copywriting Rules (Learned)
- **[2026-09-08 10:00] (user)**: Initial hook rule

---

## 2. Audio & Voiceover Nuances (TTS)
- **[2026-09-08 10:00] (user)**: Pacing control
"""
        mem_file.write_text(initial_content, encoding="utf-8")

        add_memory_entry(category="copywriting", note="Second hook rule for snacks", source="user")
        add_memory_entry(category="audio", note="Insert pauses around numbers", source="user")

        updated = mem_file.read_text(encoding="utf-8")
        assert "Initial hook rule" in updated
        assert "Second hook rule for snacks" in updated
        assert "Insert pauses around numbers" in updated

    def test_add_memory_entry_unknown_category_defaults_to_feedback(self, temp_workspace):
        mem_file = temp_workspace["memory_file"]
        add_memory_entry(category="unrecognized_cat", note="General system observation", source="auto")

        content = mem_file.read_text(encoding="utf-8")
        assert "## 5. User Feedback & Evolution Log" in content
        assert "General system observation" in content

    def test_record_run_memory_creates_detailed_log(self, temp_workspace):
        mem_file = temp_workspace["memory_file"]
        res = record_run_memory(
            product_name="pork-chili",
            product_title="น้ำพริกกากหมูแท้ กรอบนาน",
            url="https://shopee.co.th/product-i.1.2",
            transcript_path=str(temp_workspace["transcription_dir"] / "pork-chili.md"),
            audio_path=str(temp_workspace["audio_dir"] / "pork-chili.mp3"),
            feedback="Great pacing and sound effects",
            learnings=["Highlight daily freshness", "Sound of crunch is viral"],
        )

        assert res["status"] == "created"
        saved = mem_file.read_text(encoding="utf-8")
        assert "Pipeline Run: `pork-chili`" in saved
        assert "Title: น้ำพริกกากหมูแท้ กรอบนาน" in saved
        assert "Source URL: https://shopee.co.th/product-i.1.2" in saved
        assert "Transcript: `pork-chili.md`" in saved
        assert "Audio: `pork-chili.mp3`" in saved
        assert "Learned: Highlight daily freshness" in saved
        assert "Learned: Sound of crunch is viral" in saved
        assert "User Feedback / Correction: Great pacing and sound effects" in saved

    def test_get_memory_summary(self, temp_workspace):
        mem_file = temp_workspace["memory_file"]
        content = """# Memory
## Section 1
- Rule 1
- Rule 2
## Section 2
- Rule 3
"""
        mem_file.write_text(content, encoding="utf-8")
        summary = get_memory_summary()
        assert "MEMORY.md" in summary
        assert "2 sections" in summary
        assert "3 learned rules & logs" in summary
