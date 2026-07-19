"""Filesystem locations used by Nova.

Runtime state belongs outside the source checkout so Nova behaves consistently
when launched from a shortcut, a service, or a different working directory.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(
    os.environ.get("NOVA_DATA_DIR", Path.home() / ".nova")
).expanduser()
CONFIG_PATH = DATA_DIR / "config.json"
MEMORY_PATH = DATA_DIR / "memory"
VOICE_DIR = DATA_DIR / "voices"
REMINDERS_PATH = DATA_DIR / "reminders.json"


def ensure_data_dirs() -> None:
    """Create Nova's writable runtime directories when first needed."""

    for path in (DATA_DIR, MEMORY_PATH, VOICE_DIR):
        path.mkdir(parents=True, exist_ok=True)
