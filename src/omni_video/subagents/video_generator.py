import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    from ..config import CONFIG, get_date_string
except (ImportError, ValueError):
    from omni_video.config import CONFIG, get_date_string
try:
    from ..utils.ffmpeg_helper import assemble_reels_video
except (ImportError, ValueError):
    from omni_video.utils.ffmpeg_helper import assemble_reels_video
try:
    from ..utils.gemini_client import get_gemini_client, with_retry
except (ImportError, ValueError):
    from omni_video.utils.gemini_client import get_gemini_client, with_retry


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def scan_media_directory(media_dir: Path) -> tuple[list[str], list[str]]:
    """
    Scan a directory for supported image and video files.
    Returns (videos, images) lists with absolute paths, sorted alphabetically.
    """
    if not media_dir.is_dir():
        return [], []

    videos: list[str] = []
    images: list[str] = []
    for entry in sorted(media_dir.iterdir()):
        if entry.is_file():
            ext = entry.suffix.lower()
            if ext in SUPPORTED_VIDEO_EXTENSIONS:
                videos.append(str(entry.resolve()))
            elif ext in SUPPORTED_IMAGE_EXTENSIONS:
                images.append(str(entry.resolve()))
    return videos, images


def read_learned_style() -> dict[str, Any] | None:
    """Read the learned viral seller style profile from ./analysis/viral-seller-style.json."""
    json_path = Path(CONFIG["PATHS"]["ANALYSIS_DIR"]) / "viral-seller-style.json"
    if json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def generate_video(
    product_name: str,
    product_video_path: str | None = None,
    date_str: str | None = None,
    output_dir: str | None = None,
    audio_path: str | None = None,
    transcript_path: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Subagent: Video generation
    Model: gemini-omni-1.1-flash
    Original product media subdirectory: ./video/input/${product-name}/
    Supports:
    - Multiple reference images (.jpg, .png, .webp, etc.)
    - Multiple reference videos (.mp4, .mov, .mkv, etc.)
    - Legacy single video fallback (./video/input/${product-name}.mp4)
    Use the video style learned to generate the product video
    Output Path: ./video/output/YYYY-MM-DD/${product-name}.mp4
    """
    if not product_name:
        raise ValueError("Product name is required for video generation.")

    clean_name = re.sub(r'[/\\?%*:|"<>]+', "-", product_name.strip())
    target_date = date_str or get_date_string()

    target_output_dir = Path(output_dir) if output_dir else Path(CONFIG["PATHS"]["VIDEO_OUTPUT_BASE"]) / target_date
    target_output_dir.mkdir(parents=True, exist_ok=True)

    product_media_dir = Path(CONFIG["PATHS"]["VIDEO_INPUT_BASE"]) / clean_name
    # Ensure dedicated subdirectory exists for user media ingestion
    product_media_dir.mkdir(parents=True, exist_ok=True)

    discovered_videos: list[str] = []
    discovered_images: list[str] = []

    if product_video_path:
        custom_p = Path(product_video_path)
        if custom_p.is_dir():
            discovered_videos, discovered_images = scan_media_directory(custom_p)
        elif custom_p.is_file():
            if custom_p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                discovered_images = [str(custom_p.resolve())]
            else:
                discovered_videos = [str(custom_p.resolve())]
    else:
        # 1. Primary: scan dedicated subdirectory ./video/input/${product-name}/
        discovered_videos, discovered_images = scan_media_directory(product_media_dir)

        # 2. Fallbacks if directory is empty
        if not discovered_videos and not discovered_images:
            legacy_video = Path(CONFIG["PATHS"]["VIDEO_INPUT_BASE"]) / f"{clean_name}.mp4"
            dated_video = Path(CONFIG["PATHS"]["VIDEO_INPUT_BASE"]) / target_date / f"{clean_name}.mp4"

            if legacy_video.exists():
                discovered_videos = [str(legacy_video.resolve())]
            elif dated_video.exists():
                discovered_videos = [str(dated_video.resolve())]
            elif os.path.exists(CONFIG["PATHS"]["BEST_SELL_SAMPLE"]):
                print(
                    f'[VideoGenerator] Notice: No media in "{product_media_dir}". '
                    f'Using baseline sample "{CONFIG["PATHS"]["BEST_SELL_SAMPLE"]}" as reference template.'
                )
                discovered_videos = [CONFIG["PATHS"]["BEST_SELL_SAMPLE"]]

    primary_reference = (
        discovered_videos[0]
        if discovered_videos
        else (discovered_images[0] if discovered_images else str(product_media_dir))
    )

    target_audio = audio_path or str(Path(CONFIG["PATHS"]["AUDIO_DIR"]) / f"{clean_name}.mp3")
    target_transcript = transcript_path or str(
        Path(CONFIG["PATHS"]["TRANSCRIPTION_DIR"]) / f"{clean_name}.md"
    )
    target_detail = str(
        Path(CONFIG["PATHS"].get("DETAIL_DIR", Path(CONFIG["PROJECT_ROOT"]) / "detail")) / f"{clean_name}.md"
    )
    target_model = model or CONFIG["MODELS"]["VIDEO"]

    print("\n" + "=" * 55)
    print(f'🎥  [Subagent: Video Generation] Starting for "{clean_name}"')
    print(f"🎯 Model: {target_model}")
    print(f"📁 Media Subdirectory: {product_media_dir}")
    print(f"📹 Reference Videos ({len(discovered_videos)}): {[Path(v).name for v in discovered_videos]}")
    print(f"🖼️  Reference Images ({len(discovered_images)}): {[Path(i).name for i in discovered_images]}")
    print(f"🎙️ Voiceover Audio: {target_audio}")
    print(f"📂 Output Directory: {target_output_dir}")
    print("=" * 55 + "\n")

    learned_style = read_learned_style()
    if learned_style:
        print("[VideoGenerator] Applying learned viral video style from: ./analysis/viral-seller-style.json")

    transcript_text = ""
    if os.path.exists(target_transcript):
        transcript_text = Path(target_transcript).read_text(encoding="utf-8")

    detail_text = ""
    if os.path.exists(target_detail):
        detail_text = Path(target_detail).read_text(encoding="utf-8")

    client = get_gemini_client()

    editing_prompt_directive = (
        learned_style.get("video_editing_prompt", "")
        if learned_style
        else "Transform input video into 9:16 vertical high-retention video with bold Thai hook header and fast cuts."
    )
    stateful_timeline = (
        learned_style.get("stateful_transformations", [])
        if learned_style
        else []
    )

    media_inventory = f"""
Media Subdirectory: {product_media_dir}
Reference Video Clips ({len(discovered_videos)}): {', '.join(Path(v).name for v in discovered_videos) if discovered_videos else 'None'}
Reference Photos/Images ({len(discovered_images)}): {', '.join(Path(i).name for i in discovered_images) if discovered_images else 'None'}
"""

    visual_plan: dict[str, Any] | None = None
    try:
        prompt = f"""
You are an expert video director creating high-converting 9:16 vertical Shopee Affiliate and Facebook Reels videos using Gemini Omni Stateful Video Editing (https://ai.google.dev/gemini-api/docs/omni#stateful-video-editing).

Task: Generate a 9:16 vertical video layout and stateful editing storyboard combining the product reference media with the learned viral seller style.

Product: {clean_name}
Reference Media Inventory:
{media_inventory}

Learned Stateful Editing Directive:
\"\"\"
{editing_prompt_directive}
\"\"\"

Learned Stateful Timeline:
\"\"\"
{json.dumps(stateful_timeline, indent=2, ensure_ascii=False)}
\"\"\"

Transcript Excerpt:
\"\"\"
{transcript_text[:1500]}
\"\"\"
{f'Storyboard & Visual Cues (from ./detail):\n\"\"\"\n{detail_text[:1500]}\n\"\"\"' if detail_text else ''}

Generate a JSON storyboard plan:
1. "visual_theme": High-contrast, dynamic TikTok/Reels style.
2. "hook_overlay": Punchy Thai hook text for the first 3 seconds (e.g. "รู้งี้ซื้อตั้งนานแล้ว! 🔥", "ไอเทมเปลี่ยนชีวิต ✨").
3. "aspect_ratio": "9:16 (1080x1920)"
4. "transitions": Scene cut pacing across reference videos and images.
5. "cta_badge": "พิกัดในคอมเมนต์ 👇"
6. "stateful_editing_notes": Instructions for downstream rendering.

Return JSON in ```json ... ```.
"""
        response = with_retry(
            lambda: client.models.generate_content(
                model=target_model,
                contents=prompt,
            )
        )
        txt = getattr(response, "text", "") or ""
        m = re.search(r"```json\s*([\s\S]*?)\s*```", txt)
        if m:
            visual_plan = json.loads(m.group(1))
    except Exception as err:
        print(f"[VideoGenerator] Omni model planning notice: {err}", file=sys.stderr)

    final_video_path = str(target_output_dir / f"{clean_name}.mp4")
    compat_video_path = str(Path(CONFIG["PATHS"]["VIDEO_OUTPUT_BASE"]) / f"{clean_name}.mp4")

    hook_text = ""
    if visual_plan and visual_plan.get("hook_overlay"):
        hook_text = visual_plan["hook_overlay"]
    elif learned_style and learned_style.get("visual_style", {}).get("hook_visual_pacing"):
        hook_text = learned_style["visual_style"]["hook_visual_pacing"]
    else:
        hook_text = f"รีวิวของดี: {clean_name}"

    print("[VideoGenerator] Assembling vertical 9:16 Reels video (1080x1920) with multi-asset sequence & voiceover audio...")
    assemble_reels_video(
        video_paths=discovered_videos,
        image_paths=discovered_images,
        audio_path=target_audio if os.path.exists(target_audio) else None,
        output_path=final_video_path,
        title_text=clean_name,
        hook_text=hook_text,
    )

    try:
        shutil.copyfile(final_video_path, compat_video_path)
    except Exception:
        pass

    print(f"\n🎉 [VideoGenerator] Video successfully generated:")
    print(f"   -> Target Output: {final_video_path}")
    print(f"   -> Compatibility: {compat_video_path}\n")

    return {
        "productName": clean_name,
        "dateStr": target_date,
        "productMediaDir": str(product_media_dir),
        "referenceVideos": discovered_videos,
        "referenceImages": discovered_images,
        "originalProductVideo": primary_reference,
        "videoPath": final_video_path,
        "compatVideoPath": compat_video_path,
        "visualPlan": visual_plan,
        "learnedStyleUsed": learned_style is not None,
    }


if __name__ == "__main__":
    prod_name = sys.argv[1] if len(sys.argv) > 1 else "kai-nail-clipper"
    date_arg = sys.argv[2] if len(sys.argv) > 2 else None
    input_arg = sys.argv[3] if len(sys.argv) > 3 else None
    try:
        res = generate_video(product_name=prod_name, date_str=date_arg, product_video_path=input_arg)
        print("=== Video Generation Completed ===")
        print(f"Media Dir: {res['productMediaDir']}")
        print(f"Videos: {len(res['referenceVideos'])}, Images: {len(res['referenceImages'])}")
        print(f"Output: {res['videoPath']}")
    except Exception as e:
        print(f"[VideoGenerator Error]: {e}", file=sys.stderr)
        sys.exit(1)
