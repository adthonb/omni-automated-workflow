import json
import os
import sys
import time
from typing import Any
import requests

try:
    from ..config import CONFIG
except (ImportError, ValueError):
    from omni_video.config import CONFIG


def start_reel_upload_session(
    page_id: str | None = None,
    access_token: str | None = None,
    api_version: str | None = None,
) -> dict[str, str]:
    """
    Initialize Reel Upload Session (Phase 1)
    POST https://graph.facebook.com/{apiVersion}/{pageId}/video_reels?upload_phase=start
    """
    target_page_id = page_id or CONFIG["FACEBOOK"]["PAGE_ID"]
    target_token = access_token or CONFIG["FACEBOOK"]["PAGE_ACCESS_TOKEN"]
    target_version = api_version or CONFIG["FACEBOOK"]["GRAPH_API_VERSION"]

    url = f"{CONFIG['FACEBOOK']['GRAPH_API_BASE']}/{target_version}/{target_page_id}/video_reels"
    print(f"[FBReelsSkill] Initializing Reel upload session at: {url}")

    params = {
        "upload_phase": "start",
        "access_token": target_token,
    }

    res = requests.post(url, params=params, timeout=30)
    data = res.json()

    if not res.ok or data.get("error"):
        raise RuntimeError(
            f"Facebook API Session Init Error ({res.status_code}): {json.dumps(data.get('error', data))}"
        )

    print(f"[FBReelsSkill] Upload session started. Video ID: {data.get('video_id')}")
    return {
        "videoId": data["video_id"],
        "uploadUrl": data["upload_url"],
    }


def upload_reel_video_binary(
    upload_url: str,
    video_path: str,
    access_token: str | None = None,
) -> dict[str, Any]:
    """
    Upload Video Binary payload (Phase 2)
    POST {uploadUrl} with Authorization: OAuth {token}, file_size, offset
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file to publish not found: {video_path}")

    target_token = access_token or CONFIG["FACEBOOK"]["PAGE_ACCESS_TOKEN"]
    file_size = os.path.getsize(video_path)

    print(f"[FBReelsSkill] Uploading video binary ({file_size} bytes) to Meta server...")

    with open(video_path, "rb") as f:
        file_buffer = f.read()

    headers = {
        "Authorization": f"OAuth {target_token}",
        "offset": "0",
        "file_size": str(file_size),
        "Content-Type": "application/octet-stream",
    }

    res = requests.post(upload_url, headers=headers, data=file_buffer, timeout=120)
    data = res.json()

    if not res.ok or (data.get("success") is False and data.get("error")):
        raise RuntimeError(
            f"Facebook Video Binary Upload Error ({res.status_code}): {json.dumps(data.get('error', data))}"
        )

    print("[FBReelsSkill] Video binary successfully uploaded.")
    return data


def finish_and_publish_reel(
    video_id: str,
    page_id: str | None = None,
    description: str = "",
    title: str = "",
    video_state: str = "PUBLISHED",
    scheduled_publish_time: int | None = None,
    access_token: str | None = None,
    api_version: str | None = None,
) -> dict[str, Any]:
    """
    Publish the uploaded Reel (Phase 3)
    POST https://graph.facebook.com/{apiVersion}/{pageId}/video_reels?upload_phase=finish
    """
    target_page_id = page_id or CONFIG["FACEBOOK"]["PAGE_ID"]
    target_token = access_token or CONFIG["FACEBOOK"]["PAGE_ACCESS_TOKEN"]
    target_version = api_version or CONFIG["FACEBOOK"]["GRAPH_API_VERSION"]

    url = f"{CONFIG['FACEBOOK']['GRAPH_API_BASE']}/{target_version}/{target_page_id}/video_reels"
    print(f"[FBReelsSkill] Finalizing and publishing Reel {video_id}...")

    params: dict[str, Any] = {
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": video_state,
        "description": description,
        "access_token": target_token,
    }

    if title:
        params["title"] = title
    if scheduled_publish_time:
        params["scheduled_publish_time"] = scheduled_publish_time

    res = requests.post(url, params=params, timeout=30)
    data = res.json()

    if not res.ok or data.get("error"):
        raise RuntimeError(
            f"Facebook API Finish Publish Error ({res.status_code}): {json.dumps(data.get('error', data))}"
        )

    print(f"[FBReelsSkill] Reel published successfully: {data}")
    return data


def get_reel_status(
    video_id: str,
    access_token: str | None = None,
    api_version: str | None = None,
) -> dict[str, Any]:
    """
    Check Reel Publishing Status (Phase 4)
    GET https://graph.facebook.com/{apiVersion}/{videoId}?fields=status,copyright_check_status,published_time
    """
    target_token = access_token or CONFIG["FACEBOOK"]["PAGE_ACCESS_TOKEN"]
    target_version = api_version or CONFIG["FACEBOOK"]["GRAPH_API_VERSION"]

    url = (
        f"{CONFIG['FACEBOOK']['GRAPH_API_BASE']}/{target_version}/{video_id}"
        f"?fields=status,copyright_check_status,published_time&access_token={target_token}"
    )

    res = requests.get(url, timeout=30)
    data = res.json()

    if not res.ok or data.get("error"):
        raise RuntimeError(
            f"Facebook API Status Check Error ({res.status_code}): {json.dumps(data.get('error', data))}"
        )

    return data


def publish_facebook_reel(
    video_path: str,
    description: str = "",
    title: str = "",
    page_id: str | None = None,
    access_token: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Complete End-to-End Local Execution of Facebook Reels Publishing Skill
    """
    print("\n" + "=" * 40)
    print("[Skill: Publish Facebook Reel] Starting")
    print(f"Video File: {video_path}")
    print(f"Title: {title or '(auto)'}")
    print("=" * 40 + "\n")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file does not exist at: {video_path}")

    target_page_id = page_id or CONFIG["FACEBOOK"]["PAGE_ID"]
    target_token = access_token or CONFIG["FACEBOOK"]["PAGE_ACCESS_TOKEN"]

    if not target_page_id or not target_token:
        if dry_run or not os.getenv("FB_PAGE_ACCESS_TOKEN"):
            file_size = os.path.getsize(video_path)
            print("[FBReelsSkill] Notice: FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN not set in environment.")
            print("[FBReelsSkill] Running in simulated / dry-run verification mode.")
            print(f"[FBReelsSkill] Validated local video file: {video_path} ({file_size} bytes)")
            print("[FBReelsSkill] Ready to publish to Page when FB_PAGE_ID & FB_PAGE_ACCESS_TOKEN are provided in .env")
            return {
                "success": True,
                "dryRun": True,
                "videoPath": video_path,
                "simulatedVideoId": f"sim_reel_{int(time.time() * 1000)}",
                "description": description,
            }

    session = start_reel_upload_session(page_id=target_page_id, access_token=target_token)

    upload_reel_video_binary(
        upload_url=session["uploadUrl"],
        video_path=video_path,
        access_token=target_token,
    )

    publish_result = finish_and_publish_reel(
        page_id=target_page_id,
        video_id=session["videoId"],
        description=description,
        title=title,
        access_token=target_token,
    )

    status = None
    try:
        status = get_reel_status(video_id=session["videoId"], access_token=target_token)
        print("[FBReelsSkill] Current Status:", status)
    except Exception as e:
        print(f"[FBReelsSkill] Status query notice: {e}", file=sys.stderr)

    return {
        "success": True,
        "videoId": session["videoId"],
        "publishResult": publish_result,
        "status": status,
    }


if __name__ == "__main__":
    target_video = sys.argv[1] if len(sys.argv) > 1 else ""
    target_desc = sys.argv[2] if len(sys.argv) > 2 else "รีวิวสินค้า Shopee ยอดฮิต พิกัดในคอมเมนต์ 👇"

    if not target_video:
        print("Usage: python fb_reels_publisher.py <path-to-video.mp4> [description]", file=sys.stderr)
        sys.exit(1)

    try:
        res = publish_facebook_reel(video_path=target_video, description=target_desc)
        print("\n=== Reel Publishing Process Finished ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[FBReelsSkill Error]: {e}", file=sys.stderr)
        sys.exit(1)
