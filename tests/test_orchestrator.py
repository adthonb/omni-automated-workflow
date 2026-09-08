"""Unit tests for Phase 1 Active Command: Orchestrator Pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from omni_video.orchestrator import (
    extract_caption,
    extract_caption_from_transcript,
    run_orchestration_pipeline,
)


class TestCaptionExtraction:
    """Tests for extracting post caption from detail and transcript files."""

    def test_extract_caption_from_detail_file(self, tmp_path):
        detail_file = tmp_path / "detail.md"
        detail_file.write_text("""# Details
## 2. Facebook Reels Post Caption
🔥 ของเด็ดน่าใช้ #ShopeeTH
👇 พิกัดในคอมเมนต์
""", encoding="utf-8")

        caption = extract_caption(detail_path=str(detail_file))
        assert "🔥 ของเด็ดน่าใช้ #ShopeeTH" in caption
        assert "👇 พิกัดในคอมเมนต์" in caption

    def test_extract_caption_from_transcript_fallback(self, tmp_path):
        transcript_file = tmp_path / "transcript.md"
        transcript_file.write_text("""# Transcript
## 4. Facebook Reels Post Caption
แคปชั่นสำรองจากทรานสคริปต์
""", encoding="utf-8")

        caption = extract_caption(transcript_path=str(transcript_file))
        assert "แคปชั่นสำรองจากทรานสคริปต์" in caption

    def test_extract_caption_backwards_compatible_helper(self, tmp_path):
        t_file = tmp_path / "test.md"
        t_file.write_text("## Facebook Reels Post Caption\nแคปชั่นสั้น", encoding="utf-8")
        caption = extract_caption_from_transcript(str(t_file))
        assert caption == "แคปชั่นสั้น"


class TestOrchestratorPipeline:
    """Tests for run_orchestration_pipeline execution contracts and fail-closed guardrails."""

    def test_empty_inputs_raises_value_error(self):
        with pytest.raises(ValueError, match="Execution Contract Violation"):
            run_orchestration_pipeline()

    @patch("omni_video.orchestrator.record_run_memory")
    @patch("omni_video.orchestrator.generate_text_to_speech")
    @patch("omni_video.orchestrator.generate_transcript")
    @patch("omni_video.orchestrator.scrape_shopee_product")
    def test_orchestration_pipeline_phase1_shopee_url_success(
        self,
        mock_scrape,
        mock_transcript,
        mock_tts,
        mock_record_memory,
        temp_workspace,
    ):
        # Setup files created by steps
        t_path = str(temp_workspace["transcription_dir"] / "kai-clipper.md")
        d_path = str(temp_workspace["detail_dir"] / "kai-clipper.md")
        a_path = str(temp_workspace["audio_dir"] / "kai-clipper.mp3")

        Path(t_path).write_text("## 1. Spoken Transcript\nสคริปต์", encoding="utf-8")
        Path(d_path).write_text("## 2. Facebook Reels Post Caption\nแคปชั่น", encoding="utf-8")
        Path(a_path).write_bytes(b"AUDIO_BYTES")

        mock_scrape.return_value = {
            "product_name": "kai-clipper",
            "title": "กรรไกรตัดเล็บ Kai",
            "url": "https://shopee.co.th/kai-i.1.2",
            "full_summary": "สินค้าคุณภาพญี่ปุ่น",
            "shop_name": "Kai Japan",
            "scrape_source": "pdp_api",
            "has_cookie": False,
            "anti_bot_encountered": False,
        }

        mock_transcript.return_value = {
            "productName": "kai-clipper",
            "outputPath": t_path,
            "transcriptPath": t_path,
            "detailPath": d_path,
            "content": "สคริปต์",
            "detailContent": "แคปชั่น",
        }

        mock_tts.return_value = {
            "productName": "kai-clipper",
            "audioPath": a_path,
            "transcriptPath": t_path,
        }

        mock_record_memory.return_value = {
            "status": "updated",
            "path": str(temp_workspace["memory_file"]),
            "summary": "log summary",
        }

        res = run_orchestration_pipeline(
            shopee_url="https://shopee.co.th/kai-i.1.2",
            feedback="Great rhythm and pronunciation",
            learnings=["Always mention samurai heritage"],
        )

        assert res["productName"] == "kai-clipper"
        assert res["steps"]["shopeeScraper"]["status"] == "success"
        assert res["steps"]["transcript"]["status"] == "success"
        assert res["steps"]["tts"]["status"] == "success"
        assert res["steps"]["video"]["status"] == "skipped_deferred"
        assert res["steps"]["memory"]["status"] == "success"

        mock_scrape.assert_called_once_with("https://shopee.co.th/kai-i.1.2", cookie=None)
        mock_transcript.assert_called_once()
        mock_tts.assert_called_once()
        mock_record_memory.assert_called_once()

    @patch("omni_video.orchestrator.generate_transcript")
    @patch("omni_video.orchestrator.scrape_shopee_product")
    def test_orchestration_pipeline_fail_closed_missing_transcript(
        self, mock_scrape, mock_transcript, temp_workspace
    ):
        mock_scrape.return_value = {
            "product_name": "broken-item",
            "title": "สินค้า",
            "url": "https://shopee.co.th/broken-i.1.2",
            "full_summary": "สรุป",
            "shop_name": "ร้านค้า",
            "scrape_source": "url_slug",
            "has_cookie": False,
            "anti_bot_encountered": False,
        }

        # Mock transcript returning non-existent path
        mock_transcript.return_value = {
            "productName": "broken-item",
            "outputPath": "/tmp/non-existent-transcript.md",
        }

        with pytest.raises(RuntimeError, match="Fail-closed Guardrail: Transcript file not created"):
            run_orchestration_pipeline(shopee_url="https://shopee.co.th/broken-i.1.2")

    @patch("omni_video.orchestrator.generate_text_to_speech")
    @patch("omni_video.orchestrator.generate_transcript")
    @patch("omni_video.orchestrator.scrape_shopee_product")
    def test_orchestration_pipeline_fail_closed_missing_audio(
        self, mock_scrape, mock_transcript, mock_tts, temp_workspace
    ):
        t_path = str(temp_workspace["transcription_dir"] / "test-item.md")
        d_path = str(temp_workspace["detail_dir"] / "test-item.md")
        Path(t_path).write_text("## 1. Spoken Transcript\nสคริปต์", encoding="utf-8")
        Path(d_path).write_text("## 2. Facebook Reels Post Caption\nแคปชั่น", encoding="utf-8")

        mock_scrape.return_value = {
            "product_name": "test-item",
            "title": "สินค้า",
            "url": "https://shopee.co.th/test-i.1.2",
            "full_summary": "สรุป",
            "shop_name": "ร้านค้า",
            "scrape_source": "url_slug",
            "has_cookie": False,
            "anti_bot_encountered": False,
        }

        mock_transcript.return_value = {
            "productName": "test-item",
            "outputPath": t_path,
            "transcriptPath": t_path,
            "detailPath": d_path,
        }

        # Mock TTS returning non-existent audio path
        mock_tts.return_value = {
            "productName": "test-item",
            "audioPath": "/tmp/non-existent-audio.mp3",
        }

        with pytest.raises(RuntimeError, match="Fail-closed Guardrail: TTS Audio file missing or empty"):
            run_orchestration_pipeline(shopee_url="https://shopee.co.th/test-i.1.2")
