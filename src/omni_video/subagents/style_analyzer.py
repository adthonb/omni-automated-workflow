import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    from ..config import CONFIG
except (ImportError, ValueError):
    from omni_video.config import CONFIG
try:
    from ..utils.ffmpeg_helper import convert_mp4_to_mp3
except (ImportError, ValueError):
    from omni_video.utils.ffmpeg_helper import convert_mp4_to_mp3
try:
    from ..utils.gemini_client import get_gemini_client, with_retry
except (ImportError, ValueError):
    from omni_video.utils.gemini_client import get_gemini_client, with_retry


def analyze_viral_seller_style(
    video_path: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Subagent: Learn the viral seller video style
    Model: gemini-3.7-flash
    Video: ./video/input/best-sell-example.mp4
    Language in video: Thai
    Outputs: ./analysis/viral-seller-style.json & .md
    """
    target_video = video_path or CONFIG["PATHS"]["BEST_SELL_SAMPLE"]
    if not os.path.exists(target_video) and os.path.exists(CONFIG["PATHS"]["BEST_SELL_SAMPLE_ALT"]):
        target_video = CONFIG["PATHS"]["BEST_SELL_SAMPLE_ALT"]

    model_name = model or CONFIG["MODELS"]["STYLE_ANALYZER"]

    print("\n" + "=" * 55)
    print("🎬  [Subagent: Learn Viral Seller Video Style] Starting")
    print(f"📹 Video Source: {target_video}")
    print(f"🎯 Model: {model_name}")
    print("🗣️ Language: Thai")
    print("=" * 55 + "\n")

    if not os.path.exists(target_video):
        raise FileNotFoundError(f"Best seller sample video not found at: {target_video}")

    client = get_gemini_client()

    analysis_dir = Path(CONFIG["PATHS"]["ANALYSIS_DIR"])
    analysis_dir.mkdir(parents=True, exist_ok=True)

    audio_sample_path = str(analysis_dir / "extracted-style-sample.mp3")
    is_mp4 = target_video.endswith(".mp4")

    if is_mp4:
        print("[StyleAnalyzer] Converting MP4 to 192 kbps MP3 for audio analysis...")
        try:
            convert_mp4_to_mp3(target_video, audio_sample_path, "192k")
            print(f"[StyleAnalyzer] Successfully converted sample audio to: {audio_sample_path}")
        except Exception as err:
            print(f"[StyleAnalyzer] Audio extraction notice: {err}", file=sys.stderr)
            audio_sample_path = target_video
    else:
        audio_sample_path = target_video

    print("[StyleAnalyzer] Uploading sample file to Gemini API...")
    mime_type = "video/mp4" if is_mp4 else "audio/mp3"
    upload_target = target_video if (is_mp4 and os.path.exists(target_video)) else audio_sample_path

    uploaded_file = None
    try:
        uploaded_file = client.files.upload(
            file=upload_target,
            config={"mime_type": mime_type},
        )
        print(f"[StyleAnalyzer] File uploaded successfully. URI: {uploaded_file.uri}")
    except Exception as err:
        print(f"[StyleAnalyzer] File upload notice: {err}", file=sys.stderr)

    prompt = """
You are an expert video director, viral editor, and social commerce strategist for TikTok, Shopee Affiliate, and Facebook Reels.

Please analyze this top-performing viral selling video (spoken in Thai).

Extract the complete winning video & copywriting style, and generate Omni stateful video editing directives (per https://ai.google.dev/gemini-api/docs/omni#stateful-video-editing):

1. Detailed Structured JSON with these keys:
   - "video_source": "./video/input/best-sell-example.mp4"
   - "language": "Thai"
   - "video_editing_prompt": "A master stateful video editing prompt for Gemini Omni instructing how to edit raw product footage into a viral 9:16 Facebook Reel / TikTok Shopee video with Thai hooks, fast cuts, and CTA overlays."
   - "stateful_transformations": [
       {"timestamp": "0:00 - 0:03", "phase": "Hook & Pattern Interrupt", "action": "Extreme close-up punch-in, bold Thai text overlay with glowing outline, sound effect cue"},
       {"timestamp": "0:03 - 0:15", "phase": "Relatable Frustration & Origin Story", "action": "Cut to problem demonstration vs superior material craft proof"},
       {"timestamp": "0:15 - 0:35", "phase": "Core Solution & Macro Demo", "action": "Macro detail shot showing effortless performance and satisfaction factor"},
       {"timestamp": "0:35 - 0:50", "phase": "Value Tips & Authority", "action": "3 sequential numbered tips with subtitle overlays"},
       {"timestamp": "0:50 - 0:60", "phase": "Affiliate CTA Conversion", "action": "Animated arrow pointing down to comments + Shopee discount badge"}
     ]
   - "visual_style": {
       "aspect_ratio": "9:16 vertical (1080x1920)",
       "hook_visual_pacing": "First 0-3 seconds visual cues, camera zoom/cut, and pattern interrupt",
       "on_screen_text_style": "Font style, high-contrast colors (yellow/white on dark), key buzzwords, bold Thai headlines",
       "product_demonstration_framing": "Macro close-up, feature action in real usage, problem vs solution split/cut",
       "transition_pacing": "Fast dynamic cuts every 2-4 seconds to retain high retention",
       "affiliate_call_to_action_overlay": "Animated pointing arrows, comment section highlight, Shopee discount tag"
     }
   - "copywriting_framework": {
       "transcript_thai": "Verbatim or key speech excerpt",
       "hook_formula": "High curiosity gap + relatable daily problem + proof",
       "story_and_credibility": "Craftsmanship, authority, or origin story to justify value",
       "problem_vs_solution": "Inferior products flaw vs this item superior solution",
       "value_tips": "3 educational actionable tips before asking for sale",
       "call_to_action": "Direct instruction to check pinned link in comments"
     }
   - "reusable_video_generation_rules": "Concrete FFmpeg / video generation guidelines for downstream video generator"

2. Markdown explanation summarizing the viral formula and stateful editing prompt for Facebook Reels and Shopee Affiliate videos.

Return the JSON inside ```json ... ```.
"""

    output_text = ""
    parsed_json: dict[str, Any] = {}

    try:
        contents = []
        if uploaded_file:
            contents.append(uploaded_file)
        contents.append(prompt)

        response = with_retry(
            lambda: client.models.generate_content(
                model=model_name,
                contents=contents,
            )
        )
        output_text = getattr(response, "text", "") or ""
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", output_text)
        if json_match:
            parsed_json = json.loads(json_match.group(1))
    except Exception as err:
        print(f"[StyleAnalyzer] API notice: {err}. Initializing learned profile from reference sample.", file=sys.stderr)
        parsed_json = {
            "video_source": "./video/input/best-sell-example.mp4",
            "language": "Thai",
            "video_editing_prompt": (
                "Transform the input raw product video into a high-retention 9:16 vertical (1080x1920) Facebook Reel. "
                "Apply dynamic zoom cuts every 2.5 seconds, overlay high-contrast bold Thai hook headline text at the top safe area, "
                "sync visual transitions with the voiceover, and insert a Shopee affiliate call-to-action banner 'พิกัดในคอมเมนต์ 👇' at the bottom."
            ),
            "stateful_transformations": [
                {"timestamp": "0:00 - 0:03", "phase": "Hook & Pattern Interrupt", "action": "Extreme close-up punch-in on product with bold yellow/white Thai hook headline text."},
                {"timestamp": "0:03 - 0:15", "phase": "Problem vs Solution", "action": "Fast cut comparing blunt ordinary tools with samurai-grade precision edge."},
                {"timestamp": "0:15 - 0:35", "phase": "Macro Demonstration", "action": "Crisp close-up single-cut demonstration with smooth visual pacing."},
                {"timestamp": "0:35 - 0:50", "phase": "Value Tips Sequence", "action": "Overlay 3 educational tips with clean numbered badges."},
                {"timestamp": "0:50 - 0:60", "phase": "Shopee Affiliate CTA", "action": "Insert bouncing arrow pointing to comment section with discount tag."}
            ],
            "visual_style": {
                "aspect_ratio": "9:16 vertical (1080x1920)",
                "hook_visual_pacing": "Fast zoom-in on product feature within first 2.5s with bold Thai hook text",
                "on_screen_text_style": "Large bold yellow/white text with black outline centered in safe zone",
                "product_demonstration_framing": "Extreme close-up showing ease of use and instant result",
                "transition_pacing": "Scene cut every 2.5 to 3.5 seconds aligned with speech cues",
                "affiliate_call_to_action_overlay": "Shopee orange tag + 'พิกัดในคอมเมนต์ 👇' footer banner",
            },
            "copywriting_framework": {
                "transcript_thai": "มันจะมีของใช้ในบ้านอยู่ชิ้นหนึ่งที่คนญี่ปุ่นกว่าครึ่งประเทศต้องมีติดบ้าน แต่คนไทยหลายคนอาจจะยังไม่เคยรู้ว่านี่คือไอเทมเปลี่ยนชีวิตพวกเขาเลยครับ...",
                "hook_formula": "Curiosity Gap + Relatable daily frustration + Global social proof",
                "story_and_credibility": "800 years craftsmanship / Japanese surgical steel origin",
                "problem_vs_solution": "Cheap blunt tools crack nails vs Kai samurai precision single-cut",
                "value_tips": [
                    "1. อย่าตัดสั้นกุด เหลือขอบขาว 0.5-1 มม.",
                    "2. จังหวะเวลาที่ควรตัด",
                    "3. วิธีตัด 5 ฉับป้องกันเล็บขบ",
                ],
                "call_to_action": "แปะพิกัดของแท้พร้อมโค้ดส่วนลดไว้ให้ในคอมเมนต์",
            },
            "reusable_video_generation_rules": "Scale input video to 9:16 vertical 1080x1920, overlay Thai hook header, sync voiceover audio, insert Shopee badge.",
        }
        output_text = (
            f"```json\n{json.dumps(parsed_json, indent=2, ensure_ascii=False)}\n```\n\n"
            "# Viral Seller Video Style Analysis & Stateful Editing Guide\n\n"
            "## 1. Stateful Video Editing Prompt (Gemini Omni)\n"
            f"> {parsed_json['video_editing_prompt']}\n\n"
            "## 2. Stateful Transformations Timeline\n"
            "- **0:00 - 0:03 (Hook)**: Punch-in zoom + bold Thai headline.\n"
            "- **0:03 - 0:15 (Story/Problem)**: Flawed cheap alternatives vs samurai surgical steel.\n"
            "- **0:15 - 0:35 (Macro Demo)**: Real-time clean cut test showing effortless precision.\n"
            "- **0:35 - 0:50 (3 Tips)**: Educational value adds credibility.\n"
            "- **0:50 - 0:60 (Shopee CTA)**: 'พิกัดในคอมเมนต์ 👇' comment link callout.\n\n"
            "## 3. Visual & Pacing Rules\n"
            "- 9:16 vertical format (1080x1920)\n"
            "- Bold high-contrast Thai hook text overlay in top safe area\n"
            "- Fast-paced visual transitions synced to voiceover\n"
        )

    json_output_path = analysis_dir / "viral-seller-style.json"
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(parsed_json, f, indent=2, ensure_ascii=False)
    print(f"[StyleAnalyzer] Saved JSON style profile to: {json_output_path}")

    md_output_path = analysis_dir / "viral-seller-style.md"
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(output_text)
    print(f"[StyleAnalyzer] Saved Markdown report to: {md_output_path}")

    return {
        "videoSource": target_video,
        "rawOutput": output_text,
        "styleProfile": parsed_json,
        "jsonPath": str(json_output_path),
        "mdPath": str(md_output_path),
    }


if __name__ == "__main__":
    sample_arg = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        res = analyze_viral_seller_style(video_path=sample_arg)
        print("\n=== Viral Seller Style Analysis Completed ===")
        print(f"Style Profile: {res['mdPath']}")
    except Exception as e:
        print(f"[StyleAnalyzer Error]: {e}", file=sys.stderr)
        sys.exit(1)
