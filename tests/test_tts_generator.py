"""Unit tests for Phase 1 Active Agent: Text-To-Speech (TTS) Generator."""

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from omni_video.subagents.tts_generator import (
    extract_script_from_markdown,
    generate_text_to_speech,
)


class TestTTSScriptExtraction:
    """Tests for extracting the voiceover script from markdown transcripts."""

    def test_extract_script_from_markup_section(self):
        md = """# Transcript: test
## 1. Spoken Transcript with Speech Markup (For Gemini TTS)
[excited] สวัสดีครับทุกคน วันนี้มีของดีมาแนะนำ [short pause]
## 2. Plain Voiceover Script
สวัสดีครับทุกคน วันนี้มีของดีมาแนะนำ
"""
        script = extract_script_from_markdown(md)
        assert "[excited]" in script
        assert "สวัสดีครับทุกคน" in script
        assert "Plain Voiceover Script" not in script

    def test_extract_script_from_plain_section_if_markup_missing(self):
        md = """# Transcript: test
## 2. Plain Voiceover Script (Clean Text)
สวัสดีครับทุกคน วันนี้มีของดีมาแนะนำ
"""
        script = extract_script_from_markdown(md)
        assert "สวัสดีครับทุกคน" in script

    def test_extract_script_fallback_strips_headers(self):
        md = """# Header 1
## Header 2
นี่คือสคริปต์แบบไม่มีหัวข้อมาตรฐาน
"""
        script = extract_script_from_markdown(md)
        assert "นี่คือสคริปต์แบบไม่มีหัวข้อมาตรฐาน" in script
        assert "#" not in script


class TestGenerateTextToSpeech:
    """Tests for generate_text_to_speech subagent execution."""

    def test_missing_both_product_name_and_transcript_raises(self):
        with pytest.raises(ValueError, match="Either product_name or transcript_path is required"):
            generate_text_to_speech()

    def test_missing_transcript_file_raises_file_not_found(self, temp_workspace):
        with pytest.raises(FileNotFoundError, match="Transcript file not found"):
            generate_text_to_speech(product_name="non-existent-item")

    @patch("omni_video.subagents.tts_generator.convert_pcm_to_mp3")
    @patch("omni_video.subagents.tts_generator.get_gemini_client")
    def test_generate_tts_success_with_audio_stream(
        self, mock_get_client, mock_convert_pcm, temp_workspace
    ):
        # Create transcript file
        t_dir = temp_workspace["transcription_dir"]
        t_file = t_dir / "kai-nail-clipper.md"
        t_file.write_text(
            "## 1. Spoken Transcript\n[curious tone] มันจะมีของใช้ชิ้นหนึ่ง...",
            encoding="utf-8",
        )

        # Mock client and responses
        mock_client = MagicMock()
        mock_upload = MagicMock()
        mock_upload.uri = "https://gemini.api/files/voice123"
        mock_client.files.upload.return_value = mock_upload

        # Prepare fake audio candidate
        fake_audio_bytes = b"RIFF_WAV_AUDIO_DATA_FOR_TESTING"
        fake_b64 = base64.b64encode(fake_audio_bytes).decode("ascii")

        mock_part = MagicMock()
        mock_part.inline_data.data = fake_b64
        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]

        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        # Mock convert_pcm_to_mp3 to write target file
        def fake_pcm_convert(audio_data, out_path, **kwargs):
            Path(out_path).write_bytes(b"FAKE_MP3_OUTPUT")

        mock_convert_pcm.side_effect = fake_pcm_convert

        res = generate_text_to_speech(product_name="kai-nail-clipper")

        assert res["productName"] == "kai-nail-clipper"
        assert Path(res["audioPath"]).exists()
        assert Path(res["audioPath"]).read_bytes() == b"FAKE_MP3_OUTPUT"
        mock_convert_pcm.assert_called_once()

    @patch("omni_video.subagents.tts_generator.with_retry", side_effect=Exception("TTS API quota exceeded"))
    @patch("omni_video.subagents.tts_generator.get_gemini_client")
    def test_generate_tts_api_error_fallback_copies_reference(
        self, mock_get_client, mock_retry, temp_workspace
    ):
        t_dir = temp_workspace["transcription_dir"]
        t_file = t_dir / "fallback-product.md"
        t_file.write_text("## 1. Spoken Transcript\nสคริปต์สำรอง", encoding="utf-8")

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        res = generate_text_to_speech(product_name="fallback-product")

        assert Path(res["audioPath"]).exists()
        assert Path(res["audioPath"]).stat().st_size > 0
