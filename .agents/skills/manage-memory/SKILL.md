---
name: manage-memory
description: Manages persistent memory, learned copywriting guidelines, and user feedback in MEMORY.md for continuous self-improvement across prompts.
---

# Manage Memory Skill (`/manage-memory`)

Manages the persistent memory system (`./MEMORY.md`). The memory file stores high-converting copywriting patterns, audio pacing rules, product niche insights, scraper quirks, and user feedback to ensure the agent continuously improves with every prompt.

## How Continuous Improvement Works

1. **Prior to Generation**: Subagents (such as Transcript Generator) read `./MEMORY.md` and dynamically inject its rules and feedback into the prompt to guide output quality.
2. **After Pipeline Runs**: Step 6 automatically records the run metadata, product niche, and results into `./MEMORY.md`.
3. **Upon User Feedback / Corrections**: Whenever the user provides guidance, corrections, or stylistic preferences, append the note to `./MEMORY.md`.

## Memory Categories

- `copywriting`: Hook styles, storytelling blueprint, speech markup tags, Thai phrasing.
- `audio`: TTS tone, pacing pauses, volume and pronunciation.
- `niche`: Product-specific insights (food & snacks, tools, beauty, tech gadgets).
- `platform`: Shopee scraper, anti-bot cookie, Facebook Reels specs.
- `feedback`: User preferences, corrections, and evolution notes.

## Usage Commands

```bash
# View current memory and learned rules
uv run omni-video memory

# Add a learned rule or user feedback
uv run omni-video add-memory "Highlight product weight and expiry date for food items" niche

# Add general feedback
uv run omni-video add-memory "User prefers energetic tone for snacks" feedback
```
