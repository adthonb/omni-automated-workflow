import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Root of the omni-video project
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env if present
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


def get_date_string(date: datetime | None = None) -> str:
    """Return date formatted as YYYY-MM-DD."""
    d = date or datetime.now()
    return d.strftime("%Y-%m-%d")


CONFIG = {
    "PROJECT_ROOT": str(PROJECT_ROOT),
    # Gemini API Key
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    # Model Configurations (per Implementation.md)
    "MODELS": {
        "TRANSCRIPT": os.getenv("TRANSCRIPT_MODEL", "gemini-3.8-flash"),
        "TTS": os.getenv("TTS_MODEL", "gemini-3.1-flash-tts-preview"),
        "STYLE_ANALYZER": os.getenv("STYLE_ANALYZER_MODEL", "gemini-3.8-flash"),
        "VIDEO": os.getenv("VIDEO_MODEL", "gemini-omni-1.1-flash"),
    },
    # File & Directory Paths
    "PATHS": {
        "TONE_FILE": str(PROJECT_ROOT / "tone.text"),
        #"TONE_FILE_ALT": str(PROJECT_ROOT / "transcription" / "tone.text"),
        "VOICE_FILE": str(PROJECT_ROOT / "myvoice.mp3"),
        "MEMORY_FILE": str(PROJECT_ROOT / "MEMORY.md"),
        "BEST_SELL_SAMPLE": str(PROJECT_ROOT / "video" / "input" / "best-sell-example.mp4"),
        "BEST_SELL_SAMPLE_ALT": str(PROJECT_ROOT / "test" / "best-sell-example.mp3"),
        "TRANSCRIPTION_DIR": str(PROJECT_ROOT / "transcription"),
        "DETAIL_DIR": str(PROJECT_ROOT / "detail"),
        "AUDIO_DIR": str(PROJECT_ROOT / "audio"),
        "ANALYSIS_DIR": str(PROJECT_ROOT / "analysis"),
        "VIDEO_INPUT_BASE": str(PROJECT_ROOT / "video" / "input"),
        "VIDEO_OUTPUT_BASE": str(PROJECT_ROOT / "video" / "output"),
    },
    # Facebook Reels API Config
    "FACEBOOK": {
        "PAGE_ID": os.getenv("FB_PAGE_ID", ""),
        "PAGE_ACCESS_TOKEN": os.getenv("FB_PAGE_ACCESS_TOKEN", ""),
        "GRAPH_API_VERSION": os.getenv("FB_GRAPH_API_VERSION", "v26.0"),
        "GRAPH_API_BASE": "https://graph.facebook.com",
        "RUPLOAD_BASE": "https://rupload.facebook.com",
    },
    # Shopee Scraper & Anti-Bot Cookie Config
    "SHOPEE": {
        "COOKIE": os.getenv("SHOPEE_COOKIE", ""),
        "USER_AGENT": os.getenv(
            "SHOPEE_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        ),
    },
    # Helper
    "get_date_string": get_date_string,
}
