#!/usr/bin/env python3
"""CLI interface for Shopee Affiliate Video & Facebook Reels Pipeline."""

import json
import sys
from .orchestrator import run_interactive_command, run_orchestration_pipeline
from .skills.fb_reels_publisher import publish_facebook_reel
from .skills.memory_manager import add_memory_entry, get_memory_summary, read_memory
from .skills.shopee_scraper import scrape_shopee_product
from .subagents.style_analyzer import analyze_viral_seller_style
from .subagents.transcript_generator import generate_transcript
from .subagents.tts_generator import generate_text_to_speech
from .subagents.video_generator import generate_video
from .utils.ffmpeg_helper import convert_mp4_to_mp3


def print_help() -> None:
    print("""
Shopee Affiliate Video & Audio Orchestration CLI (Python 3.14)
Pattern: Command -> Agent -> Skill (Claude / Antigravity Compatible)

Usage:
  omni-video                         Interactive Command (Prompts for Shopee URL)
  omni-video orchestrate <url|name>  Run Phase 1 pipeline (Scrape + Transcript + TTS + Memory)
  omni-video orchestrate <url|name> --with-video  Run full pipeline including Video
  omni-video scrape <shopee-url>     Scrape Shopee product description & shop details
  omni-video transcript <url|name>   Generate Thai transcript with speech tags & memory
  omni-video tts <product-name>      Generate TTS voice audio matching ./myvoice.mp3
  omni-video memory                  View learned rules and persistent memory
  omni-video add-memory <note> [cat] Add learning/rule to MEMORY.md for next prompt
  omni-video analyze-style [file]    Learn viral selling video style (Phase 2)
  omni-video generate-video <prod>   Assemble 9:16 vertical Reels video (Phase 2)
  omni-video publish-reel <video>    Publish video to Facebook Reels via API
  omni-video convert-audio <in> <out> Convert MP4 to 192k MP3 with FFmpeg

Environment Variables (.env):
  SHOPEE_COOKIE   Optional cookie string to bypass Shopee anti-bot on PDP pages
  GEMINI_API_KEY  Google Gemini API key
""")


def main() -> None:
    args = sys.argv[1:]
    command = args[0] if args else ""

    try:
        if command in ("orchestrate", "run"):
            sub_args = args[1:]
            with_video = "--with-video" in sub_args or "-v" in sub_args
            clean_sub_args = [a for a in sub_args if a not in ("--with-video", "-v")]
            if clean_sub_args:
                target = clean_sub_args[0]
                is_url = target.startswith("http://") or target.startswith("https://") or "shopee.co.th" in target
                run_orchestration_pipeline(
                    shopee_url=target if is_url else None,
                    product_name=target if not is_url else None,
                    product_details=" ".join(clean_sub_args[1:]) if len(clean_sub_args) > 1 else "",
                    skip_video=not with_video,
                )
            else:
                run_interactive_command()

        elif command == "scrape":
            if len(args) < 2:
                print("Usage: omni-video scrape <shopee-url>", file=sys.stderr)
                sys.exit(1)
            res = scrape_shopee_product(args[1])
            print("\n=== Shopee Scraped Product Data ===")
            print(json.dumps(res, indent=2, ensure_ascii=False))

        elif command == "transcript":
            if len(args) < 2:
                print("Usage: omni-video transcript <shopee-url|product-name> [details]", file=sys.stderr)
                sys.exit(1)
            res = generate_transcript(
                product_name=args[1],
                product_details=" ".join(args[2:]) if len(args) > 2 else "",
            )
            print("\n=== Transcript & Details Generated ===")
            print(f"📄 Transcript: {res['outputPath']}")
            print(f"📋 Details:    {res['detailPath']}")

        elif command == "tts":
            if len(args) < 2:
                print("Usage: omni-video tts <product-name>", file=sys.stderr)
                sys.exit(1)
            generate_text_to_speech(product_name=args[1])

        elif command == "analyze-style":
            sample_file = args[1] if len(args) > 1 else None
            analyze_viral_seller_style(video_path=sample_file)

        elif command == "generate-video":
            if len(args) < 2:
                print("Usage: omni-video generate-video <product-name> [date-YYYY-MM-DD]", file=sys.stderr)
                sys.exit(1)
            date_str = args[2] if len(args) > 2 else None
            generate_video(product_name=args[1], date_str=date_str)

        elif command == "publish-reel":
            if len(args) < 2:
                print("Usage: omni-video publish-reel <video-path> [caption]", file=sys.stderr)
                sys.exit(1)
            caption = args[2] if len(args) > 2 else ""
            publish_facebook_reel(video_path=args[1], description=caption)

        elif command == "convert-audio":
            if len(args) < 3:
                print("Usage: omni-video convert-audio <video.mp4> <audio.mp3>", file=sys.stderr)
                sys.exit(1)
            convert_mp4_to_mp3(video_path=args[1], audio_path=args[2], bitrate="192k")
            print(f"Converted {args[1]} to {args[2]} at 192 kb/s.")

        elif command in ("memory", "get-memory"):
            print("=== Continuous Improvement Memory ===")
            print(get_memory_summary())
            print("\n" + read_memory())

        elif command in ("add-memory", "learn"):
            if len(args) < 2:
                print("Usage: omni-video add-memory <note> [category]", file=sys.stderr)
                print("Categories: copywriting, audio, niche, platform, feedback (default)", file=sys.stderr)
                sys.exit(1)
            note = args[1]
            cat = args[2] if len(args) > 2 else "feedback"
            res = add_memory_entry(category=cat, note=note, source="cli")
            print(f"✅ Memory recorded to {res['path']}:")
            print(f"   {res['bullet']}")

        elif command in ("help", "--help", "-h"):
            print_help()

        elif not command:
            run_interactive_command()

        else:
            # Treat single argument as Shopee URL or product name
            target = command
            is_url = target.startswith("http://") or target.startswith("https://") or "shopee.co.th" in target
            run_orchestration_pipeline(
                shopee_url=target if is_url else None,
                product_name=target if not is_url else None,
                product_details=" ".join(args[1:]) if len(args) > 1 else "",
            )

    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)
    except Exception as err:
        print(f"CLI Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
