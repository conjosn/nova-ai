"""Small, fault-tolerant configuration store for Nova."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from utils.logger import NovaLogger
from utils.paths import CONFIG_PATH

logger = NovaLogger()

DEFAULT_CONFIG: dict[str, Any] = {
    "model_name": "gemma2:2b",
    "ollama_host": "http://127.0.0.1:11434",
    "whisper_model": "base",
    "whisper_device": "auto",
    "mic_index": None,
    "speaker_index": None,
    "voice_model": None,
    "wake_word": "hey nova",
    "open_conversation": False,
    "auto_improve": False,
    "auto_improve_interval_minutes": 60,
}


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load config while preserving defaults and recovering from bad JSON."""

    config = DEFAULT_CONFIG.copy()
    if not path.exists():
        return config

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("configuration root must be a JSON object")
        config.update(loaded)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.error("Failed to load config from %s: %s", path, exc)
    return config


def save_config(config: dict[str, Any], path: Path = CONFIG_PATH) -> None:
    """Atomically write config so an interrupted save cannot corrupt it."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary_name, path)
    except Exception:
        with suppress(OSError):
            os.unlink(temporary_name)
        raise
