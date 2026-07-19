from __future__ import annotations

import threading

import customtkinter as ctk

from core.model_router import ModelRouter
from core.personality import Personality
from core.voice_engine import VoiceEngine
from gui.components import NovaButton, NovaLabel
from utils.styles import NovaStyles

styles = NovaStyles.apply()


class VoiceMode(ctk.CTkFrame):
    def __init__(
        self,
        master,
        voice_engine: VoiceEngine,
        model_router: ModelRouter,
    ) -> None:
        super().__init__(master, fg_color=styles["bg_primary"])
        self.voice_engine = voice_engine
        self.model_router = model_router
        self._starting = False
        self._closed = False

        NovaLabel(self, text="VOICE MODE", font_size=18, bold=True).pack(pady=(25, 8))
        self.status = NovaLabel(
            self, text='Say "Hey Nova" followed by your request', font_size=14
        )
        self.status.pack(pady=8)

        self.level = ctk.CTkProgressBar(
            self,
            width=420,
            height=16,
            progress_color=styles["accent"],
        )
        self.level.pack(pady=20)
        self.level.set(0)

        self.transcript = ctk.CTkTextbox(
            self, width=760, height=300, font=("Segoe UI", 14), wrap="word"
        )
        self.transcript.pack(fill="both", expand=True, padx=80, pady=15)
        self.transcript.configure(state="disabled")

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(pady=(5, 25))
        self.listen_button = NovaButton(
            controls, text="Start Listening", command=self.toggle_listening
        )
        self.listen_button.pack(side="left", padx=6)
        NovaButton(
            controls, text="Stop Speaking", command=self.voice_engine.stop_speaking
        ).pack(side="left", padx=6)

        self.after(50, self._refresh_level)

    def _append(self, speaker: str, text: str) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{speaker}: {text}\n\n")
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def _refresh_level(self) -> None:
        if self._closed or not self.winfo_exists():
            return
        self.level.set(self.voice_engine.current_audio_level)
        self.after(50, self._refresh_level)

    def toggle_listening(self) -> None:
        if self._starting:
            return
        if self.voice_engine.is_listening:
            self.voice_engine.stop_listening()
            self.status.configure(text="Listening paused")
            self.listen_button.configure(text="Start Listening")
            return

        self._starting = True
        self.listen_button.configure(state="disabled", text="Loading speech model...")

        def start() -> None:
            try:
                self.voice_engine.start_listening(self._on_wake_word)
            except Exception as exc:
                if not self._closed:
                    self.after(0, self._listening_failed, str(exc))
            else:
                if self._closed:
                    self.voice_engine.stop_listening()
                else:
                    self.after(0, self._listening_started)

        threading.Thread(target=start, name="nova-voice-start", daemon=True).start()

    def _listening_started(self) -> None:
        if self._closed:
            return
        self._starting = False
        self.status.configure(text='Listening for "Hey Nova"')
        self.listen_button.configure(state="normal", text="Stop Listening")

    def _listening_failed(self, error: str) -> None:
        if self._closed:
            return
        self._starting = False
        self.status.configure(text=f"Voice unavailable: {error}")
        self.listen_button.configure(state="normal", text="Retry Listening")

    def _on_wake_word(self, prompt: str) -> None:
        if self._closed:
            return
        self.after(0, self._append, "You", prompt)
        self.after(0, self.status.configure, {"text": "Thinking..."})

        def request() -> None:
            try:
                response = self.model_router.chat(
                    [
                        {
                            "role": "system",
                            "content": Personality.get_system_prompt(),
                        },
                        {"role": "user", "content": prompt},
                    ]
                )
            except Exception as exc:
                self.after(0, self._finish_response, None, str(exc))
            else:
                self.after(0, self._finish_response, response, None)

        threading.Thread(target=request, name="nova-voice-chat", daemon=True).start()

    def _finish_response(self, response: str | None, error: str | None) -> None:
        if self._closed:
            return
        if error:
            self._append("Error", error)
        else:
            assert response is not None
            self._append("Nova", response)
            self.voice_engine.speak(response)
        self.status.configure(
            text='Listening for "Hey Nova"'
            if self.voice_engine.is_listening
            else "Listening paused"
        )

    def destroy(self) -> None:
        self._closed = True
        self.voice_engine.stop_listening()
        super().destroy()
