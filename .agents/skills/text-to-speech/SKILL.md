---
name: text-to-speech
description: Generates high-quality Thai voiceover audio under ./audio/${product-name}.mp3 using transcript from ./transcription/${product-name}.md and voice tone from ./myvoice.mp3 with gemini-3.1-flash-tts-preview.
---

# Text-To-Speech (TTS) Subagent & Skill (Python 3.14)

Synthesizes Thai voiceover audio matching your voice tone from `./myvoice.mp3` using transcript files.

## Specification

- **My Voice Tone**: `./myvoice.mp3`
- **Output Target**: `./audio/${product-name}.mp3` (192 kb/s MP3)
- **Input Transcript**: `./transcription/${product-name}.md` matching `product-name`
- **Voice Synthesis**: Generates audio with transcript and voice tone
- **Model**: `gemini-3.1-flash-tts-preview`
- **Languages**: Thai (`th-TH`)

## Processing Flow

1. Locates and reads `./transcription/${product-name}.md`.
2. Extracts spoken script with speech markup and director's notes.
3. Uploads `./myvoice.mp3` to Gemini File API as acoustic voice tone reference.
4. Uses `gemini-3.1-flash-tts-preview` to synthesize Thai speech matching the reference voice tone.
5. Converts generated audio to 192 kb/s MP3 and saves to `./audio/${product-name}.mp3`.

## Usage

```bash
uv run omni-video tts "<product-name>"
```
