"""Unit tests for Phase 1 Active Command: CLI Interface."""

import sys
from unittest.mock import MagicMock, patch
import pytest

from omni_video.cli import main, print_help


class TestCliCommands:
    """Tests for CLI arguments dispatching to Active Phase subagents and skills."""

    def test_print_help(self, capsys):
        print_help()
        captured = capsys.readouterr()
        assert "Shopee Affiliate Video & Audio Orchestration CLI" in captured.out
        assert "omni-video orchestrate" in captured.out

    @patch("omni_video.cli.print_help")
    def test_cli_help_flag(self, mock_help, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["omni-video", "--help"])
        main()
        mock_help.assert_called_once()

    @patch("omni_video.cli.scrape_shopee_product")
    def test_cli_scrape_command(self, mock_scrape, monkeypatch, capsys):
        mock_scrape.return_value = {
            "product_name": "test-item",
            "title": "สินค้าทดสอบ",
            "price": "฿99.00",
        }
        monkeypatch.setattr(sys, "argv", ["omni-video", "scrape", "https://shopee.co.th/item-i.1.2"])
        main()
        mock_scrape.assert_called_once_with("https://shopee.co.th/item-i.1.2")
        captured = capsys.readouterr()
        assert "สินค้าทดสอบ" in captured.out

    @patch("omni_video.cli.scrape_shopee_product")
    def test_cli_scrape_missing_arg_exits(self, mock_scrape, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["omni-video", "scrape"])
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1

    @patch("omni_video.cli.generate_transcript")
    def test_cli_transcript_command(self, mock_transcript, monkeypatch, capsys):
        mock_transcript.return_value = {
            "productName": "test-pork",
            "outputPath": "/path/to/transcript.md",
            "detailPath": "/path/to/detail.md",
        }
        monkeypatch.setattr(
            sys, "argv", ["omni-video", "transcript", "test-pork", "น้ำพริกกรอบอร่อย"]
        )
        main()
        mock_transcript.assert_called_once_with(
            product_name="test-pork",
            product_details="น้ำพริกกรอบอร่อย",
        )
        captured = capsys.readouterr()
        assert "/path/to/transcript.md" in captured.out

    @patch("omni_video.cli.generate_text_to_speech")
    def test_cli_tts_command(self, mock_tts, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["omni-video", "tts", "kai-clipper"])
        main()
        mock_tts.assert_called_once_with(product_name="kai-clipper")

    @patch("omni_video.cli.read_memory", return_value="Test memory notes")
    @patch("omni_video.cli.get_memory_summary", return_value="Memory Summary")
    def test_cli_memory_command(self, mock_summary, mock_read, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["omni-video", "memory"])
        main()
        captured = capsys.readouterr()
        assert "Memory Summary" in captured.out
        assert "Test memory notes" in captured.out

    @patch("omni_video.cli.add_memory_entry")
    def test_cli_add_memory_command(self, mock_add, monkeypatch, capsys):
        mock_add.return_value = {
            "path": "/path/to/MEMORY.md",
            "bullet": "- **[2026-09-08] (cli)**: Custom rule",
        }
        monkeypatch.setattr(
            sys, "argv", ["omni-video", "add-memory", "Custom rule", "copywriting"]
        )
        main()
        mock_add.assert_called_once_with(
            category="copywriting", note="Custom rule", source="cli"
        )
        captured = capsys.readouterr()
        assert "Memory recorded to" in captured.out

    @patch("omni_video.cli.run_orchestration_pipeline")
    def test_cli_orchestrate_command_with_url(self, mock_pipeline, monkeypatch):
        test_url = "https://shopee.co.th/product-i.123.456"
        monkeypatch.setattr(sys, "argv", ["omni-video", "orchestrate", test_url])
        main()
        mock_pipeline.assert_called_once_with(
            shopee_url=test_url,
            product_name=None,
            product_details="",
            skip_video=True,
        )

    @patch("omni_video.cli.run_interactive_command")
    def test_cli_interactive_when_no_arguments(self, mock_interactive, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["omni-video"])
        main()
        mock_interactive.assert_called_once()
