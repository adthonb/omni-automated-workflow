#!/usr/bin/env python3
"""Shopee Scraper Skill Runner."""

import json
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from omni_video.skills.shopee_scraper import (
    clean_slug_to_product_name,
    extract_shopee_identifiers,
    resolve_shopee_url,
    scrape_shopee_product,
)

__all__ = [
    "resolve_shopee_url",
    "extract_shopee_identifiers",
    "clean_slug_to_product_name",
    "scrape_shopee_product",
]

if __name__ == "__main__":
    target_url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://shopee.co.th/%E0%B8%99%E0%B9%89%E0%B8%B3%E0%B8%9E%E0%B8%A3%E0%B8%B4%E0%B8%81%E0%B8%81%E0%B8%B2%E0%B8%81%E0%B8%AB%E0%B8%A1%E0%B8%B9-40-%E0%B8%81%E0%B8%A3%E0%B8%B1%E0%B8%A1-%E0%B8%99%E0%B9%89%E0%B8%B3%E0%B8%9E%E0%B8%A3%E0%B8%B4%E0%B8%81%E0%B8%AB%E0%B8%A1%E0%B8%B9%E0%B8%81%E0%B8%A3%E0%B8%B0%E0%B8%88%E0%B8%81-%E0%B8%99%E0%B9%89%E0%B8%B3%E0%B8%9E%E0%B8%A3%E0%B8%B4%E0%B8%81%E0%B9%81%E0%B8%84%E0%B8%9A%E0%B8%AB%E0%B8%A1%E0%B8%B9-%E0%B8%99%E0%B9%89%E0%B8%B3%E0%B8%9E%E0%B8%A3%E0%B8%B4%E0%B8%81%E0%B9%84%E0%B8%8B%E0%B8%AA%E0%B9%8C%E0%B8%9E%E0%B8%81%E0%B8%9E%E0%B8%B2-%E0%B8%9A%E0%B8%A3%E0%B8%A3%E0%B8%88%E0%B8%B8%E0%B8%8B%E0%B8%AD%E0%B8%87-%E0%B8%81%E0%B8%A3%E0%B8%AD%E0%B8%9A%E0%B8%99%E0%B8%B2%E0%B8%99-%E0%B9%84%E0%B8%A1%E0%B9%88%E0%B9%80%E0%B8%AB%E0%B8%A1%E0%B9%87%E0%B8%99%E0%B8%AB%E0%B8%B7%E0%B8%99-i.94288742.44006657140?extraParams=%7B%22display_model_id%22%3A128432243592%2C%22model_selection_logic%22%3A3%7D"
    )
    res = scrape_shopee_product(target_url)
    print("\n=== Shopee Scraper Finished ===")
    print(json.dumps(res, indent=2, ensure_ascii=False))
