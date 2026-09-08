"""Unit tests for Phase 1 Active Agent: Transcript Generator."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from omni_video.subagents.transcript_generator import (
    _build_contextual_transcript_fallback,
    generate_transcript,
    read_tone_reference,
    split_transcript_and_details,
)


class TestTranscriptParsingAndFallback:
    """Tests for tone reading, output splitting, and contextual fallback."""

    def test_read_tone_reference(self, temp_workspace):
        tone = read_tone_reference()
        assert "Reference tone sample for non-hard-sell Thai copywriting." in tone

    def test_split_transcript_and_details_with_markers(self):
        raw_text = """
=== TRANSCRIPT START ===
# Transcript: test-item
## 1. Spoken Transcript
[curious tone] มันจะมีของกินชิ้นหนึ่ง...
=== TRANSCRIPT END ===

=== DETAIL START ===
# Details: test-item
## 1. Video Storyboard
| Scene | 1 |
=== DETAIL END ===
"""
        transcript, detail = split_transcript_and_details(
            raw_content=raw_text,
            clean_product_name="test-item",
            product_title="Test Item",
        )
        assert "[curious tone]" in transcript
        assert "Video Storyboard" in detail
        assert "=== TRANSCRIPT START ===" not in transcript
        assert "=== DETAIL START ===" not in detail

    def test_split_transcript_and_details_fallback_headings(self):
        raw_text = """# Transcript: test-item
## 1. Spoken Transcript with Speech Markup
[excited] สคริปต์พูดภาษาไทย

## 3. Video Storyboard
| Scene | Visual |
| 1 | Shot 1 |

## 4. Facebook Reels Post Caption
แคปชั่นโพสต์สุดปัง #ShopeeTH
"""
        transcript, detail = split_transcript_and_details(
            raw_content=raw_text,
            clean_product_name="test-item",
            product_title="Test Item",
        )
        assert "[excited]" in transcript
        assert "Video Storyboard" in detail
        assert "Facebook Reels Post Caption" in detail

    def test_build_contextual_fallback_food(self):
        t_content, d_content = _build_contextual_transcript_fallback(
            clean_product_name="pork-crackling",
            product_title="น้ำพริกกากหมูแท้ กรอบนาน",
            product_details="รสชาติเข้มข้น ไม่เหม็นหืน",
            scraped_data={"shop_name": "ร้านคุณยาย", "price": "฿79.00"},
            affiliate_link="https://shope.ee/test",
        )

        assert "น้ำพริกกากหมูแท้" in t_content
        assert "[curious tone]" in t_content
        assert "ร้านคุณยาย" in t_content
        assert "กรอบสะท้านฟัน" in t_content
        assert "3 วิธีฟินให้อร่อยคูณสอง" in t_content
        assert "https://shope.ee/test" in d_content
        assert "Video Storyboard & Scene Cues" in d_content

    def test_build_contextual_fallback_general_goods(self):
        t_content, d_content = _build_contextual_transcript_fallback(
            clean_product_name="nail-clipper",
            product_title="กรรไกรตัดเล็บพรีเมียม ญี่ปุ่น",
            product_details="สแตนเลสสตีล คมกริบ",
            scraped_data={"shop_name": "Seki Knives", "price": "฿199.00"},
            affiliate_link="https://shope.ee/nail",
        )

        assert "ของใช้ชิ้นหนึ่ง" in t_content
        assert "Seki Knives" in t_content
        assert "Video Storyboard & Scene Cues" in d_content
        assert "https://shope.ee/nail" in d_content


class TestGenerateTranscript:
    """Tests for the main generate_transcript subagent function."""

    def test_empty_product_name_raises_value_error(self):
        with pytest.raises(ValueError, match="Product name or Shopee URL is required"):
            generate_transcript("")

    @patch("omni_video.subagents.transcript_generator.get_gemini_client")
    def test_generate_transcript_with_gemini_success(self, mock_get_client, temp_workspace):
        # Mock Gemini client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """
=== TRANSCRIPT START ===
# Transcript: kai-clipper
## 1. Spoken Transcript with Speech Markup
[curious tone] มันจะมีของใช้ชิ้นหนึ่ง...
## 2. Plain Voiceover Script
มันจะมีของใช้ชิ้นหนึ่ง...
=== TRANSCRIPT END ===

=== DETAIL START ===
# Details: kai-clipper
## 1. Video Storyboard
| Scene | 1 |
## 2. Facebook Reels Post Caption
แคปชั่นโพสต์ #ShopeeTH
=== DETAIL END ===
"""
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        res = generate_transcript(
            product_name="kai-clipper",
            product_details="กรรไกรตัดเล็บเกรดซามูไร 800 ปี",
        )

        assert res["productName"] == "kai-clipper"
        assert Path(res["outputPath"]).exists()
        assert Path(res["detailPath"]).exists()
        assert "[curious tone]" in Path(res["outputPath"]).read_text(encoding="utf-8")
        assert "Video Storyboard" in Path(res["detailPath"]).read_text(encoding="utf-8")

    @patch("omni_video.subagents.transcript_generator.with_retry", side_effect=Exception("API unavailable"))
    @patch("omni_video.subagents.transcript_generator.get_gemini_client")
    def test_generate_transcript_api_error_fallback(self, mock_get_client, mock_retry, temp_workspace):
        res = generate_transcript(
            product_name="น้ำพริกตาแดง",
            product_details="น้ำพริกตาแดงรสเด็ด สูตรโบราณ",
        )

        assert res["productName"] == "น้ำพริกตาแดง"
        assert Path(res["outputPath"]).exists()
        assert Path(res["detailPath"]).exists()
        # Fallback content should be written
        content = Path(res["outputPath"]).read_text(encoding="utf-8")
        assert "น้ำพริกตาแดง" in content
        assert "ของกินชิ้นหนึ่ง" in content

    @patch("omni_video.subagents.transcript_generator.get_gemini_client")
    def test_generate_transcript_injects_memory(self, mock_get_client, temp_workspace):
        # Write learning to memory
        temp_workspace["memory_file"].write_text(
            "- **Rule**: Always emphasize crunch sound for crispy snacks",
            encoding="utf-8",
        )

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "=== TRANSCRIPT START ===\n# Transcript\n=== TRANSCRIPT END ===\n=== DETAIL START ===\n# Detail\n=== DETAIL END ==="
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        generate_transcript(product_name="crispy-pork", product_details="หมูกระจกกรอบ")

        # Verify prompt passed to Gemini contains memory
        args, kwargs = mock_client.models.generate_content.call_args
        prompt_used = kwargs.get("contents", "")
        assert "CONTINUOUS IMPROVEMENT MEMORY & LEARNED RULES:" in prompt_used
        assert "Always emphasize crunch sound" in prompt_used

    @patch("omni_video.skills.shopee_scraper.scrape_shopee_product")
    @patch("omni_video.subagents.transcript_generator.get_gemini_client")
    def test_generate_transcript_auto_scrapes_shopee_url(
        self, mock_get_client, mock_scrape, temp_workspace
    ):
        mock_scrape.return_value = {
            "product_name": "auto-scraped-pork",
            "title": "กากหมูทอดสดใหม่",
            "url": "https://shopee.co.th/auto-pork-i.1.2",
            "full_summary": "สรุปสินค้าจาก Shopee",
            "shop_name": "ร้านหมูทอง",
        }

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "=== TRANSCRIPT START ===\n# Transcript\n=== TRANSCRIPT END ===\n=== DETAIL START ===\n# Detail\n=== DETAIL END ==="
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        res = generate_transcript(product_name="https://shopee.co.th/auto-pork-i.1.2")

        mock_scrape.assert_called_once_with("https://shopee.co.th/auto-pork-i.1.2")
        assert res["productName"] == "auto-scraped-pork"
