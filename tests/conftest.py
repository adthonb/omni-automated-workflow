"""Pytest configuration and shared fixtures for omni-video Active Phase unit tests."""

from pathlib import Path
from typing import Any
import pytest

from omni_video.config import CONFIG


@pytest.fixture
def temp_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Provide an isolated temporary workspace for file generation tests.
    
    Patches CONFIG['PATHS'] to redirect outputs to temporary directories,
    preventing any pollution of project or production assets.
    """
    transcription_dir = tmp_path / "transcription"
    detail_dir = tmp_path / "detail"
    audio_dir = tmp_path / "audio"
    memory_file = tmp_path / "MEMORY.md"
    tone_file = tmp_path / "tone.text"
    voice_file = tmp_path / "myvoice.mp3"

    transcription_dir.mkdir(parents=True, exist_ok=True)
    detail_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    tone_file.write_text("Reference tone sample for non-hard-sell Thai copywriting.", encoding="utf-8")
    voice_file.write_bytes(b"ID3_DUMMY_VOICE_TONE_DATA")

    # Patch CONFIG PATHS
    new_paths = CONFIG["PATHS"].copy()
    new_paths["TRANSCRIPTION_DIR"] = str(transcription_dir)
    new_paths["DETAIL_DIR"] = str(detail_dir)
    new_paths["AUDIO_DIR"] = str(audio_dir)
    new_paths["MEMORY_FILE"] = str(memory_file)
    new_paths["TONE_FILE"] = str(tone_file)
    new_paths["VOICE_FILE"] = str(voice_file)

    monkeypatch.setitem(CONFIG, "PATHS", new_paths)

    return {
        "root": tmp_path,
        "transcription_dir": transcription_dir,
        "detail_dir": detail_dir,
        "audio_dir": audio_dir,
        "memory_file": memory_file,
        "tone_file": tone_file,
        "voice_file": voice_file,
    }
