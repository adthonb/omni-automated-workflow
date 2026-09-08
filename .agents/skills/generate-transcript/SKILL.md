---
name: generate-transcript
description: Generates high-converting Thai Shopee affiliate video transcripts reflecting scraped product descriptions with Gemini speech tags following tone.text guidelines.
---

# Generate Transcript Skill (Python 3.14)

Generates high-converting spoken Thai scripts for Shopee affiliate marketing videos and Facebook Reels, incorporating scraped Shopee product descriptions and shop lore.

## Specification

- **Model**: `gemini-3.8-flash`
- **Speech Prompting Guide**: [Google Speech Generation Guide](https://ai.google.dev/gemini-api/docs/speech-generation#prompting-guide)
- **Input**: Shopee product URL or product name
- **Tone Reference**: `./tone.text`
- **Output Target (Transcript)**: `./transcription/${product-name}.md` (Contains only the transcript)
- **Output Target (Details)**: `./detail/${product-name}.md` (Contains Video Storyboard & Facebook Caption)

## Structure of Generated Files

### 1. Transcript File (`./transcription/${product-name}.md`)
1. **Spoken Transcript with Speech Markup**: Contains tags like `[excited]`, `[curious tone]`, `[short pause]`, `[emphasis]`, following the 5-stage soft-sell blueprint.
2. **Plain Voiceover Text**: Unmarked spoken Thai text for clean subtitles.

### 2. Detail File (`./detail/${product-name}.md`)
1. **Video Storyboard & Scene Cues**: Timestamped table for video generation.
2. **Facebook Reels Post Caption & Copywriting**: Copy with emojis, hashtags (#ShopeeTH), and Shopee affiliate CTA.

## Usage

```bash
# Using Shopee URL (automatically scrapes product description):
uv run omni-video transcript "https://shopee.co.th/..."

# Using product name:
uv run omni-video transcript "<product-name>"
```
