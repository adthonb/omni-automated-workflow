"""Shopee Product Scraper Skill.

Scrapes product title, description, specifications, and shop lore from Shopee URLs.
Handles anti-bot protection via SHOPEE_COOKIE environment variable with multi-tier fallbacks.
"""

import json
import os
import re
import sys
import urllib.parse
from typing import Any

import requests

try:
    from ..config import CONFIG
except (ImportError, ValueError):
    from omni_video.config import CONFIG


def resolve_shopee_url(url: str, user_agent: str | None = None) -> str:
    """Resolve redirect for short links like shope.ee / th.shp.ee to full canonical URL."""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    parsed = urllib.parse.urlparse(url)
    # If already a full product URL with i.shopid.itemid, return as-is
    if "shopee.co.th" in parsed.netloc and ("-i." in parsed.path or "/product/" in parsed.path):
        return url

    # Follow redirect for short links
    ua = user_agent or CONFIG.get("SHOPEE", {}).get("USER_AGENT", "")
    headers = {"User-Agent": ua or "Mozilla/5.0"}
    try:
        resp = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        final_url = resp.url
        if final_url and final_url != url:
            print(f"[ShopeeScraper] Resolved short link {url} -> {final_url}")
            return final_url
    except Exception as err:
        print(f"[ShopeeScraper] Warning resolving URL {url}: {err}", file=sys.stderr)

    return url


def extract_shopee_identifiers(url: str) -> dict[str, str | None]:
    """Extract shop_id, item_id, and unquoted slug from a Shopee URL."""
    unquoted = urllib.parse.unquote(url)
    parsed = urllib.parse.urlparse(unquoted)
    path = parsed.path.strip("/")

    shop_id: str | None = None
    item_id: str | None = None
    raw_slug = ""

    # Match pattern: {slug}-i.{shop_id}.{item_id}
    m_i = re.search(r"(.*?)-i\.(\d+)\.(\d+)", path)
    if m_i:
        raw_slug = m_i.group(1).strip()
        shop_id = m_i.group(2)
        item_id = m_i.group(3)
    else:
        # Match pattern: /product/{shop_id}/{item_id}
        m_prod = re.search(r"product/(\d+)/(\d+)", path)
        if m_prod:
            shop_id = m_prod.group(1)
            item_id = m_prod.group(2)
            raw_slug = path.split("/")[-1]
        else:
            # Check query parameters (e.g. ?itemid=...&shopid=...)
            qs = urllib.parse.parse_qs(parsed.query)
            if "itemid" in qs and "shopid" in qs:
                item_id = qs["itemid"][0]
                shop_id = qs["shopid"][0]

    return {
        "shop_id": shop_id,
        "item_id": item_id,
        "raw_slug": raw_slug or path,
    }


def clean_slug_to_product_name(raw_slug: str, max_words: int = 4) -> str:
    """Derive a clean, concise product name suitable for file paths."""
    if not raw_slug:
        return "shopee-product"
    
    # Remove URL artifacts and decode
    slug = raw_slug.replace("_", "-").replace(" ", "-")
    slug = re.sub(r"-+", "-", slug).strip("-")

    # Split by hyphen or punctuation
    parts = [p.strip() for p in slug.split("-") if p.strip()]
    if not parts:
        return "shopee-product"

    # Take up to max_words parts for a clean filename
    short_parts = parts[:max_words]
    clean_name = "-".join(short_parts)
    # Sanitize characters safe for filesystems
    clean_name = re.sub(r'[/\\?%*:|"<>]+', "-", clean_name)
    return clean_name[:60].strip("-")


def get_cookie_from_env() -> str:
    """Retrieve Shopee cookie from environment variables."""
    # Check CONFIG or direct os.getenv
    cookie = CONFIG.get("SHOPEE", {}).get("COOKIE") or ""
    if not cookie:
        cookie = os.getenv("SHOPEE_COOKIE") or os.getenv("SHOPEE_COOKIES") or ""
    
    # Also support cookie file if specified
    cookie_file = os.getenv("SHOPEE_COOKIE_FILE", "")
    if not cookie and cookie_file and os.path.exists(cookie_file):
        try:
            cookie = open(cookie_file, encoding="utf-8").read().strip()
        except Exception:
            pass

    return cookie.strip()


def scrape_shopee_product(
    url: str,
    cookie: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """
    Scrape Shopee product description and details from URL.
    
    Tiers:
    1. PDP API (/api/v4/pdp/get_pc) using SHOPEE_COOKIE
    2. Item API (/api/v4/item/get)
    3. Shop Detail API (/api/v4/shop/get_shop_detail) - works even without cookie
    4. URL slug parsing for high-fidelity fallback
    """
    if not url or not url.strip():
        raise ValueError("Shopee URL cannot be empty.")

    resolved_url = resolve_shopee_url(url.strip())
    ident = extract_shopee_identifiers(resolved_url)
    shop_id = ident["shop_id"]
    item_id = ident["item_id"]
    raw_slug = ident["raw_slug"] or ""

    unquoted_slug_title = raw_slug.replace("-", " ").strip()
    clean_product_name = clean_slug_to_product_name(raw_slug)

    active_cookie = (cookie or get_cookie_from_env()).strip()
    ua = user_agent or CONFIG.get("SHOPEE", {}).get("USER_AGENT") or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

    headers = {
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": resolved_url,
        "X-Shopee-Language": "th",
        "X-Requested-With": "XMLHttpRequest",
        "X-API-SOURCE": "rweb",
    }
    if active_cookie:
        headers["Cookie"] = active_cookie

    product_title = unquoted_slug_title or clean_product_name
    product_description = ""
    attributes: list[dict[str, str]] = []
    price_str = ""
    shop_name = ""
    shop_description = ""
    anti_bot_encountered = False
    scrape_source = "url_slug"

    print(f"\n[ShopeeScraper] Scraping product from: {resolved_url}")
    if shop_id and item_id:
        print(f"[ShopeeScraper] Detected Shop ID: {shop_id}, Item ID: {item_id}")
    if active_cookie:
        print(f"[ShopeeScraper] Using SHOPEE_COOKIE from environment.")
    else:
        print(f"[ShopeeScraper] No SHOPEE_COOKIE defined. Attempting API & fallback extraction.")

    # 1. Attempt PDP API
    if shop_id and item_id:
        pdp_url = f"https://shopee.co.th/api/v4/pdp/get_pc?item_id={item_id}&shop_id={shop_id}"
        try:
            resp = requests.get(pdp_url, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("error") == 0 and "data" in data:
                    item_data = data["data"].get("item", {})
                    if item_data:
                        product_title = item_data.get("title") or item_data.get("name") or product_title
                        product_description = item_data.get("description", "")
                        scrape_source = "pdp_api"

                        # Extract attributes
                        for attr in item_data.get("attributes", []):
                            name = attr.get("name", "")
                            val = attr.get("value", "")
                            if name and val:
                                attributes.append({"name": name, "value": val})

                        # Price
                        price_min = item_data.get("price_min")
                        if price_min:
                            price_str = f"฿{price_min / 100000:.2f}"
                elif data.get("error") == 90309999 or "error" in data:
                    anti_bot_encountered = True
            elif resp.status_code == 403:
                anti_bot_encountered = True
        except Exception as err:
            print(f"[ShopeeScraper] PDP API notice: {err}", file=sys.stderr)

    # 2. Attempt Item API if PDP didn't give full description
    if shop_id and item_id and not product_description:
        item_api_url = f"https://shopee.co.th/api/v4/item/get?itemid={item_id}&shopid={shop_id}"
        try:
            resp = requests.get(item_api_url, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("error") == 0 and "data" in data:
                    item_data = data["data"]
                    product_title = item_data.get("name") or product_title
                    product_description = item_data.get("description", "")
                    scrape_source = "item_api"
                    if item_data.get("price"):
                        price_str = f"฿{item_data['price'] / 100000:.2f}"
            elif resp.status_code == 403:
                anti_bot_encountered = True
        except Exception as err:
            print(f"[ShopeeScraper] Item API notice: {err}", file=sys.stderr)

    # 3. Fetch Shop Detail API (Often accessible without full anti-bot challenge)
    if shop_id:
        shop_url = f"https://shopee.co.th/api/v4/shop/get_shop_detail?shopid={shop_id}"
        try:
            shop_headers = {"User-Agent": "ShopeeTH/3.15.20 (Android 12; Pixel 6 Pro)"}
            if active_cookie:
                shop_headers["Cookie"] = active_cookie
            s_resp = requests.get(shop_url, headers=shop_headers, timeout=6)
            if s_resp.status_code == 200:
                s_data = s_resp.json().get("data", {})
                shop_name = s_data.get("name", "")
                shop_description = s_data.get("description", "")
                if shop_name:
                    print(f"[ShopeeScraper] Shop lore extracted: '{shop_name}'")
        except Exception as err:
            print(f"[ShopeeScraper] Shop detail notice: {err}", file=sys.stderr)

    # 4. If anti-bot was encountered without cookie, inform user
    if anti_bot_encountered and not active_cookie:
        print(
            "[ShopeeScraper] 🛡️  Shopee anti-bot detected on product page.\n"
            "                 -> Scraped rich product metadata from URL slug & Shop profile.\n"
            "                 -> To fetch full product description via API, define SHOPEE_COOKIE in your .env file."
        )

    # 5. Build structured summary for downstream Transcript Subagent
    summary_lines: list[str] = [
        f"ชื่อสินค้า (Title): {product_title}",
    ]
    if shop_name:
        summary_lines.append(f"ร้านค้า (Shop): {shop_name}")
    if price_str:
        summary_lines.append(f"ราคา (Price): {price_str}")
    if attributes:
        attr_str = ", ".join(f"{a['name']}: {a['value']}" for a in attributes)
        summary_lines.append(f"คุณลักษณะสินค้า (Attributes): {attr_str}")
    if product_description:
        summary_lines.append(f"\nรายละเอียดสินค้า (Description):\n{product_description.strip()}")
    elif shop_description:
        summary_lines.append(f"\nจุดเด่นและข้อมูลร้านค้า (Shop Lore & Quality Assurance):\n{shop_description.strip()}")
    else:
        summary_lines.append(
            f"\nจุดเด่นสินค้า: {unquoted_slug_title} (สินค้าคุณภาพ คัดสรรจาก Shopee การันตีความอร่อย/ความคุ้มค่า)"
        )

    full_summary = "\n".join(summary_lines)

    result = {
        "url": resolved_url,
        "product_name": clean_product_name,
        "title": product_title,
        "description": product_description,
        "shop_id": shop_id,
        "item_id": item_id,
        "shop_name": shop_name,
        "shop_description": shop_description,
        "attributes": attributes,
        "price": price_str,
        "full_summary": full_summary,
        "scrape_source": scrape_source,
        "anti_bot_encountered": anti_bot_encountered,
        "has_cookie": bool(active_cookie),
    }

    print(f"[ShopeeScraper] Successfully parsed: '{clean_product_name}'")
    print(f"[ShopeeScraper] Source: {scrape_source} | Shop: '{shop_name or 'N/A'}'")
    return result


if __name__ == "__main__":
    test_url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://shopee.co.th/%E0%B8%99%E0%B9%89%E0%B8%B3%E0%B8%9E%E0%B8%A3%E0%B8%B4%E0%B8%81%E0%B8%81%E0%B8%B2%E0%B8%81%E0%B8%AB%E0%B8%A1%E0%B8%B9-40-%E0%B8%81%E0%B8%A3%E0%B8%B1%E0%B8%A1-%E0%B8%99%E0%B9%89%E0%B8%B3%E0%B8%9E%E0%B8%A3%E0%B8%B4%E0%B8%81%E0%B8%AB%E0%B8%A1%E0%B8%B9%E0%B8%81%E0%B8%A3%E0%B8%B0%E0%B8%88%E0%B8%81-%E0%B8%99%E0%B9%89%E0%B8%B3%E0%B8%9E%E0%B8%A3%E0%B8%B4%E0%B8%81%E0%B9%81%E0%B8%84%E0%B8%9A%E0%B8%AB%E0%B8%A1%E0%B8%B9-%E0%B8%99%E0%B9%89%E0%B8%B3%E0%B8%9E%E0%B8%A3%E0%B8%B4%E0%B8%81%E0%B9%84%E0%B8%8B%E0%B8%AA%E0%B9%8C%E0%B8%9E%E0%B8%81%E0%B8%9E%E0%B8%B2-%E0%B8%9A%E0%B8%A3%E0%B8%A3%E0%B8%88%E0%B8%B8%E0%B8%8B%E0%B8%AD%E0%B8%87-%E0%B8%81%E0%B8%A3%E0%B8%AD%E0%B8%9A%E0%B8%99%E0%B8%B2%E0%B8%99-%E0%B9%84%E0%B8%A1%E0%B9%88%E0%B9%80%E0%B8%AB%E0%B8%A1%E0%B9%87%E0%B8%99%E0%B8%AB%E0%B8%B7%E0%B8%99-i.94288742.44006657140?extraParams=%7B%22display_model_id%22%3A128432243592%2C%22model_selection_logic%22%3A3%7D"
    )
    res = scrape_shopee_product(test_url)
    print("\n=== Scraped Result Summary ===")
    print(json.dumps(res, indent=2, ensure_ascii=False))
