---
name: analyze-viral-seller
description: Analyzes viral selling video and audio in Thai to extract winning hook formulas, visual pacing, and psychological triggers.
---

# Analyze Viral Seller Video Style Subagent & Skill (Python 3.14)

Analyzes top-performing viral video and audio to extract visual editing and sales copywriting frameworks.

## Specification

- **Model**: `gemini-3.7-flash`
- **Video Source**: `./video/input/best-sell-example.mp4` (or `./test/best-sell-example.mp3`)
- **Language**: Thai
- **Omni Video Editing Reference**: https://ai.google.dev/gemini-api/docs/omni#stateful-video-editing
- **Target Outputs**:
  - Structured profile & Omni stateful editing prompts: `./analysis/viral-seller-style.json`
  - Comprehensive report & editing guide: `./analysis/viral-seller-style.md`

## Audio Extraction

To convert reference MP4 video to 192k MP3 for audio processing:
```bash
ffmpeg -i video.mp4 -vn -c:a libmp3lame -b:a 192k audio.mp3
```

## Usage

```bash
uv run omni-video analyze-style
```
