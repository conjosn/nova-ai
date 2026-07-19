from __future__ import annotations

import threading

import customtkinter as ctk

from core.assistant_session import AssistantReply, AssistantSession
from gui.components import GhostButton, NovaButton, NovaFrame, NovaLabel, SectionTitle
from utils.styles import NovaStyles

styles = NovaStyles.apply()


class TextMode(ctk.CTkFrame):
    def __init__(self, master, session: AssistantSession):
        super().__init__(master, fg_color=styles["bg_primary"])
        self.session = session
        self._request_in_flight = False

        panel = NovaFrame(self)
        panel.pack(fill="both", expand=True)
        SectionTitle(panel, "Persistent Session", "SHARED WITH VOICE").pack(
            fill="x", padx=18, pady=(16, 8)
        )

        self.chat_box = ctk.CTkTextbox(
            panel,
            font=("Segoe UI", 13),
            wrap="word",
            fg_color=styles["bg_secondary"],
            border_width=1,
            border_color=styles["border"],
        )
        self.chat_box.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        self.chat_box.configure(state="disabled")
        for message in self.session.history:
            self._append("YOU" if message["role"] == "user" else "NOVA", message["content"])

        input_frame = ctk.CTkFrame(panel, fg_color="transparent")
        input_frame.pack(fill="x", padx=18, pady=(0, 16))
        self.input_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Continue the shared session...",
            height=42,
            fg_color=styles["bg_tertiary"],
            border_color=styles["border"],
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.input_entry.bind("<Return>", self.send_message)
        GhostButton(input_frame, text="CLEAR", command=self.clear_session).pack(
            side="right", padx=(0, 8)
        )
        self.send_button = NovaButton(
            input_frame, text="TRANSMIT", command=self.send_message
        )
        self.send_button.pack(side="right")

        self.footer = NovaLabel(
            panel,
            text="Ready // local skills and model routing active",
            font_size=9,
            text_color=styles["text_muted"],
        )
        self.footer.pack(anchor="w", padx=18, pady=(0, 12))

    def _append(self, speaker: str, text: str) -> None:
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"{speaker}  //\n{text.strip()}\n\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def clear_session(self) -> None:
        if self._request_in_flight:
            return
        self.session.clear()
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.configure(state="disabled")
        self.footer.configure(text="Session context cleared")

    def send_message(self, event=None):
        del event
        if self._request_in_flight:
            return "break"
        message = self.input_entry.get().strip()
        if not message:
            return "break"
        self._append("YOU", message)
        self.input_entry.delete(0, "end")
        self._request_in_flight = True
        self.send_button.configure(state="disabled", text="PROCESSING")
        self.footer.configure(text="Routing directive...")

        def request() -> None:
            try:
                reply = self.session.respond(message)
            except Exception as exc:
                self.after(0, self._finish_request, None, str(exc))
            else:
                self.after(0, self._finish_request, reply, None)

        threading.Thread(target=request, name="nova-console", daemon=True).start()
        return "break"

    def _finish_request(self, reply: AssistantReply | None, error: str | None) -> None:
        if not self.winfo_exists():
            return
        if error:
            self._append("FAULT", error)
            self.footer.configure(text="Directive failed")
        else:
            assert reply is not None
            self._append("NOVA", reply.text)
            source = reply.command or reply.model or reply.source
            self.footer.configure(text=f"Completed // {source}")
        self._request_in_flight = False
        self.send_button.configure(state="normal", text="TRANSMIT")
        self.input_entry.focus_set()
