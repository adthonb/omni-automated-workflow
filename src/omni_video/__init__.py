"""Omni Video Orchestration Workflow (Command -> Agent -> Skill) in Python 3.14."""

__version__ = "1.0.0"

from .config import CONFIG, get_date_string
from .orchestrator import run_interactive_command, run_orchestration_pipeline

__all__ = [
    "CONFIG",
    "get_date_string",
    "run_orchestration_pipeline",
    "run_interactive_command",
]
