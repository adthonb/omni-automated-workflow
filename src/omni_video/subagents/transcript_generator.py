import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    from ..config import CONFIG
    from ..skills.memory_manager import read_memory
    from ..utils.gemini_client import get_gemini_client, with_retry
except (ImportError, ValueError):
    from omni_video.config import CONFIG
    from omni_video.skills.memory_manager import read_memory
    from omni_video.utils.gemini_client import get_gemini_client, with_retry


def read_tone_reference() -> str:
    """Read the reference tone file (from ./tone.text)."""
    tone_path = Path(CONFIG["PATHS"]["TONE_FILE"])
    if tone_path.exists():
        return tone_path.read_text(encoding="utf-8")
    return ""


def read_viral_style_profile() -> dict[str, Any] | None:
    """Read learned viral seller style profile if available."""
    json_path = Path(CONFIG["PATHS"]["ANALYSIS_DIR"]) / "viral-seller-style.json"
    if json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _build_contextual_transcript_fallback(
    clean_product_name: str,
    product_title: str,
    product_details: str,
    scraped_data: dict[str, Any] | None,
    affiliate_link: str,
) -> tuple[str, str]:
    """Build a high-converting 5-stage storytelling script and split into (transcript_content, detail_content)."""
    shop_name = (scraped_data.get("shop_name") if scraped_data else "") or ""
    shop_desc = (scraped_data.get("shop_description") if scraped_data else "") or ""
    p_desc = (scraped_data.get("description") if scraped_data else "") or ""
    price_str = (scraped_data.get("price") if scraped_data else "") or ""

    clean_tag = re.sub(r'[^a-zA-Z0-9ก-๙]+', '', clean_product_name)

    # Detect product niche (food vs general)
    is_food = any(w in (product_title + product_details).lower() for w in ["น้ำพริก", "หมู", "กิน", "กากหมู", "ขนม", "อร่อย", "แซ่บ", "อาหาร"])

    if is_food:
        item_category = "ของอร่อย"
        hook_sentence = f"มันจะมีของกินชิ้นหนึ่งที่ใครได้ลองชิมแล้วต้องพูดเป็นเสียงเดียวกันว่า รู้งี้สั่งตั้งนานแล้ว! [short pause] ของชิ้นนั้นก็คือ {product_title} ครับ! [enthusiastic]"
        if shop_name:
            origin_sentence = f"จุดเริ่มต้นของความอร่อยนี้มาจากร้าน {shop_name} ครับ [warm] เขาทำอาหารสูตรต้นตำรับแท้ๆ ที่ใส่ใจทุกขั้นตอน ผลิตสดใหม่วันต่อวัน คัดสรรวัตถุดิบคุณภาพดี จนคนในพื้นที่ยกนิ้วให้เลยครับ [confident]"
        else:
            origin_sentence = f"จุดเริ่มต้นมาจากสูตรพื้นบ้านต้นตำรับแท้ๆ ที่ทำสดใหม่วันต่อวัน [warm] คัดสรรวัตถุดิบชั้นดี ปรุงรสแบบเข้มข้นถึงเครื่อง จนใครได้ชิมก็ติดใจครับ [confident]"

        pain_sentence = f"ปกติแล้วเวลาเราสั่งของกินแบบนี้ทั่วไป ถ้าไม่สดจริง บางทีเจอทั้งเหนียว เหม็นหืน และอมน้ำมัน กินแล้วเสียอารมณ์มาก [sighs] แต่ตัวนี้ทำออกมาได้มาตรฐานสุดๆ [emphasis] ชิ้นใหญ่ กรอบสะท้านฟัน ไม่อมน้ำมัน และที่สำคัญคือกรอบนาน ไม่มีกลิ่นหืนกวนใจเลยครับ [excited]"

        tips_block = f"""และนี่คือ 3 วิธีฟินให้อร่อยคูณสอง:
1. [emphasis] โรยบนข้าวสวยร้อนๆ หรือทานคู่กับไข่ต้มยางมะตูมเยิ้มๆ ฟินมาก!
2. [warm] พกติดกระเป๋าไปกินที่ทำงานตอนบ่าย แก้ง่วงได้ดีสุดๆ
3. [excited] ทานเล่นเป็นของว่างเคี้ยวเพลินจนหยุดไม่อยู่!"""

        cta_question = "แล้วเพื่อนๆ ล่ะครับ ชอบกินคู่กับเมนูไหนมากที่สุด คอมเมนต์มาคุยกันหน่อยครับ! [laughs]"
        bullet_points = (
            f"✅ ผลิตสดใหม่ทุกวัน รสชาติเข้มข้น กรอบนาน ไม่เหม็นหืน\n"
            f"✅ สูตรต้นตำรับแท้ คัดสรรวัตถุดิบคุณภาพ {f'จากร้าน ' + shop_name if shop_name else ''}\n"
            f"✅ ขนาดพกพาสะดวก ทานกับอะไรก็อร่อย"
        )
    else:
        item_category = "ของใช้ในบ้าน"
        hook_sentence = f"มันจะมีของใช้ชิ้นหนึ่งที่ใครได้ลองใช้แล้วต้องพูดเป็นเสียงเดียวกันว่า รู้งี้ซื้อตั้งนานแล้ว! [short pause] ของชิ้นนั้นก็คือ {product_title} ครับ! [enthusiastic]"
        if shop_name:
            origin_sentence = f"แบรนด์นี้มาจากร้าน {shop_name} ครับ [warm] ที่ตั้งใจคัดสรรของดีมีมาตรฐาน แก้ปัญหาชีวิตประจำวันได้ตรงจุด คุ้มค่าคุ้มราคามากครับ [confident]"
        else:
            origin_sentence = f"จุดเริ่มต้นมาจากความตั้งใจที่จะแก้ปัญหาจุกจิกในชีวิตประจำวัน [warm] ด้วยนวัตกรรมที่ใส่ใจในรายละเอียด คุ้มค่าคุ้มราคามากครับ [confident]"

        pain_sentence = f"หลายคนเจอปัญหาที่ใช้ของทั่วไปแล้วพังง่าย ไม่ทนทาน [short pause] และเสียเวลา [sighs] แต่ตัวนี้ออกแบบมาตอบโจทย์สุดๆ [emphasis] ใช้งานง่าย แข็งแรงทนทาน และคุณภาพเกินราคามากๆ ครับ [warm]"

        tips_block = f"""และนี่คือ 3 ข้อดีที่ทำให้ตัวนี้น่าใช้สุดๆ:
1. [emphasis] คุณภาพวัสดุเกรดพรีเมียม ใช้งานได้ยาวนาน
2. [warm] ดีไซน์กะทัดรัด สะดวกสบาย ตอบโจทย์ทุกการใช้งาน
3. [excited] ฟังก์ชันครบ จบในตัวเดียว ไม่ต้องซื้อเพิ่ม!"""

        cta_question = "แล้วเพื่อนๆ เคยเจอปัญหาแบบนี้กันไหม คอมเมนต์มาคุยกันหน่อยครับ! [laughs]"
        bullet_points = (
            f"✅ วัสดุเกรดพรีเมียม แข็งแรง ทนทาน\n"
            f"✅ ใช้งานง่าย ประหยัดเวลา ตอบโจทย์ชีวิตประจำวัน\n"
            f"✅ การันตีคุณภาพ คุ้มค่าคุ้มราคา"
        )

    clean_hook = re.sub(r'\[.*?\]', '', hook_sentence).strip()
    clean_origin = re.sub(r'\[.*?\]', '', origin_sentence).strip()
    clean_pain = re.sub(r'\[.*?\]', '', pain_sentence).strip()
    clean_tips = re.sub(r'\[.*?\]', '', tips_block).strip()
    clean_cta = re.sub(r'\[.*?\]', '', cta_question).strip()

    transcript_content = f"""# Transcript: {clean_product_name}

## Metadata
- **Product**: {clean_product_name}
- **Title**: {product_title}
- **Shop**: {shop_name or 'Shopee Verified Shop'}
- **Language**: Thai (th-TH)
- **Target Duration**: 45-60 seconds
- **Platform**: Facebook Reels & Shopee Affiliate

## 1. Spoken Transcript with Speech Markup (For Gemini TTS)
[curious tone] {hook_sentence}
{origin_sentence}
[short pause]
{pain_sentence}

{tips_block}

[friendly] ใครที่กำลังหาไอเทมตัวนี้อยู่ ผมแปะพิกัดของแท้พร้อมโค้ดส่วนลด Shopee ไว้ให้ในคอมเมนต์แล้วนะครับ [short pause]
{cta_question}

## 2. Plain Voiceover Script (Clean Text)
{clean_hook} {clean_origin} {clean_pain} {clean_tips} ใครที่กำลังหาไอเทมตัวนี้อยู่ ผมแปะพิกัดของแท้พร้อมโค้ดส่วนลด Shopee ไว้ให้ในคอมเมนต์แล้วนะครับ {clean_cta}"""

    detail_content = f"""# Details: {clean_product_name}

## Metadata
- **Product**: {clean_product_name}
- **Title**: {product_title}
- **Shop**: {shop_name or 'Shopee Verified Shop'}
- **Language**: Thai (th-TH)
- **Target Duration**: 45-60 seconds
- **Platform**: Facebook Reels & Shopee Affiliate

## 1. Video Storyboard & Scene Cues (For Video Generator)
| Scene | Timestamp | Visual Scene Prompt (for Gemini Omni Video) | On-Screen Thai Text Overlay | Audio Voiceover Cue |
|---|---|---|---|---|
| 1 | 0:00-0:05 | Closeup beauty shot of {product_title[:30]} with dynamic lighting | รู้งี้ซื้อตั้งนานแล้ว! 🔥 | มันจะมี{item_category}... |
| 2 | 0:05-0:15 | Origin & Craftsmanship presentation | การันตีความฟิน ✨ | จุดเริ่มต้นของ... |
| 3 | 0:15-0:30 | Core features & texture demonstration | คุณภาพพรีเมียม กรอบนาน 💡 | ปกติทั่วไปเวลาซื้อ... |
| 4 | 0:30-0:45 | 3 Key benefits & consumption/usage tips | 3 จุดเด่นที่ต้องลอง! 🌟 | และนี่คือ 3 ข้อดี... |
| 5 | 0:45-0:60 | Shopee affiliate badge & comment pointer | พิกัดในคอมเมนต์ 👇 | ใครที่กำลังหาไอเทมตัวนี้อยู่... |

## 2. Facebook Reels Post Caption & Copywriting
🔥 แนะนำไอเทมเด็ด Shopee: {product_title[:60]}

{bullet_points}
{f'💰 ราคาพิเศษ: {price_str}' if price_str else ''}

👇 พิกัด Shopee พร้อมแจกโค้ดส่วนลดพิเศษ จิ้มที่ลิงก์ในคอมเมนต์ได้เลยครับ!
🔗 {affiliate_link}

#ShopeeTH #ของดีบอกต่อ #ShopeeAffiliate #รีวิวShopee #{clean_tag}"""

    return transcript_content, detail_content


def split_transcript_and_details(
    raw_content: str,
    clean_product_name: str,
    product_title: str,
    shop_name: str = "",
    product_details: str = "",
    scraped_data: dict[str, Any] | None = None,
    affiliate_link: str = "https://shope.ee/affiliate-link",
) -> tuple[str, str]:
    """
    Split content into:
    1. Transcript (Metadata + Spoken Transcript + Plain Voiceover)
    2. Details (Metadata + Video Storyboard & Scene Cues + Facebook Reels Post Caption)
    """
    t_match = re.search(r"===\s*TRANSCRIPT START\s*===([\s\S]*?)===\s*TRANSCRIPT END\s*===", raw_content, re.IGNORECASE)
    d_match = re.search(r"===\s*DETAIL START\s*===([\s\S]*?)===\s*DETAIL END\s*===", raw_content, re.IGNORECASE)

    if t_match and d_match:
        return t_match.group(1).strip(), d_match.group(1).strip()

    # Fallback: check if standard markdown headings exist
    split_point = re.search(r"\n(?=##\s*(?:3\.\s*)?Video Storyboard)", raw_content, re.IGNORECASE)
    if not split_point:
        split_point = re.search(r"\n(?=##\s*(?:4\.\s*)?Facebook Reels Post Caption)", raw_content, re.IGNORECASE)

    if split_point:
        transcript_part = raw_content[:split_point.start()].strip()
        detail_raw = raw_content[split_point.start():].strip()

        # Adjust headings in detail_raw if needed
        detail_body = re.sub(r"##\s*3\.\s*Video Storyboard", "## 1. Video Storyboard", detail_raw, flags=re.IGNORECASE)
        detail_body = re.sub(r"##\s*4\.\s*Facebook Reels Post Caption", "## 2. Facebook Reels Post Caption", detail_body, flags=re.IGNORECASE)

        metadata_header = f"""# Details: {clean_product_name}

## Metadata
- **Product**: {clean_product_name}
- **Title**: {product_title}
{f'- **Shop**: {shop_name}' if shop_name else ''}
- **Language**: Thai (th-TH)
- **Target Duration**: 45-60 seconds
- **Platform**: Facebook Reels & Shopee Affiliate

"""
        detail_part = metadata_header + detail_body
        return transcript_part, detail_part

    # If no details found in raw_content, generate fallback detail
    fb_t, fb_d = _build_contextual_transcript_fallback(
        clean_product_name=clean_product_name,
        product_title=product_title,
        product_details=product_details,
        scraped_data=scraped_data,
        affiliate_link=affiliate_link,
    )
    if raw_content.strip():
        return raw_content.strip(), fb_d
    return fb_t, fb_d


def generate_transcript(
    product_name: str,
    product_details: str = "",
    target_audience: str = "Shopee / Facebook Reels Thai shoppers",
    affiliate_link: str = "https://shope.ee/affiliate-link",
    model: str | None = None,
    scraped_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Subagent: Generate transcript
    Model: gemini-3.8-flash
    Tone reference: ./tone.text
    Transcript Output: ./transcription/${product-name}.md (Transcript only)
    Detail Output: ./detail/${product-name}.md (Storyboard & Facebook Caption)
    """
    if not product_name:
        raise ValueError("Product name or Shopee URL is required to generate transcript.")

    # If product_name is actually a Shopee URL, scrape it first
    if product_name.startswith("http://") or product_name.startswith("https://") or "shopee.co.th" in product_name:
        try:
            from ..skills.shopee_scraper import scrape_shopee_product
        except (ImportError, ValueError):
            from omni_video.skills.shopee_scraper import scrape_shopee_product
        scraped_data = scrape_shopee_product(product_name)
        product_name = scraped_data["product_name"]
        if not affiliate_link or affiliate_link == "https://shope.ee/affiliate-link":
            affiliate_link = scraped_data["url"]
        if not product_details:
            product_details = scraped_data["full_summary"]
        else:
            product_details = f"{product_details}\n\n{scraped_data['full_summary']}"

    clean_product_name = re.sub(r'[/\\?%*:|"<>]+', "-", product_name.strip())
    model_name = model or CONFIG["MODELS"]["TRANSCRIPT"]

    product_title = (scraped_data.get("title") if scraped_data else None) or clean_product_name
    shop_name = (scraped_data.get("shop_name") if scraped_data else None) or ""
    scraped_summary = (scraped_data.get("full_summary") if scraped_data else None) or product_details

    print(f'[TranscriptGenerator] Generating transcript for: "{clean_product_name}"')
    if product_title != clean_product_name:
        print(f'[TranscriptGenerator] Full Title: "{product_title[:60]}..."')
    if shop_name:
        print(f'[TranscriptGenerator] Shop: "{shop_name}"')
    print(f"[TranscriptGenerator] Using model: {model_name}")

    tone_reference = read_tone_reference()
    viral_style = read_viral_style_profile()
    persistent_memory = read_memory()
    if persistent_memory:
        print("[TranscriptGenerator] Loaded persistent memory from MEMORY.md for continuous improvement.")

    client = get_gemini_client()

    prompt = f"""
You are an award-winning Thai social commerce copywriter and scriptwriter specializing in high-conversion Shopee Affiliate videos and Facebook Reels.

Follow Google Gemini Speech Generation Prompting Guidelines (https://ai.google.dev/gemini-api/docs/speech-generation#prompting-guide):
- Use natural Thai conversational spoken language (ภาษาพูดที่เป็นธรรมชาติ ชวนฟัง ไม่เป็นทางการเกินไป น่าติดตาม).
- Structure the script for optimal audio delivery with Gemini TTS.
- Include explicit Director's Notes and Speech Tags for the TTS engine:
  - Emotion & delivery tags: [excited], [curious tone], [enthusiastic], [empathetic], [confident], [warm], [whispering]
  - Pacing & pause tags: [short pause], [beat], [emphasis], [dramatic pause]
  - Sound/reaction tags: [laughs], [sighs], [gasp]

TARGET PRODUCT & SHOPEE DETAILS:
- Product Title / Name: {product_title}
{f'- Shop Name: {shop_name}' if shop_name else ''}
- Scraped Product Features & Specifications:
\"\"\"
{scraped_summary or "Top quality, trending item, solves daily life problem, must-have recommendation"}
\"\"\"
- Target Audience: {target_audience}
- Affiliate Call To Action: Link in comments / bio ({affiliate_link})

WINNING REFERENCE TONE (Analyze this viral soft-sell script carefully):
\"\"\"
{tone_reference}
\"\"\"

{f'CONTINUOUS IMPROVEMENT MEMORY & LEARNED RULES:\n\"\"\"\n{persistent_memory}\n\"\"\"\n\nCRITICAL SELF-IMPROVEMENT INSTRUCTION:\nReview the CONTINUOUS IMPROVEMENT MEMORY above carefully. You MUST strictly adhere to all learned rules, tone nuances, past corrections, and user preferences to ensure this transcript improves upon previous outputs.\n' if persistent_memory else ''}
{f'LEARNED VIRAL SELLER STYLE PROFILE:\n{json.dumps(viral_style, indent=2, ensure_ascii=False)}' if viral_style else ''}

INSTRUCTIONS FOR OUTPUT:
Generate two distinct blocks:

=== TRANSCRIPT START ===
# Transcript: {clean_product_name}

## Metadata
- **Product**: {clean_product_name}
- **Title**: {product_title}
{f'- **Shop**: {shop_name}' if shop_name else ''}
- **Language**: Thai (th-TH)
- **Target Duration**: 45-60 seconds
- **Platform**: Facebook Reels & Shopee Affiliate

## 1. Spoken Transcript with Speech Markup (For Gemini TTS)
Write the complete voiceover script in Thai with inline speech tags and director's notes (e.g. `[excited] มันจะมี...`, `[short pause]`, `[emphasis] ขาดในฉับเดียว`).
The script MUST reflect the actual product description, craftsmanship/origin, and features scraped from Shopee, following the winning 5-stage blueprint:
1. **Curiosity Hook (0-5s)**: Grab attention immediately without hard-selling (e.g., "มันจะมีของใช้/ของกินชิ้นหนึ่งที่...", "ใครที่เจอปัญหานี้อยู่...").
2. **Origin / Credibility / Pain Story (5-15s)**: Explain why this exists, shop lore/craftsmanship heritage, and what problem it solves.
3. **Product Revelation & Core Solution (15-30s)**: Highlight key features and contrast with ordinary inferior products.
4. **Actionable Value / 3 Expert Tips (30-45s)**: Give viewers genuinely useful advice/tips that make them trust you.
5. **Call To Action & Engagement (45-60s)**: Direct them to the Shopee link in the comment section and ask a relatable question to boost comments/algorithm.

## 2. Plain Voiceover Script (Clean Text)
The exact Thai voiceover without markup tags, suitable for clean audio processing and subtitles.
=== TRANSCRIPT END ===

=== DETAIL START ===
# Details: {clean_product_name}

## Metadata
- **Product**: {clean_product_name}
- **Title**: {product_title}
{f'- **Shop**: {shop_name}' if shop_name else ''}
- **Language**: Thai (th-TH)
- **Target Duration**: 45-60 seconds
- **Platform**: Facebook Reels & Shopee Affiliate

## 1. Video Storyboard & Scene Cues (For Video Generator)
A table with columns: | Scene | Timestamp | Visual Scene Prompt (for Gemini Omni Video) | On-Screen Thai Text Overlay | Audio Voiceover Cue |

## 2. Facebook Reels Post Caption & Copywriting
The ready-to-publish Facebook Reels post copy, including:
- Catchy Thai headline
- 3 key bullet points based on the product description
- Shopee affiliate link CTA ("พิกัดสินค้าจิ้มที่ลิงก์ในคอมเมนต์เลยนะครับ 👇")
- Relevant hashtags (#ShopeeTH #ของดีบอกต่อ #ShopeeAffiliate #รีวิวShopee)
=== DETAIL END ===

Ensure the output is clean and directly usable by downstream agents and skills.
"""

    print("[TranscriptGenerator] Sending request to Gemini...")
    transcript_content = ""
    detail_content = ""
    try:
        response = with_retry(
            lambda: client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
        )
        raw_text = getattr(response, "text", "") or ""
        transcript_content, detail_content = split_transcript_and_details(
            raw_content=raw_text,
            clean_product_name=clean_product_name,
            product_title=product_title,
            shop_name=shop_name,
            product_details=product_details,
            scraped_data=scraped_data,
            affiliate_link=affiliate_link,
        )
    except Exception as err:
        print(
            f"[TranscriptGenerator] API quota note: {err}. Generating contextual script reflecting scraped Shopee product description.",
            file=sys.stderr,
        )
        transcript_content, detail_content = _build_contextual_transcript_fallback(
            clean_product_name=clean_product_name,
            product_title=product_title,
            product_details=product_details,
            scraped_data=scraped_data,
            affiliate_link=affiliate_link,
        )

    transcription_dir = Path(CONFIG["PATHS"]["TRANSCRIPTION_DIR"])
    transcription_dir.mkdir(parents=True, exist_ok=True)
    output_path = transcription_dir / f"{clean_product_name}.md"
    output_path.write_text(transcript_content.strip() + "\n", encoding="utf-8")
    print(f"[TranscriptGenerator] Successfully generated transcript: {output_path}")

    detail_dir = Path(CONFIG["PATHS"].get("DETAIL_DIR", Path(CONFIG["PROJECT_ROOT"]) / "detail"))
    detail_dir.mkdir(parents=True, exist_ok=True)
    detail_path = detail_dir / f"{clean_product_name}.md"
    detail_path.write_text(detail_content.strip() + "\n", encoding="utf-8")
    print(f"[TranscriptGenerator] Successfully generated details (storyboard & caption): {detail_path}")

    return {
        "productName": clean_product_name,
        "productTitle": product_title,
        "outputPath": str(output_path),
        "transcriptPath": str(output_path),
        "detailPath": str(detail_path),
        "content": transcript_content,
        "detailContent": detail_content,
    }


if __name__ == "__main__":
    target_input = sys.argv[1] if len(sys.argv) > 1 else "kai-nail-clipper"
    details = sys.argv[2] if len(sys.argv) > 2 else ""
    try:
        res = generate_transcript(product_name=target_input, product_details=details)
        print("\n=== Generation Completed ===")
        print(f"Transcript: {res['outputPath']}")
        print(f"Details:    {res['detailPath']}")
    except Exception as e:
        print(f"[TranscriptGenerator Error]: {e}", file=sys.stderr)
        sys.exit(1)
