#!/usr/bin/env python3
"""Nova desktop launcher."""

from __future__ import annotations

import sys

from utils.config import load_config
from utils.logger import NovaLogger
from utils.paths import ensure_data_dirs

logger = NovaLogger()


def main() -> int:
    try:
        import customtkinter as ctk

        from core.model_router import ModelRouter
        from core.voice_engine import VoiceEngine
        from gui.main_window import MainWindow
    except ImportError as exc:
        logger.error("Missing dependency: %s", exc)
        logger.error("Install dependencies with: python -m pip install -r requirements.txt")
        return 1

    try:
        ensure_data_dirs()
        config = load_config()
        ctk.set_appearance_mode("dark")

        voice_engine = VoiceEngine(
            mic_index=config.get("mic_index"),
            speaker_index=config.get("speaker_index"),
            whisper_model=config.get("whisper_model"),
            whisper_device=config.get("whisper_device"),
            wake_word=config.get("wake_word"),
            open_conversation=config.get("open_conversation"),
        )
        model_router = ModelRouter(default_model=config.get("model_name"))
        app = MainWindow(voice_engine=voice_engine, model_router=model_router)
        app.mainloop()
        return 0
    except KeyboardInterrupt:
        logger.info("Nova closed by user")
        return 0
    except Exception:
        logger.exception("Fatal startup error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
