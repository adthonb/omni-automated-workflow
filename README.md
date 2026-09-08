# Omni Video Orchestrator

Generate Thai Facebook Reels scripts and voiceovers from Shopee product links.

Built with Python 3.14, [uv](https://github.com/astral-sh/uv), Google Gemini, and FFmpeg.

---

## What It Does

The workflow writes story-driven scripts instead of standard product pitches, matching the tone sample in `tone.text`:

- **Shopee scraper**: Extracts specifications, sales points, and shop background from Shopee URLs. Includes cookie support for anti-bot pages and fallback parsing for short links.
- **Story-driven scripts**: Writes Thai video scripts structured around a hook, origin lore, pain-point contrast, three actionable tips, and a soft call to action.
- **Voice synthesis**: Clones the cadence, timbre, and pacing of [myvoice.mp3](myvoice.mp3) using Gemini Flash TTS and exports 192 kbps MP3 files through FFmpeg.
- **Persistent memory**: Ingests rules and corrections from [MEMORY.md](MEMORY.md) before drafting, then records run feedback for future generations.
- **Facebook Reels publishing**: Assembles 9:16 vertical video and publishes to Facebook Pages via Meta Graph API v26.0.

---

## How It Works

```
  1. Input Shopee URL
         │
         ▼
  2. Scrape Details & Shop Lore
     Extracts title, attributes, craftsmanship history, with anti-bot fallback
         │
         ▼
  3. Generate Script with Memory
     Ingests MEMORY.md + tone.text → creates ./transcription/ and ./detail/
         │
         ▼
  4. Synthesize Voiceover (TTS)
     Clones ./myvoice.mp3 tone → outputs 192 kbps MP3 in ./audio/
         │
         ▼
  5. Learn & Self-Improve
     Logs feedback and niche takeaways to MEMORY.md for future runs
```

---

## Quick Start

### 1. Prerequisites
- Python 3.14+ managed with [uv](https://github.com/astral-sh/uv)
- FFmpeg installed and available on system path

### 2. Installation
```bash
git clone https://github.com/your-username/omni-automated-workflow.git
cd omni-automated-workflow
uv sync
```

### 3. Configure Credentials
Create `.env` in the root directory (see [`.env.example`](.env.example)):
```env
# Google Gemini API (Required)
GEMINI_API_KEY="your-gemini-api-key"

# Shopee Anti-Bot Cookie (Optional - for PDP page access)
SHOPEE_COOKIE="SPC_F=...; SPC_SI=...; SPC_EC=...; SPC_U=...;"

# Meta Graph API (Optional - for direct Reels publishing)
FB_PAGE_ID="your-facebook-page-id"
FB_PAGE_ACCESS_TOKEN="your-page-access-token"
FB_GRAPH_API_VERSION="v26.0"
```

### 4. Run Interactive Mode
```bash
uv run omni-video
```
Enter a Shopee product URL when prompted. The tool scrapes product details, writes the script, synthesizes the voiceover, and prompts for feedback to append to memory.

---

## CLI Commands

| Action | Command |
|---|---|
| Interactive mode | `uv run omni-video` |
| Direct pipeline (Phase 1) | `uv run omni-video orchestrate "<shopee-url>"` |
| Pipeline with video rendering | `uv run omni-video orchestrate "<shopee-url>" --with-video` |
| Scrape Shopee URL only | `uv run omni-video scrape "<shopee-url>"` |
| Generate transcript only | `uv run omni-video transcript "<shopee-url>"` |
| Generate voiceover only | `uv run omni-video tts "<product-name>"` |
| View memory | `uv run omni-video memory` |
| Add rule to memory | `uv run omni-video add-memory "<feedback or note>" [category]` |
| Publish video to Facebook Reels | `uv run omni-video publish-reel "<video-path>" "<caption-text>"` |
| Convert MP4 to 192k MP3 | `uv run omni-video convert-audio input.mp4 output.mp3` |

---

## Slash Commands

For Antigravity CLI and compatible agent environments, the following slash commands are registered:

- `/omni-video`: Interactive orchestrator (prompts for Shopee URL)
- `/orchestrator`: Orchestrator alias command
- `/generate-transcript`: Scrape product details and write Thai script
- `/text-to-speech`: Synthesize voiceover matching reference sample
- `/manage-memory`: View or add persistent self-improvement rules
- `/generate-video`: Render vertical 9:16 Reels video (Phase 2)
- `/analyze-viral-seller`: Analyze hook structure from video sample (Phase 2)
- `/publish-facebook-reel`: Publish video to Facebook Reels via Meta Graph API

---

## Output Files and Directories

| Directory or File | Description |
|---|---|
| [`transcription/${name}.md`](transcription/) | Spoken Thai transcript with Gemini speech tags and plain voiceover text |
| [`detail/${name}.md`](detail/) | Storyboard scene cues and Facebook Reels caption with hashtags |
| [`audio/${name}.mp3`](audio/) | 192 kbps MP3 Thai voiceover |
| [`MEMORY.md`](MEMORY.md) | Copywriting rules, product niche insights, and logged user feedback |
| [`video/output/`](video/output/) | Rendered 9:16 vertical Reels videos |
| [`myvoice.mp3`](myvoice.mp3) | Reference audio sample for vocal timbre and tone |
| [`tone.text`](tone.text) | Reference script demonstrating the 5-stage storytelling structure |

---

## Continuous Improvement Memory

The transcript generator connects with [`MEMORY.md`](MEMORY.md) across runs:
1. **Before generation**: The script generator reads [`MEMORY.md`](MEMORY.md) to apply past corrections and category guidelines.
2. **After execution**: The CLI prompts for feedback and appends new notes to [`MEMORY.md`](MEMORY.md).

---

## Architecture and Agent Rules

For orchestration contracts, guardrails, and implementation details:
- [`AGENTS.md`](AGENTS.md): Orchestration guidelines and fail-closed rules
- [`GEMINI.md`](GEMINI.md): Technical implementation specification
