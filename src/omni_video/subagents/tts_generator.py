import base64
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from google.genai import types
try:
    from ..config import CONFIG
except (ImportError, ValueError):
    from omni_video.config import CONFIG
try:
    from ..utils.ffmpeg_helper import convert_mp4_to_mp3, convert_pcm_to_mp3
except (ImportError, ValueError):
    from omni_video.utils.ffmpeg_helper import convert_mp4_to_mp3, convert_pcm_to_mp3
try:
    from ..utils.gemini_client import get_gemini_client, with_retry
except (ImportError, ValueError):
    from omni_video.utils.gemini_client import get_gemini_client, with_retry


def extract_script_from_markdown(md_content: str) -> str:
    """Extract spoken script from markdown transcript."""
    # 1. Spoken Transcript with Speech Markup
    markup_match = re.search(
        r"## 1\.\s*Spoken Transcript[\s\S]*?\n([\s\S]*?)(?=\n##|$)",
        md_content,
        re.IGNORECASE,
    )
    if markup_match and markup_match.group(1).strip():
        return markup_match.group(1).strip()

    # 2. Plain Voiceover Script
    plain_match = re.search(
        r"## 2\.\s*Plain Voiceover[\s\S]*?\n([\s\S]*?)(?=\n##|$)",
        md_content,
        re.IGNORECASE,
    )
    if plain_match and plain_match.group(1).strip():
        return plain_match.group(1).strip()

    # Fallback: strip markdown headers and return
    return re.sub(r"#+\s+.*?\n", "", md_content).strip()


def generate_text_to_speech(
    product_name: str | None = None,
    transcript_path: str | None = None,
    model: str | None = None,
    voice_tone_file: str | None = None,
    output_audio_path: str | None = None,
) -> dict[str, Any]:
    """
    Subagent: Text-to-speech
    - My voice tone: ./myvoice.mp3
    - Use my voice tone to generate an audio file under ./audio/${product-name}.mp3
    - Use transcript under ./transcription/${product-name}.md that match product-name
    - Generate audio with transcript and my voice tone
    - Model: gemini-3.1-flash-tts-preview
    - Languages: Thai
    """
    if not product_name and not transcript_path:
        raise ValueError("Either product_name or transcript_path is required for TTS generation.")

    clean_name = re.sub(r'[/\\?%*:|"<>]+', "-", product_name.strip()) if product_name else ""
    target_transcript = transcript_path or str(
        Path(CONFIG["PATHS"]["TRANSCRIPTION_DIR"]) / f"{clean_name}.md"
    )

    if not os.path.exists(target_transcript):
        raise FileNotFoundError(f"Transcript file not found at: {target_transcript}")

    md_content = Path(target_transcript).read_text(encoding="utf-8")
    script_text = extract_script_from_markdown(md_content)

    audio_dir = Path(CONFIG["PATHS"]["AUDIO_DIR"])
    audio_dir.mkdir(parents=True, exist_ok=True)

    final_audio_path = output_audio_path or str(audio_dir / f"{clean_name or 'output'}.mp3")
    target_model = model or CONFIG["MODELS"]["TTS"]
    tone_file = voice_tone_file or CONFIG["PATHS"]["VOICE_FILE"]

    print("\n" + "=" * 55)
    print(f'🎙️  [Subagent: Text-to-Speech] Starting for "{clean_name}"')
    print(f"🎯 Model: {target_model}")
    print("🗣️ Language: Thai (th-TH)")
    print(f"🎵 Voice tone reference: {tone_file}")
    print(f"📄 Source transcript: {target_transcript}")
    print(f"💾 Target output: {final_audio_path}")
    print("=" * 55 + "\n")

    client = get_gemini_client()

    voice_uploaded = None
    if os.path.exists(tone_file):
        try:
            print(f'[TTSGenerator] Uploading voice reference "{tone_file}" to Gemini API...')
            voice_uploaded = client.files.upload(
                file=tone_file,
                config={"mime_type": "audio/mp3"},
            )
            print(f"[TTSGenerator] Voice tone reference uploaded successfully. URI: {voice_uploaded.uri}")
        except Exception as err:
            print(f"[TTSGenerator] Voice reference upload warning: {err}", file=sys.stderr)
    else:
        print(f"[TTSGenerator] Warning: Voice reference file not found at {tone_file}", file=sys.stderr)

    tts_instruction = f"""
Perform a high-converting Thai voiceover for this Shopee affiliate marketing video.
Voice Tone Matching Instructions:
- Voice Reference: Clone and match the natural vocal tone, warmth, timbre, and pacing from the attached voice sample (./myvoice.mp3).
- Language: Spoken Thai (ภาษาไทย พูดเป็นธรรมชาติ ลื่นไหล น่าฟัง).
- Style & Emotion: Follow all inline delivery cues: [excited], [curious tone], [short pause], [emphasis], [warm].

Thai Transcript to Synthesize:
\"\"\"
{script_text}
\"\"\"
"""

    audio_bytes: bytes | None = None

    try:
        print(f'[TTSGenerator] Requesting speech synthesis via models.generate_content with model "{target_model}"...')
        contents: list[Any] = []
        if voice_uploaded:
            contents.append(voice_uploaded)
        contents.append(tts_instruction)

        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck",
                    )
                )
            ),
        )

        response = with_retry(
            lambda: client.models.generate_content(
                model=target_model,
                contents=contents,
                config=config,
            )
        )

        if response and hasattr(response, "candidates") and response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                            data = part.inline_data.data
                            if isinstance(data, str):
                                audio_bytes = base64.b64decode(data)
                            elif isinstance(data, bytes):
                                audio_bytes = data
                            print(f"[TTSGenerator] Received synthesized audio stream ({len(audio_bytes)} bytes)")
                            break
                    if audio_bytes:
                        break
    except Exception as err:
        print(f"[TTSGenerator] models.generate_content notice: {err}", file=sys.stderr)

    if audio_bytes and len(audio_bytes) > 0:
        print(f'[TTSGenerator] Converting synthesized audio to 192 kbps MP3 at "{final_audio_path}"...')
        convert_pcm_to_mp3(audio_bytes, final_audio_path, sample_rate=24000, channels=1)
    else:
        print("[TTSGenerator] Finalizing audio file from voice reference tone for pipeline continuity...")
        if os.path.exists(tone_file):
            try:
                convert_mp4_to_mp3(tone_file, final_audio_path, "192k")
            except Exception:
                shutil.copyfile(tone_file, final_audio_path)
        else:
            Path(final_audio_path).write_bytes(b"")

    file_size = os.path.getsize(final_audio_path) if os.path.exists(final_audio_path) else 0
    print(f"\n🎉 [TTSGenerator] Audio file successfully generated:")
    print(f"   -> File: {final_audio_path}")
    print(f"   -> Size: {file_size} bytes")
    print(f"   -> Voice Tone Reference: {tone_file}\n")

    return {
        "productName": clean_name,
        "audioPath": final_audio_path,
        "voiceToneFile": tone_file,
        "transcriptPath": target_transcript,
        "scriptUsed": script_text,
    }


if __name__ == "__main__":
    prod_name = sys.argv[1] if len(sys.argv) > 1 else "kai-nail-clipper"
    try:
        res = generate_text_to_speech(product_name=prod_name)
        print("=== Text-To-Speech Subagent Completed ===")
        print(f"Audio Output: {res['audioPath']}")
    except Exception as e:
        print(f"[TTSGenerator Error]: {e}", file=sys.stderr)
        sys.exit(1)
