import customtkinter as ctk
import os
import json
from gui.components import NovaButton, NovaLabel
from utils.styles import NovaStyles
from utils.logger import NovaLogger

logger = NovaLogger()
styles = NovaStyles.apply()
CONFIG_PATH = "config.json"

class SettingsPanel(ctk.CTkFrame):
    def __init__(self, master, voice_engine=None):
        super().__init__(master, fg_color=styles["bg_primary"])

        self.voice_engine = voice_engine
        self.config = self._load_config()

        NovaLabel(self, text="SETTINGS", font_size=20, bold=True).pack(pady=20)

        NovaLabel(self, text="Microphone", font_size=14).pack(anchor="w", padx=30)
        self.mic_menu = ctk.CTkOptionMenu(self, values=["Default"], command=self._save_mic)
        self.mic_menu.pack(fill="x", padx=30, pady=5)

        NovaLabel(self, text="Speaker", font_size=14).pack(anchor="w", padx=30, pady=(15, 0))
        self.speaker_menu = ctk.CTkOptionMenu(self, values=["Default"], command=self._save_speaker)
        self.speaker_menu.pack(fill="x", padx=30, pady=5)

        NovaLabel(self, text="Voice (Piper)", font_size=14).pack(anchor="w", padx=30, pady=(15, 0))
        self.voice_menu = ctk.CTkOptionMenu(self, values=[
            "en_US-lessac-medium (Default)",
            "en_US-ryan-medium",
            "Custom .onnx file..."
        ], command=self._on_voice_selected)
        self.voice_menu.pack(fill="x", padx=30, pady=5)

        NovaButton(self, text="Import from ChatGPT / Claude / Gemini", command=self._import_data).pack(pady=20, padx=30, fill="x")
        NovaButton(self, text="Clear Long-Term Memory", command=self._clear_memory, fg_color="#ef4444").pack(pady=10, padx=30, fill="x")

        self._populate_audio_devices()

    def _load_config(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        return {}

    def _save_config(self):
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=2)

    def _populate_audio_devices(self):
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = [d["name"] for d in devices if d["max_input_channels"] > 0]
            output_devices = [d["name"] for d in devices if d["max_output_channels"] > 0]

            self.mic_menu.configure(values=input_devices or ["Default"])
            self.speaker_menu.configure(values=output_devices or ["Default"])
        except Exception as e:
            logger.error(f"Failed to load audio devices: {e}")

    def _save_mic(self, choice):
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            index = next((i for i, d in enumerate(devices) if d["name"] == choice), None)
            if index is not None:
                self.config["mic_index"] = index
                self._save_config()
                if self.voice_engine:
                    self.voice_engine.set_microphone(index)
        except Exception as e:
            logger.error(f"Error saving mic: {e}")

    def _save_speaker(self, choice):
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            index = next((i for i, d in enumerate(devices) if d["name"] == choice), None)
            if index is not None:
                self.config["speaker_index"] = index
                self._save_config()
        except Exception as e:
            logger.error(f"Error saving speaker: {e}")

    def _on_voice_selected(self, choice):
        if choice == "Custom .onnx file...":
            from tkinter import filedialog
            path = filedialog.askopenfilename(title="Select Piper voice model (.onnx)", filetypes=[("Piper Model", "*.onnx")])
            if path:
                self.config["voice_model"] = path
                self._save_config()
                if self.voice_engine:
                    self.voice_engine.set_voice(path)
        else:
            voice_map = {
                "en_US-lessac-medium (Default)": os.path.expanduser("~/.local/share/piper-tts/en_US-lessac-medium.onnx"),
                "en_US-ryan-medium": os.path.expanduser("~/.local/share/piper-tts/en_US-ryan-medium.onnx"),
            }
            path = voice_map.get(choice)
            if path and os.path.exists(path):
                self.config["voice_model"] = path
                self._save_config()
                if self.voice_engine:
                    self.voice_engine.set_voice(path)

    def _import_data(self):
        from tkinter import filedialog
        from core.data_importer import DataImporter
        from core.persistent_memory import PersistentMemory

        path = filedialog.askdirectory(title="Select exported folder")
        if not path: return

        try:
            memory = PersistentMemory()
            importer = DataImporter(memory)
            importer.import_chatgpt_export(path)
            ctk.CTkLabel(self, text="Import successful!", text_color="#22c55e").pack(pady=10)
        except Exception as e:
            logger.error(f"Import failed: {e}")

    def _clear_memory(self):
        try:
            from core.persistent_memory import PersistentMemory
            memory = PersistentMemory()
            memory.client.delete_collection("nova_memory")
            ctk.CTkLabel(self, text="Memory cleared", text_color="#22c55e").pack(pady=10)
        except Exception as e:
            logger.error(f"Clear memory failed: {e}")