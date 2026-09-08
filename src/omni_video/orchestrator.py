import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .config import CONFIG, get_date_string
    from .skills.fb_reels_publisher import publish_facebook_reel
    from .skills.memory_manager import add_memory_entry, get_memory_summary, read_memory, record_run_memory
    from .skills.shopee_scraper import scrape_shopee_product
    from .subagents.style_analyzer import analyze_viral_seller_style
    from .subagents.transcript_generator import generate_transcript
    from .subagents.tts_generator import generate_text_to_speech
    from .subagents.video_generator import generate_video
except (ImportError, ValueError):
    from omni_video.config import CONFIG, get_date_string
    from omni_video.skills.fb_reels_publisher import publish_facebook_reel
    from omni_video.skills.memory_manager import add_memory_entry, get_memory_summary, read_memory, record_run_memory
    from omni_video.skills.shopee_scraper import scrape_shopee_product
    from omni_video.subagents.style_analyzer import analyze_viral_seller_style
    from omni_video.subagents.transcript_generator import generate_transcript
    from omni_video.subagents.tts_generator import generate_text_to_speech
    from omni_video.subagents.video_generator import generate_video


def extract_caption(detail_path: str | None = None, transcript_path: str | None = None) -> str:
    """Extract Facebook Reels post caption from detail file or transcript fallback."""
    paths_to_check = [p for p in (detail_path, transcript_path) if p and os.path.exists(p)]
    for path in paths_to_check:
        content = Path(path).read_text(encoding="utf-8")
        match = re.search(
            r"##\s*(?:\d+\.\s*)?Facebook Reels Post Caption[\s\S]*?\n([\s\S]*?)$",
            content,
            re.IGNORECASE,
        )
        if match and match.group(1).strip():
            return match.group(1).strip()
    return ""


def extract_caption_from_transcript(transcript_path: str) -> str:
    """Extract caption from transcript or detail file (backwards compatible)."""
    detail_dir = Path(CONFIG["PATHS"].get("DETAIL_DIR", Path(transcript_path).parent.parent / "detail"))
    detail_path = str(detail_dir / Path(transcript_path).name)
    return extract_caption(detail_path=detail_path, transcript_path=transcript_path)


def run_orchestration_pipeline(
    shopee_url: str | None = None,
    product_name: str | None = None,
    product_details: str = "",
    product_video_path: str | None = None,
    affiliate_link: str | None = None,
    date_str: str | None = None,
    skip_style_analysis: bool = True,
    skip_video: bool = True,
    publish_to_reels: bool = False,
    shopee_cookie: str | None = None,
    feedback: str | None = None,
    learnings: list[str] | None = None,
) -> dict[str, Any]:
    """
    Programmatic Orchestrator Pipeline implementing Command -> Agent -> Skill.
    Step 1: Input Shopee URL & Scrape Product Description
    Step 2: Generate Transcript reflecting scraped Shopee description & persistent memory
    Step 3: Text-to-Speech (TTS Voiceover)
    Step 4: Video Generation (Phase 2 - Deferred)
    Step 5: Skill: Facebook Reels Publishing (On-Demand)
    Step 6: Skill: Memory & Self-Improvement (Record Learnings to MEMORY.md for Next Prompt)
    """
    # Detect whether input is a Shopee URL or product-name
    if not shopee_url and product_name:
        if product_name.startswith("http://") or product_name.startswith("https://") or "shopee.co.th" in product_name:
            shopee_url = product_name
            product_name = None

    if not shopee_url and not product_name:
        raise ValueError("Execution Contract Violation: Shopee URL (or product-name) is required to run orchestration pipeline.")

    target_date = date_str or get_date_string()
    results: dict[str, Any] = {
        "dateStr": target_date,
        "timestamp": datetime.now().isoformat(),
        "steps": {},
    }

    scraped: dict[str, Any] | None = None
    clean_name = ""
    product_title = ""

    # STEP 1: Input Shopee URL & Scrape Product Description (Phase 1 Active)
    if shopee_url:
        print("\n" + "=" * 60)
        print(f'🛒 [Command: Omni Video Orchestrator] Starting for Shopee URL')
        print(f"🔗 URL: {shopee_url}")
        print(f"📅 Target Date: {target_date}")
        print(f"⚙️ Execution Mode: Phase 1 Active (Scrape + Transcript + TTS) | Phase 2 Video: {'Active' if not skip_video else 'Deferred'}")
        print("=" * 60 + "\n")

        print("\n--- [Step 1/5] Skill: Scrape Product Description from Shopee ---")
        scraped = scrape_shopee_product(shopee_url, cookie=shopee_cookie)
        clean_name = scraped["product_name"]
        product_title = scraped["title"]
        affiliate_link = affiliate_link or scraped["url"]
        combined_details = f"{product_details}\n\n{scraped['full_summary']}".strip()

        results["steps"]["shopeeScraper"] = {
            "status": "success",
            "url": scraped["url"],
            "title": product_title,
            "productName": clean_name,
            "shopName": scraped.get("shop_name", ""),
            "scrapeSource": scraped["scrape_source"],
            "hasCookie": scraped["has_cookie"],
            "antiBotEncountered": scraped["anti_bot_encountered"],
        }
    else:
        clean_name = re.sub(r'[/\\?%*:|"<>]+', "-", (product_name or "").strip())
        product_title = clean_name
        combined_details = product_details
        affiliate_link = affiliate_link or "https://shope.ee/affiliate-link"

        print("\n" + "=" * 60)
        print(f'🎬 [Command: Omni Video Orchestrator] Starting for: "{clean_name}"')
        print(f"📅 Target Date: {target_date}")
        print(f"⚙️ Execution Mode: Phase 1 Active (Transcript + TTS) | Phase 2 Video: {'Active' if not skip_video else 'Deferred'}")
        print("=" * 60 + "\n")

    results["productName"] = clean_name

    # STEP 2: Generate Transcript reflecting scraped Shopee description (Phase 1 Active)
    print("\n--- [Step 2/5] Subagent: Generate Transcript (Reflecting Shopee Product) ---")
    transcript_res = generate_transcript(
        product_name=clean_name,
        product_details=combined_details,
        affiliate_link=affiliate_link,
        model=CONFIG["MODELS"]["TRANSCRIPT"],
        scraped_data=scraped,
    )
    transcript_path = transcript_res.get("outputPath", "")
    detail_path = transcript_res.get("detailPath", "")
    
    # Fail-closed guardrail: Validate transcript output
    if not transcript_path or not os.path.exists(transcript_path):
        raise RuntimeError(f"Fail-closed Guardrail: Transcript file not created at {transcript_path}. Aborting pipeline.")
    
    results["steps"]["transcript"] = {
        "status": "success",
        "path": transcript_path,
        "detailPath": detail_path,
        "title": product_title,
    }

    # STEP 3: Text-to-Speech Generation (Phase 1 Active)
    print("\n--- [Step 3/5] Subagent: Text-to-Speech (TTS Voiceover) ---")
    tts_res = generate_text_to_speech(
        product_name=clean_name,
        transcript_path=transcript_path,
        model=CONFIG["MODELS"]["TTS"],
        voice_tone_file=CONFIG["PATHS"]["VOICE_FILE"],
    )
    audio_path = tts_res.get("audioPath", "")

    # Fail-closed guardrail: Validate audio output
    if not audio_path or not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        raise RuntimeError(f"Fail-closed Guardrail: TTS Audio file missing or empty at {audio_path}. Aborting pipeline.")

    results["steps"]["tts"] = {
        "status": "success",
        "path": audio_path,
        "sizeBytes": os.path.getsize(audio_path),
    }

    # Style learning step status record
    results["steps"]["styleAnalysis"] = {"status": "skipped_deferred"}

    # STEP 4: Video Generation (Phase 2 - Deferred / Skipped at this moment)
    print("\n--- [Step 4/5] Subagent: Video Generation ---")
    video_path: str | None = None
    product_media_dir = str(Path(CONFIG["PATHS"]["VIDEO_INPUT_BASE"]) / clean_name)
    if skip_video:
        print("[Orchestrator] Video Generation is SKIPPED AT THIS MOMENT (Phase 2 Deferred).")
        print("              Audio and transcript are ready. To render video, use 'omni-video generate-video'.")
        print(f"              Reference media directory: ./video/input/{clean_name}/")
        results["steps"]["video"] = {
            "status": "skipped_deferred",
            "note": "Phase 2 deferred per Implementation.md",
            "mediaDir": product_media_dir,
        }
    else:
        video_res = generate_video(
            product_name=clean_name,
            product_video_path=product_video_path,
            date_str=target_date,
            audio_path=audio_path,
            transcript_path=transcript_path,
            model=CONFIG["MODELS"]["VIDEO"],
        )
        video_path = video_res["videoPath"]
        results["steps"]["video"] = {
            "status": "success",
            "videoPath": video_path,
            "compatVideoPath": video_res["compatVideoPath"],
            "mediaDir": video_res.get("productMediaDir", product_media_dir),
            "referenceVideos": video_res.get("referenceVideos", []),
            "referenceImages": video_res.get("referenceImages", []),
        }

    # STEP 5: Skill: Facebook Reels Publishing (On-Demand)
    print("\n--- [Step 5/5] Skill: Facebook Reels Publishing ---")
    caption = (
        extract_caption(detail_path=detail_path, transcript_path=transcript_path)
        or f"รีวิว {product_title or clean_name} ไอเทมเด็ด Shopee พิกัดในคอมเมนต์เลยนะครับ 👇 #ShopeeTH #ของดีบอกต่อ"
    )

    if video_path and (publish_to_reels or os.getenv("AUTO_PUBLISH_REELS") == "true"):
        pub_res = publish_facebook_reel(
            video_path=video_path,
            description=caption,
            title=product_title or clean_name,
        )
        results["steps"]["reelsPublishing"] = {
            "status": "dry_run" if pub_res.get("dryRun") else "published",
            "details": pub_res,
        }
    elif video_path:
        print("[Orchestrator] Reels publishing ready on-demand. To publish, run:")
        print(f'  uv run omni-video publish-reel "{video_path}"')
        results["steps"]["reelsPublishing"] = {
            "status": "ready_to_publish",
            "videoPath": video_path,
            "suggestedCaption": caption,
        }
    else:
        print("[Orchestrator] Reels post caption prepared from transcript.")
        results["steps"]["reelsPublishing"] = {
            "status": "caption_ready",
            "suggestedCaption": caption,
        }

    # STEP 6: Skill: Memory & Self-Improvement (Record Learnings for Next Prompt)
    print("\n--- [Step 6/6] Skill: Memory & Self-Improvement (Record Learnings) ---")
    inferred_learnings = list(learnings or [])
    if not inferred_learnings:
        inferred_learnings.append(f"Product '{clean_name}': generated 5-stage soft-sell transcript reflecting Shopee PDP.")
        if results["steps"].get("shopeeScraper", {}).get("shopName"):
            inferred_learnings.append(f"Shop '{results['steps']['shopeeScraper']['shopName']}' lore integrated into credibility hook.")
        inferred_learnings.append("Synthesized 192k audio voice-matched with ./myvoice.mp3.")

    mem_res = record_run_memory(
        product_name=clean_name,
        product_title=product_title,
        url=results["steps"].get("shopeeScraper", {}).get("url") or shopee_url,
        transcript_path=transcript_path,
        audio_path=audio_path,
        feedback=feedback,
        learnings=inferred_learnings,
    )
    results["steps"]["memory"] = {
        "status": "success",
        "path": mem_res["path"],
        "summary": mem_res.get("summary", ""),
    }
    print(f"🧠 Memory Logged: {mem_res['path']}")
    print("   Knowledge and feedback will be loaded on the next prompt for continuous improvement.")

    # Output Summary
    print("\n" + "=" * 60)
    print("🎉 [Omni Video Orchestrator] Output Summary")
    print("=" * 60)
    if "shopeeScraper" in results["steps"]:
        print(f"🛒 Shopee Product: {results['steps']['shopeeScraper'].get('title', clean_name)[:60]}")
        if results['steps']['shopeeScraper'].get('shopName'):
            print(f"🏪 Shop:           {results['steps']['shopeeScraper'].get('shopName')}")
        print(f"🔗 Shopee URL:     {results['steps']['shopeeScraper'].get('url')[:70]}...")
    else:
        print(f"📦 Product:        {clean_name}")
    print(f"📄 Transcript:     {results['steps']['transcript']['path']}")
    if results["steps"]["transcript"].get("detailPath"):
        print(f"📋 Details:        {results['steps']['transcript']['detailPath']}")
    print(f"🎙️ Audio (192k):   {results['steps']['tts']['path']} ({results['steps']['tts'].get('sizeBytes', 0)} bytes)")
    if results["steps"]["video"].get("status") == "success":
        print(f"🎥 Video:          {results['steps']['video']['videoPath']}")
        v_cnt = len(results["steps"]["video"].get("referenceVideos", []))
        i_cnt = len(results["steps"]["video"].get("referenceImages", []))
        if v_cnt > 0 or i_cnt > 0:
            print(f"📁 Reference Media:{results['steps']['video'].get('mediaDir')} ({v_cnt} vids, {i_cnt} imgs)")
    else:
        print(f"🎥 Video:          [Deferred - Phase 2] (Media folder: ./video/input/{clean_name}/)")
    print(f"📝 Caption:        {caption[:80]}...")
    if "memory" in results["steps"]:
        print(f"🧠 Memory Log:     {results['steps']['memory']['path']} (Loaded in next prompt for self-improvement)")
    print("=" * 60 + "\n")

    return results


def run_interactive_command() -> None:
    """
    Interactive Command Entry Point
    Implements: "1. change step one to input Shopee URL instead of product-name"
    """
    print("\n" + "=" * 60)
    print("🌟  Shopee Affiliate & Facebook Reels Orchestrator (Python)  🌟")
    print("=" * 60 + "\n")

    try:
        shopee_input = input("👉 Enter Shopee product URL (or product-name) to generate audio and video: ").strip()
        if not shopee_input:
            print("❌ Input cannot be empty. Exiting.")
            return

        product_details = input(
            "📝 (Optional) Additional selling points [Press Enter to auto-extract from Shopee]: "
        ).strip()

        video_answer = input("🎥 Render video now? (y/N) [Default: N (Phase 1 focus: Scrape + Transcript + TTS)]: ").strip().lower()
        skip_video = video_answer != "y"

        publish_answer = input("🚀 Publish to Facebook Reels now? (y/N): ").strip().lower()
        publish_to_reels = publish_answer == "y"

        is_url = shopee_input.startswith("http://") or shopee_input.startswith("https://") or "shopee.co.th" in shopee_input
        pipeline_res = run_orchestration_pipeline(
            shopee_url=shopee_input if is_url else None,
            product_name=shopee_input if not is_url else None,
            product_details=product_details,
            skip_video=skip_video,
            publish_to_reels=publish_to_reels,
        )

        feedback_note = input("\n💡 Any feedback or memory notes to remember for next prompt? [Press Enter to skip]: ").strip()
        if feedback_note:
            clean_ref = pipeline_res.get("productName", shopee_input)
            mem_add = add_memory_entry(category="feedback", note=f"Feedback on {clean_ref}: {feedback_note}", source="user")
            print(f"✅ Memory saved to {mem_add['path']}! Future prompts will incorporate this guidance.")
    except (KeyboardInterrupt, EOFError):
        print("\n\nExecution cancelled by user.")
    except Exception as err:
        print(f"\n❌ [Orchestrator Execution Error]: {err}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg1 = sys.argv[1]
        arg2 = sys.argv[2] if len(sys.argv) > 2 else ""
        try:
            is_url = arg1.startswith("http://") or arg1.startswith("https://") or "shopee.co.th" in arg1
            run_orchestration_pipeline(
                shopee_url=arg1 if is_url else None,
                product_name=arg1 if not is_url else None,
                product_details=arg2,
            )
        except Exception as e:
            print(f"[Orchestrator Error]: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        run_interactive_command()
