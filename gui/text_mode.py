from __future__ import annotations

import threading

import customtkinter as ctk

from core.model_router import ModelRouter
from core.personality import Personality
from gui.components import NovaButton, NovaLabel
from utils.styles import NovaStyles

styles = NovaStyles.apply()


class TextMode(ctk.CTkFrame):
    def __init__(self, master, model_router: ModelRouter):
        super().__init__(master, fg_color=styles["bg_primary"])
        self.model_router = model_router
        self.history: list[dict[str, str]] = []
        self._request_in_flight = False

        NovaLabel(self, text="TEXT MODE", font_size=18, bold=True).pack(pady=15)

        self.chat_box = ctk.CTkTextbox(
            self, font=("Segoe UI", 14), height=400, wrap="word"
        )
        self.chat_box.pack(fill="both", expand=True, padx=30, pady=10)
        self.chat_box.configure(state="disabled")

        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=30, pady=10)

        self.input_entry = ctk.CTkEntry(
            input_frame, placeholder_text="Type your message...", height=40
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input_entry.bind("<Return>", self.send_message)

        self.send_button = NovaButton(
            input_frame, text="Send", command=self.send_message
        )
        self.send_button.pack(side="right")

    def _append(self, speaker: str, text: str) -> None:
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"{speaker}: {text}\n\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def send_message(self, event=None):
        del event
        if self._request_in_flight:
            return "break"
        message = self.input_entry.get().strip()
        if not message:
            return "break"

        self._append("You", message)
        self.input_entry.delete(0, "end")
        self._request_in_flight = True
        self.send_button.configure(state="disabled", text="Thinking...")
        self.history.append({"role": "user", "content": message})

        def request() -> None:
            try:
                messages = [
                    {"role": "system", "content": Personality.get_system_prompt()},
                    *self.history[-12:],
                ]
                response = self.model_router.chat(messages)
            except Exception as exc:
                self.after(0, self._finish_request, None, str(exc))
            else:
                self.after(0, self._finish_request, response, None)

        threading.Thread(target=request, name="nova-text-chat", daemon=True).start()
        return "break"

    def _finish_request(self, response: str | None, error: str | None) -> None:
        if not self.winfo_exists():
            return
        if error:
            self._append("Error", error)
            # Failed user turns should not poison future conversation context.
            if self.history and self.history[-1]["role"] == "user":
                self.history.pop()
        else:
            assert response is not None
            self.history.append({"role": "assistant", "content": response})
            self._append("Nova", response)
        self._request_in_flight = False
        self.send_button.configure(state="normal", text="Send")
        self.input_entry.focus_set()
