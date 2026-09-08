"""Unit tests for Phase 1 Active Skill: Shopee Product Scraper."""

import json
from unittest.mock import MagicMock, patch
import pytest

from omni_video.skills.shopee_scraper import (
    clean_slug_to_product_name,
    extract_shopee_identifiers,
    get_cookie_from_env,
    resolve_shopee_url,
    scrape_shopee_product,
)


class TestShopeeUrlHandling:
    """Tests for URL resolution and identifier extraction."""

    def test_resolve_canonical_shopee_url(self):
        url = "https://shopee.co.th/product-slug-i.123456.789012"
        resolved = resolve_shopee_url(url)
        assert resolved == url

    @patch("requests.head")
    def test_resolve_short_link_success(self, mock_head):
        mock_resp = MagicMock()
        mock_resp.url = "https://shopee.co.th/premium-nail-clipper-i.999.888"
        mock_head.return_value = mock_resp

        short_url = "https://shope.ee/xyz123"
        resolved = resolve_shopee_url(short_url)
        assert resolved == "https://shopee.co.th/premium-nail-clipper-i.999.888"
        mock_head.assert_called_once()

    @patch("requests.head", side_effect=Exception("Connection timed out"))
    def test_resolve_short_link_fallback_on_error(self, mock_head):
        short_url = "https://shope.ee/fail"
        resolved = resolve_shopee_url(short_url)
        assert resolved == short_url

    def test_extract_identifiers_dash_i_format(self):
        url = "https://shopee.co.th/kai-nail-clipper-japan-i.94288742.44006657140"
        ident = extract_shopee_identifiers(url)
        assert ident["shop_id"] == "94288742"
        assert ident["item_id"] == "44006657140"
        assert "kai-nail-clipper-japan" in ident["raw_slug"]

    def test_extract_identifiers_product_path_format(self):
        url = "https://shopee.co.th/product/123456/789012"
        ident = extract_shopee_identifiers(url)
        assert ident["shop_id"] == "123456"
        assert ident["item_id"] == "789012"

    def test_extract_identifiers_query_param_format(self):
        url = "https://shopee.co.th/item_detail?itemid=99999&shopid=11111"
        ident = extract_shopee_identifiers(url)
        assert ident["shop_id"] == "11111"
        assert ident["item_id"] == "99999"

    def test_clean_slug_to_product_name(self):
        raw_slug = "น้ำพริกกากหมู_กรอบนาน_40-กรัม_ไม่เหม็นหืน"
        cleaned = clean_slug_to_product_name(raw_slug, max_words=4)
        assert cleaned == "น้ำพริกกากหมู-กรอบนาน-40-กรัม"

    def test_clean_slug_empty_fallback(self):
        assert clean_slug_to_product_name("") == "shopee-product"


class TestShopeeCookieHandling:
    """Tests for cookie retrieval."""

    def test_get_cookie_from_env_var(self, monkeypatch):
        monkeypatch.setenv("SHOPEE_COOKIE", "SPC_TEST=12345;")
        cookie = get_cookie_from_env()
        assert cookie == "SPC_TEST=12345;"

    def test_get_cookie_from_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SHOPEE_COOKIE", raising=False)
        cookie_file = tmp_path / "cookie.txt"
        cookie_file.write_text("SPC_FROM_FILE=abc;", encoding="utf-8")
        monkeypatch.setenv("SHOPEE_COOKIE_FILE", str(cookie_file))

        cookie = get_cookie_from_env()
        assert cookie == "SPC_FROM_FILE=abc;"


class TestShopeeScraping:
    """Tests for scrape_shopee_product skill execution."""

    def test_scrape_empty_url_raises_value_error(self):
        with pytest.raises(ValueError, match="Shopee URL cannot be empty"):
            scrape_shopee_product("   ")

    @patch("requests.get")
    def test_scrape_pdp_api_success(self, mock_get):
        # Mock PDP API response
        mock_pdp_resp = MagicMock()
        mock_pdp_resp.status_code = 200
        mock_pdp_resp.json.return_value = {
            "error": 0,
            "data": {
                "item": {
                    "title": "กรรไกรตัดเล็บ Kai ญี่ปุ่นแท้ สแตนเลสพรีเมียม",
                    "description": "กรรไกรตัดเล็บทำจากเหล็กกล้าคมกริบ พร้อมปลอกดักเศษเล็บ",
                    "price_min": 19900000,
                    "attributes": [
                        {"name": "แบรนด์", "value": "Kai"},
                        {"name": "ประเทศผู้ผลิต", "value": "ญี่ปุ่น"},
                    ],
                }
            },
        }

        # Mock Shop Detail response
        mock_shop_resp = MagicMock()
        mock_shop_resp.status_code = 200
        mock_shop_resp.json.return_value = {
            "data": {"name": "Kai Official Store", "description": "ร้านค้าอย่างเป็นทางการ"}
        }

        mock_get.side_effect = [mock_pdp_resp, mock_shop_resp]

        url = "https://shopee.co.th/kai-nail-clipper-i.12345.67890"
        result = scrape_shopee_product(url, cookie="SPC_TEST=123")

        assert result["scrape_source"] == "pdp_api"
        assert result["title"] == "กรรไกรตัดเล็บ Kai ญี่ปุ่นแท้ สแตนเลสพรีเมียม"
        assert "ปลอกดักเศษเล็บ" in result["description"]
        assert result["price"] == "฿199.00"
        assert result["shop_name"] == "Kai Official Store"
        assert len(result["attributes"]) == 2
        assert result["has_cookie"] is True
        assert result["anti_bot_encountered"] is False

    @patch("requests.get")
    def test_scrape_item_api_fallback(self, mock_get):
        # PDP API returns error
        mock_pdp_resp = MagicMock()
        mock_pdp_resp.status_code = 200
        mock_pdp_resp.json.return_value = {"error": 1, "data": {}}

        # Item API returns success
        mock_item_resp = MagicMock()
        mock_item_resp.status_code = 200
        mock_item_resp.json.return_value = {
            "error": 0,
            "data": {
                "name": "น้ำพริกกากหมู สูตรโบราณ",
                "description": "ทอดสดใหม่ทุกวัน ไร้น้ำมัน หอมเจียวกรอบ",
                "price": 8900000,
            },
        }

        # Shop Detail API
        mock_shop_resp = MagicMock()
        mock_shop_resp.status_code = 200
        mock_shop_resp.json.return_value = {
            "data": {"name": "ครัวคุณยายต้นตำรับ", "description": "สูตรโบราณ 50 ปี"}
        }

        mock_get.side_effect = [mock_pdp_resp, mock_item_resp, mock_shop_resp]

        url = "https://shopee.co.th/pork-chili-paste-i.111.222"
        result = scrape_shopee_product(url)

        assert result["scrape_source"] == "item_api"
        assert result["title"] == "น้ำพริกกากหมู สูตรโบราณ"
        assert "ทอดสดใหม่ทุกวัน" in result["description"]
        assert result["price"] == "฿89.00"
        assert result["shop_name"] == "ครัวคุณยายต้นตำรับ"

    @patch("requests.get")
    def test_scrape_anti_bot_with_shop_lore_fallback(self, mock_get):
        # PDP returns anti-bot challenge
        mock_pdp_resp = MagicMock()
        mock_pdp_resp.status_code = 403

        # Item API also blocked
        mock_item_resp = MagicMock()
        mock_item_resp.status_code = 403

        # Shop Detail API succeeds (accessible without full PDP cookie)
        mock_shop_resp = MagicMock()
        mock_shop_resp.status_code = 200
        mock_shop_resp.json.return_value = {
            "data": {
                "name": "มีดช่างเซกิ ญี่ปุ่นโบราณ",
                "description": "สืบทอดศาสตร์การตีดาบซามูไร 800 ปี",
            }
        }

        mock_get.side_effect = [mock_pdp_resp, mock_item_resp, mock_shop_resp]

        url = "https://shopee.co.th/seki-craft-knife-i.333.444"
        result = scrape_shopee_product(url, cookie=None)

        assert result["anti_bot_encountered"] is True
        assert result["scrape_source"] == "url_slug"
        assert result["shop_name"] == "มีดช่างเซกิ ญี่ปุ่นโบราณ"
        assert "สืบทอดศาสตร์การตีดาบซามูไร" in result["shop_description"]
        assert "จุดเด่นและข้อมูลร้านค้า" in result["full_summary"]
