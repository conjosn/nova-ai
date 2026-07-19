from __future__ import annotations

import os
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from gui.components import NovaButton, NovaLabel
from utils.config import load_config, save_config
from utils.logger import NovaLogger
from utils.paths import VOICE_DIR
from utils.styles import NovaStyles

logger = NovaLogger()
styles = NovaStyles.apply()


class SettingsPanel(ctk.CTkFrame):
    def __init__(self, master, voice_engine=None):
        super().__init__(master, fg_color=styles["bg_primary"])
        self.voice_engine = voice_engine
        self.config = load_config()
        self._input_devices: dict[str, int | None] = {"Default": None}
        self._output_devices: dict[str, int | None] = {"Default": None}

        NovaLabel(self, text="SETTINGS", font_size=20, bold=True).pack(pady=20)

        NovaLabel(self, text="Microphone", font_size=14).pack(anchor="w", padx=30)
        self.mic_menu = ctk.CTkOptionMenu(
            self, values=["Default"], command=self._save_mic
        )
        self.mic_menu.pack(fill="x", padx=30, pady=5)

        NovaLabel(self, text="Speaker", font_size=14).pack(
            anchor="w", padx=30, pady=(15, 0)
        )
        self.speaker_menu = ctk.CTkOptionMenu(
            self, values=["Default"], command=self._save_speaker
        )
        self.speaker_menu.pack(fill="x", padx=30, pady=5)

        NovaLabel(self, text="Voice (Piper)", font_size=14).pack(
            anchor="w", padx=30, pady=(15, 0)
        )
        self.voice_menu = ctk.CTkOptionMenu(
            self,
            values=[
                "en_US-lessac-medium (Default)",
                "en_US-ryan-medium",
                "Custom .onnx file...",
            ],
            command=self._on_voice_selected,
        )
        self.voice_menu.pack(fill="x", padx=30, pady=5)

        NovaButton(
            self,
            text="Import ChatGPT / Claude Export",
            command=self._import_data,
        ).pack(pady=20, padx=30, fill="x")
        NovaButton(
            self,
            text="Clear Long-Term Memory",
            command=self._clear_memory,
            fg_color="#ef4444",
            hover_color="#dc2626",
            text_color="white",
        ).pack(pady=10, padx=30, fill="x")
        self.feedback = NovaLabel(self, text="", font_size=12)
        self.feedback.pack(pady=8)

        self._populate_audio_devices()

    def _persist(self) -> None:
        try:
            save_config(self.config)
        except OSError as exc:
            logger.error("Failed to save settings: %s", exc)
            self.feedback.configure(text=f"Could not save settings: {exc}")

    def _populate_audio_devices(self) -> None:
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            for index, device in enumerate(devices):
                host_api = sd.query_hostapis(device["hostapi"])["name"]
                name = f"{index}: {device['name']} [{host_api}]"
                if device["max_input_channels"] > 0:
                    self._input_devices[name] = index
                if device["max_output_channels"] > 0:
                    self._output_devices[name] = index
            self.mic_menu.configure(values=list(self._input_devices))
            self.speaker_menu.configure(values=list(self._output_devices))
            self._select_saved_device(
                self.mic_menu, self._input_devices, self.config.get("mic_index")
            )
            self._select_saved_device(
                self.speaker_menu,
                self._output_devices,
                self.config.get("speaker_index"),
            )
        except Exception as exc:
            logger.error("Failed to load audio devices: %s", exc)
            self.feedback.configure(text=f"Audio devices unavailable: {exc}")

    @staticmethod
    def _select_saved_device(menu, devices, saved_index) -> None:
        selected = next(
            (name for name, index in devices.items() if index == saved_index), "Default"
        )
        menu.set(selected)

    def _save_mic(self, choice: str) -> None:
        index = self._input_devices.get(choice)
        self.config["mic_index"] = index
        self._persist()
        if self.voice_engine:
            self.voice_engine.set_microphone(index)

    def _save_speaker(self, choice: str) -> None:
        index = self._output_devices.get(choice)
        self.config["speaker_index"] = index
        self._persist()
        if self.voice_engine:
            self.voice_engine.set_speaker(index)

    def _on_voice_selected(self, choice: str) -> None:
        if choice == "Custom .onnx file...":
            path = filedialog.askopenfilename(
                title="Select Piper voice model (.onnx)",
                filetypes=[("Piper Model", "*.onnx")],
            )
            if not path:
                return
        else:
            filename = {
                "en_US-lessac-medium (Default)": "en_US-lessac-medium.onnx",
                "en_US-ryan-medium": "en_US-ryan-medium.onnx",
            }[choice]
            path = str(VOICE_DIR / filename)
            if not os.path.exists(path):
                self.feedback.configure(text=f"Voice model is not installed: {path}")
                return

        self.config["voice_model"] = path
        self._persist()
        if self.voice_engine:
            self.voice_engine.set_voice(path)

    def _import_data(self) -> None:
        path = filedialog.askdirectory(title="Select exported conversation folder")
        if not path:
            return
        self.feedback.configure(text="Importing conversations...")

        def worker() -> None:
            try:
                from core.data_importer import DataImporter
                from core.persistent_memory import PersistentMemory

                count = DataImporter(PersistentMemory()).import_export(path)
            except Exception as exc:
                logger.exception("Conversation import failed")
                self.after(0, self.feedback.configure, {"text": f"Import failed: {exc}"})
            else:
                self.after(
                    0,
                    self.feedback.configure,
                    {"text": f"Imported {count} messages"},
                )

        threading.Thread(target=worker, name="nova-import", daemon=True).start()

    def _clear_memory(self) -> None:
        if not messagebox.askyesno(
            "Clear Long-Term Memory",
            "Permanently delete Nova's local conversation memory?",
        ):
            return
        try:
            from core.persistent_memory import PersistentMemory

            PersistentMemory().clear()
            self.feedback.configure(text="Memory cleared")
        except Exception as exc:
            logger.exception("Clear memory failed")
            self.feedback.configure(text=f"Clear failed: {exc}")
