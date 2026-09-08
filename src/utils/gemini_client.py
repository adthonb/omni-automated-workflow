import math
import re
import sys
from pathlib import Path
import time
from typing import Any, Callable

# Ensure src is importable
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from google import genai
from config import CONFIG

_client_instance: genai.Client | None = None


def get_gemini_client(api_key: str | None = None) -> genai.Client:
    """Return a singleton instance of genai.Client."""
    global _client_instance
    key = api_key or CONFIG["GEMINI_API_KEY"]
    if _client_instance is None:
        _client_instance = genai.Client(api_key=key)
    return _client_instance


def with_retry(
    fn: Callable[[], Any],
    max_retries: int = 3,
    initial_delay_s: float = 2.0,
) -> Any:
    """Execute a function with automatic retry on 429 RateLimit / temporary errors."""
    delay = initial_delay_s
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as err:
            err_str = str(err).lower()
            is_rate_limit = (
                "429" in err_str
                or "quota" in err_str
                or "resource_exhausted" in err_str
                or "ratelimit" in err_str
                or getattr(err, "code", None) == 429
                or getattr(err, "status_code", None) == 429
            )

            if is_rate_limit and attempt < max_retries:
                match = re.search(r"retry in ([\d.]+)s", str(err), re.IGNORECASE)
                if match:
                    wait_s = math.ceil(float(match.group(1))) + 1.0
                else:
                    wait_s = delay
                print(
                    f"[GeminiClient] Quota/Rate limit reached. Retrying in {int(wait_s)}s (Attempt {attempt}/{max_retries})...",
                    file=sys.stderr,
                )
                time.sleep(wait_s)
                delay *= 2.0
            else:
                raise err
