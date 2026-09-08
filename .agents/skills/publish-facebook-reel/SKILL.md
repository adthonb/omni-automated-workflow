---
name: publish-facebook-reel
description: Publishes video reels to Facebook Pages using Meta Graph API with local Python execution.
---

# Publish Facebook Reels Skill (Python 3.14)

Publishes generated 9:16 vertical videos to Facebook Pages as Facebook Reels using the official Meta Reels Publishing API via Python.

## Reference

- [Meta Reels Publishing API Guide](https://developers.facebook.com/documentation/video-api/guides/reels-publishing.md)
- [Meta Sample Repository](https://github.com/fbsamples/reels_publishing_apis/tree/main/fb_reels_publishing_api_sample)

## API Publishing Protocol

1. **Phase 1: Start Upload Session**
   `POST https://graph.facebook.com/v26.0/{PAGE_ID}/video_reels?upload_phase=start&access_token={ACCESS_TOKEN}`
2. **Phase 2: Upload Video Binary**
   `POST {upload_url}` with header `Authorization: OAuth {ACCESS_TOKEN}` and binary payload.
3. **Phase 3: Finalize and Publish**
   `POST https://graph.facebook.com/v26.0/{PAGE_ID}/video_reels?upload_phase=finish&video_id={VIDEO_ID}&video_state=PUBLISHED&description={DESCRIPTION}`
4. **Phase 4: Status Query**
   `GET https://graph.facebook.com/v26.0/{VIDEO_ID}?fields=status,published_time`

## Environment Setup

Add credentials to `.env`:
```env
FB_PAGE_ID=your_page_id
FB_PAGE_ACCESS_TOKEN=your_page_access_token
```

## Usage

```bash
uv run omni-video publish-reel "<path-to-video.mp4>" "<description>"
```
