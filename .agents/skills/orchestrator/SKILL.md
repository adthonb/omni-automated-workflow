---
name: orchestrator
description: >-
  Interactive Command orchestrator for Shopee Affiliate Video & Facebook Reels.
  Prompts the user for Shopee URL, scrapes product description with anti-bot support,
  and delegates to Transcript and TTS subagents following the Command -> Agent -> Skill architecture.
---

# Omni Video Orchestrator Command (`/orchestrator`)

The master user entry point for the Shopee affiliate marketing Facebook Reels generation pipeline. It coordinates the entire workflow following the **Command → Agent → Skill** architecture.

## Execution Contract (Non-Negotiable)

You MUST complete this command by strictly following these non-negotiable constraints:

1. **Mandatory Interactive Prompting**: If `shopee-url` was not explicitly provided by the user in their prompt, you MUST use the `ask_question` tool (or prompt the user) to collect `shopee-url` (or product-name as fallback). Never invent or assume a product.
2. **Automated Shopee Scraping**: Step 1 MUST scrape product description, specifications, and shop lore from the provided Shopee URL before generating the script.
3. **Anti-Bot & Cookie Support**: Shopee employs anti-bot protection. Support the `SHOPEE_COOKIE` environment variable to bypass anti-bot challenges and fetch detailed PDP descriptions. If no cookie is provided, gracefully fall back to URL slug parsing and the Shop API.
4. **Delegation Only**: You are strictly forbidden from writing or improvising the transcript or audio directly in this command turn. You MUST delegate to the specialist subagents.
5. **Fail-Closed Guardrails**:
   - If the user provides an empty URL/product name, STOP immediately.
   - If the Transcript Subagent fails to generate `./transcription/${product-name}.md`, DO NOT proceed to TTS. Report the failure and STOP.
   - If the TTS Subagent fails to produce `./audio/${product-name}.mp3` or outputs an empty file (0 bytes), DO NOT proceed. Report the failure and STOP.
6. **Preserve Non-Hard-Sell Pattern**: The transcript MUST strictly reflect the scraped Shopee product description while following the 5-stage storytelling formula deconstructed from `./tone.text`.
7. **Honor Phased Execution**: Video Generation (`gemini-omni-1.1-flash`) and Style Learning are **SKIPPED AT THIS MOMENT** (Phase 2 Deferred) unless the user explicitly requests video rendering.
8. **Continuous Self-Improvement (Memory Persistence)**: The pipeline MUST load `./MEMORY.md` before generating scripts to adhere to learned rules, tone nuances, and user feedback. Step 6 MUST persist run learnings and user feedback to `./MEMORY.md` to improve subsequent prompts.

---

## Workflow

### Step 1: Input Shopee URL & Scrape Product Description

If the user did not specify the Shopee URL in their message:
- Prompt the user using `ask_question` or interactive prompt:
  - **Question**: "What is the Shopee product URL to generate audio and video?"
  - **Optional Details**: "Additional selling points or features [Press Enter to auto-extract from Shopee]?"

Execute the Shopee Scraper skill:
```bash
uv run python src/skills/shopee_scraper.py "${shopee-url}"
# or
uv run omni-video scrape "${shopee-url}"
```

**What this skill does**:
- Resolves short links (`shope.ee`, `shp.ee`) to full canonical Shopee URLs.
- Extracts `shop_id`, `item_id`, and decoded product slug.
- Connects to Shopee PDP API (`/api/v4/pdp/get_pc`) using `SHOPEE_COOKIE` if configured.
- Extracts shop name and heritage lore via `/api/v4/shop/get_shop_detail`.
- Produces clean product slug for file naming (e.g., `น้ำพริกกากหมู-40-กรัม`).

---

### Step 2: Delegate to Transcript Subagent (`gemini-3.8-flash`)

Execute the Transcript Generator subagent:
```bash
uv run python src/subagents/transcript_generator.py "${shopee-url}"
# or
uv run omni-video transcript "${shopee-url}"
```

**What this subagent does**:
- Ingests scraped Shopee product description and shop lore.
- Analyzes `./tone.text` to apply the **5-Stage Non-Hard-Sell Copywriting Blueprint**:
  1. *Curiosity & Intrigue Hook (0–5s)*: Thumb-stopping lifestyle premise without hard selling.
  2. *Origin Lore & Craftsmanship Credibility (5–15s)*: Shop heritage and origin storytelling (e.g. authentic recipes, craftsman techniques).
  3. *Pain Agitation vs Solution Contrast (15–30s)*: Ordinary product failures vs effortless satisfaction with the item.
  4. *Value-First Expert Education / 3 Golden Rules (30–45s)*: Actionable expert tips & consumption/usage techniques that build immense trust.
  5. *Frictionless Soft CTA & Algorithmic Engagement (45–60s)*: Casual comment link referral + comment starter question.
- Formats inline Gemini Director's speech tags (`[curious tone]`, `[excited]`, `[short pause]`, `[emphasis]`, `[warm]`).
- Outputs ONLY the transcript to `./transcription/${product-name}.md`.
- Splits "Video Storyboard & Scene Cues" and "Facebook Reels Post Caption & Copywriting" to `./detail/${product-name}.md`.

**Fail-closed verification**: Confirm `./transcription/${product-name}.md` exists and contains Section 1 (`## 1. Spoken Transcript with Speech Markup`). If missing, STOP.

---

### Step 3: Delegate to Text-to-Speech Subagent (`gemini-3.1-flash-tts-preview`)

Execute the Text-to-Speech subagent:
```bash
uv run python src/subagents/tts_generator.py "${product-name}"
# or
uv run omni-video tts "${product-name}"
```

**What this subagent does**:
- Reads the tagged script from `./transcription/${product-name}.md`.
- Uses `./myvoice.mp3` as the vocal tone reference.
- Synthesizes Thai voiceover matching the pacing, warmth, and emotion cues.
- Exports to `./audio/${product-name}.mp3` at 192 kb/s.

**Fail-closed verification**: Confirm `./audio/${product-name}.mp3` exists and file size > 0 bytes. If missing or 0 bytes, STOP.

---

### Step 4: Video Generation Guardrail (`Phase 2 - Deferred`)

> [!NOTE]
> **Status: SKIPPED AT THIS MOMENT**. Video rendering and viral style analysis are deferred.
> When rendering video, the generator uses a dedicated subdirectory `./video/input/${product-name}/` supporting multiple reference images (.jpg, .png, etc.) and video clips (.mp4, .mov, etc.), with automatic 9:16 vertical assembly:
> ```bash
> uv run omni-video generate-video "${product-name}"
> ```

---

### Step 5: Skill: Facebook Reels Publishing (On-Demand)

If the user requested publishing:
```bash
uv run python src/skills/fb_reels_publisher.py "<video-path>" "<caption-text>"
```
- Caption is automatically extracted from `./detail/${product-name}.md` (with fallback to transcript).
- Publishes via Meta Graph API v26.0 with 3-step resumable binary upload.

---

### Step 6: Skill: Memory & Self-Improvement (Record Learnings for Next Prompt)

Execute the Memory Manager skill to record learnings, niche insights, and user feedback:
```bash
uv run python src/skills/memory_manager.py "${feedback-or-learning}" "${category}"
# or
uv run omni-video add-memory "${feedback-or-learning}" [category]
```

**What this skill does**:
- Updates `./MEMORY.md` with product niche takeaways (e.g. food vs essentials), audio pacing notes, and user corrections.
- Transcript Generator dynamically injects `./MEMORY.md` into future Gemini prompts, ensuring every subsequent prompt improves upon previous runs.
- In interactive CLI mode, prompts the user for optional feedback to persist into memory.

---

## Output Summary

Provide a structured execution summary to the user:

| Item | Status / Output Path | Details |
|---|---|---|
| **Shopee Product** | `${product-title}` | Scraped Shopee product |
| **Shop Lore** | `${shop-name}` | Brand heritage / origin |
| **Transcript** | `./transcription/${product-name}.md` | 5-stage soft-sell script with speech markup & memory rules |
| **Details & Cues** | `./detail/${product-name}.md` | Video Storyboard & Scene Cues + Facebook Reels Caption |
| **Voice Audio** | `./audio/${product-name}.mp3` | 192 kbps MP3, voice-matched to `./myvoice.mp3` |
| **Video** | `[Deferred - Phase 2]` | Skipped at this moment per Implementation.md |
| **Reels Caption** | Ready in `./detail/${product-name}.md` | Includes hashtags, emojis & affiliate CTA |
| **Memory Log** | `./MEMORY.md` | Persistent learnings & feedback loaded for next prompt |

### Next Steps for User
- Review the generated script in `./transcription/${product-name}.md`.
- Review the storyboard and caption in `./detail/${product-name}.md`.
- Listen to the synthesized voiceover in `./audio/${product-name}.mp3`.
- View or append to persistent memory using `/manage-memory` or `uv run omni-video memory`.
- When ready for video rendering, run `/generate-video "${product-name}"` or `uv run omni-video generate-video "${product-name}"`.
