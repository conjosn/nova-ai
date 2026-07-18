#!/usr/bin/env python3
import customtkinter as ctk
import json
import os
import sys
from utils.logger import NovaLogger

logger = NovaLogger()
CONFIG_PATH = "config.json"

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def main():
    try:
        ctk.set_appearance_mode("dark")
        config = load_config()

        from core.voice_engine import VoiceEngine
        voice_engine = VoiceEngine(mic_index=config.get("mic_index"))

        if config.get("speaker_index") is not None:
            voice_engine.set_speaker(config.get("speaker_index"))

        if config.get("voice_model") and os.path.exists(config["voice_model"]):
            voice_engine.set_voice(config["voice_model"])

        from core.model_router import ModelRouter
        model_router = ModelRouter()

        from gui.main_window import MainWindow
        app = MainWindow(voice_engine=voice_engine, model_router=model_router)
        app.mainloop()

    except KeyboardInterrupt:
        logger.info("Nova closed by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()