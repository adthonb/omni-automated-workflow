---
name: generate-video
description: Generates and renders 9:16 vertical Facebook Reels and Shopee Affiliate videos using gemini-omni-1.1-flash with multi reference images or videos in ./video/input/${product-name}/ and learned viral style.
---

# Video Generation Subagent & Skill (Python 3.14)

Generates 9:16 vertical short-form video for Facebook Reels combining multi reference images or videos from the dedicated `./video/input/${product-name}/` subdirectory, the learned viral seller style, and the synthesized voiceover audio.

## Specification

- **Model**: `gemini-omni-1.1-flash`
- **Product Media Subdirectory**: `./video/input/${product-name}/`
  - Supports multiple reference videos (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.m4v`)
  - Supports multiple reference images (`.jpg`, `.jpeg`, `.png`, `.webp`, `.avif`, `.bmp`)
- **Fallback Video Path**: `./video/input/${product-name}.mp4` or baseline `./video/input/best-sell-example.mp4`
- **Learned Video Style Source**: `./analysis/viral-seller-style.json` (from `./video/input/best-sell-example.mp4`)
- **Voiceover Audio**: `./audio/${product-name}.mp3`
- **Output Path**: `./video/output/YYYY-MM-DD/${product-name}.mp4`
- **Video Resolution**: 9:16 Vertical (1080x1920), H.264 video, AAC 192 kbps audio

## Processing Flow

1. Scans dedicated subdirectory `./video/input/${product-name}/` for all valid reference video clips and image photos (falls back to `./video/input/${product-name}.mp4`).
2. Applies the visual storyboard, multi-scene cut pacing, on-screen Thai hook text, and framing from the learned viral seller style.
3. Synchronizes with Thai voiceover audio from `./audio/${product-name}.mp3`.
4. Uses FFmpeg to render the 9:16 vertical video under `./video/output/YYYY-MM-DD/${product-name}.mp4`:
   - Multi-video concatenation with vertical scale/crop/pad.
   - Dynamic slideshow timing across all reference images.
   - Mixed media montage (video cuts + image slides).

## Usage

```bash
uv run omni-video generate-video "<product-name>"
```
