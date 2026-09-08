import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from omni_video.config import CONFIG, PROJECT_ROOT, get_date_string

__all__ = ["CONFIG", "PROJECT_ROOT", "get_date_string"]
