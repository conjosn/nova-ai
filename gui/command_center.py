"""JARVIS-inspired, original command-center interface for Nova."""

from __future__ import annotations

import threading
from tkinter import filedialog

import customtkinter as ctk

from core.agent_profiles import AGENT_PROFILES
from core.assistant_session import AssistantReply, AssistantSession
from core.voice_engine import VoiceEngine
from gui.components import GhostButton, NovaButton, NovaFrame, NovaLabel, SectionTitle
from gui.hud import MetricCard, NeuralCore
from utils.config import load_config, save_config
from utils.styles import NovaStyles

styles = NovaStyles.apply()


class CommandCenter(ctk.CTkFrame):
    def __init__(
        self,
        master,
        voice_engine: VoiceEngine,
        session: AssistantSession,
    ) -> None:
        super().__init__(master, fg_color=styles["bg_primary"])
        self.voice_engine = voice_engine
        self.session = session
        self._closed = False
        self._starting_voice = False
        self._request_in_flight = False
        self._telemetry_in_flight = False

        self.grid_columnconfigure(0, minsize=290)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, minsize=250)
        self.grid_rowconfigure(0, weight=1)

        self._build_core_panel()
        self._build_conversation_panel()
        self._build_telemetry_panel()
        self.after(80, self._refresh_runtime_state)
        self.after(150, self._poll_telemetry)
        if load_config().get("auto_start_listening"):
            self.after(650, self.toggle_listening)

    def _build_core_panel(self) -> None:
        panel = NovaFrame(self)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        SectionTitle(panel, "Neural Core", "LOCAL").pack(fill="x", padx=16, pady=(15, 4))
        self.core = NeuralCore(panel, size=250)
        self.core.pack(padx=15, pady=(5, 0))
        self.voice_status = NovaLabel(
            panel,
            text=self._voice_idle_text(),
            font_size=11,
            text_color=styles["text_secondary"],
            wraplength=240,
        )
        self.voice_status.pack(padx=18, pady=(4, 12))

        self.audio_level = ctk.CTkProgressBar(
            panel,
            width=220,
            height=6,
            progress_color=styles["accent"],
            fg_color=styles["bg_secondary"],
        )
        self.audio_level.pack(pady=(0, 14))
        self.audio_level.set(0)

        self.listen_button = NovaButton(
            panel, text="ENGAGE VOICE", command=self.toggle_listening
        )
        self.listen_button.pack(fill="x", padx=24, pady=5)
        GhostButton(
            panel, text="STOP SPEAKING", command=self.voice_engine.stop_speaking
        ).pack(fill="x", padx=24, pady=5)

        NovaLabel(
            panel,
            text="AGENT PROFILE",
            font_size=9,
            bold=True,
            text_color=styles["text_muted"],
        ).pack(anchor="w", padx=24, pady=(14, 4))
        self._profile_by_name = {
            profile.name: key for key, profile in AGENT_PROFILES.items()
        }
        self.profile_menu = ctk.CTkOptionMenu(
            panel,
            values=list(self._profile_by_name),
            command=self._change_profile,
            fg_color=styles["bg_tertiary"],
            button_color=styles["accent_dim"],
            button_hover_color=styles["accent_hover"],
        )
        self.profile_menu.set(AGENT_PROFILES[self.session.profile_key].name)
        self.profile_menu.pack(fill="x", padx=24, pady=(0, 7))

        self.mode_menu = ctk.CTkSegmentedButton(
            panel,
            values=["Smart", "Controlled", "Chat"],
            command=self._change_mode,
            selected_color=styles["accent_dim"],
            selected_hover_color=styles["accent_hover"],
            unselected_color=styles["bg_tertiary"],
            unselected_hover_color=styles["bg_card_alt"],
        )
        self.mode_menu.set(self.session.mode.title())
        self.mode_menu.pack(fill="x", padx=24, pady=(0, 8))

        mode = "OPEN CHANNEL" if self.voice_engine.open_conversation else "WAKE WORD"
        NovaLabel(
            panel,
            text=f"VOICE PROTOCOL  //  {mode}",
            font_size=9,
            bold=True,
            text_color=styles["text_muted"],
        ).pack(side="bottom", pady=16)

    def _build_conversation_panel(self) -> None:
        panel = NovaFrame(self)
        panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=0)
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        SectionTitle(panel, "Command Stream", "ENCRYPTED // LOCAL").grid(
            row=0, column=0, sticky="ew", padx=16, pady=(15, 8)
        )
        self.transcript = ctk.CTkTextbox(
            panel,
            font=("Segoe UI", 13),
            wrap="word",
            fg_color=styles["bg_secondary"],
            text_color=styles["text_primary"],
            border_width=1,
            border_color=styles["border"],
            corner_radius=8,
        )
        self.transcript.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 10))
        self.transcript.configure(state="disabled")
        if self.session.history:
            for message in self.session.history:
                speaker = "YOU" if message["role"] == "user" else "NOVA"
                self._append(speaker, message["content"])
        else:
            self._append(
                "NOVA",
                "Command center online. Say the wake phrase, open the voice channel, "
                "or type a directive below. /help lists deterministic local skills.",
            )

        input_row = ctk.CTkFrame(panel, fg_color="transparent")
        input_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 15))
        input_row.grid_columnconfigure(0, weight=1)
        self.input_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Enter directive or /command...",
            height=42,
            fg_color=styles["bg_tertiary"],
            border_color=styles["border"],
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.input_entry.bind("<Return>", self.send_typed)
        self.send_button = NovaButton(input_row, text="EXECUTE", command=self.send_typed)
        self.send_button.grid(row=0, column=1)

    def _build_telemetry_panel(self) -> None:
        panel = NovaFrame(self)
        panel.grid(row=0, column=2, sticky="nsew", padx=(10, 0), pady=0)
        SectionTitle(panel, "Telemetry", "LIVE").pack(fill="x", padx=16, pady=(15, 8))
        self.health_label = NovaLabel(
            panel, text="SYSTEM // SCANNING", font_size=10, bold=True, text_color=styles["warning"]
        )
        self.health_label.pack(anchor="w", padx=16, pady=(0, 8))

        self.cpu_metric = MetricCard(panel, "CPU")
        self.cpu_metric.pack(fill="x", padx=12, pady=4)
        self.memory_metric = MetricCard(panel, "Memory")
        self.memory_metric.pack(fill="x", padx=12, pady=4)
        self.disk_metric = MetricCard(panel, "Storage")
        self.disk_metric.pack(fill="x", padx=12, pady=4)
        self.gpu_metric = MetricCard(panel, "GPU", styles["success"])
        self.gpu_metric.pack(fill="x", padx=12, pady=4)

        SectionTitle(panel, "Quick Directives").pack(fill="x", padx=16, pady=(18, 8))
        for label, command in (
            ("SYSTEM REPORT", "/status"),
            ("MODEL INVENTORY", "/models"),
            ("CAPABILITIES", "/help"),
            ("NEW SESSION", "/clear"),
        ):
            GhostButton(
                panel,
                text=label,
                height=32,
                command=lambda prompt=command: self._submit_prompt(prompt, False),
            ).pack(fill="x", padx=16, pady=3)
        GhostButton(
            panel,
            text="INGEST KNOWLEDGE",
            height=32,
            command=self._select_knowledge,
        ).pack(fill="x", padx=16, pady=3)

        self.host_label = NovaLabel(
            panel,
            text="NODE // --",
            font_size=9,
            text_color=styles["text_muted"],
        )
        self.host_label.pack(side="bottom", anchor="w", padx=16, pady=16)

    def _append(self, speaker: str, text: str) -> None:
        if self._closed:
            return
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{speaker}  //\n{text.strip()}\n\n")
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def show_alert(self, message: str) -> None:
        self._append("ALERT", message)

    def _voice_idle_text(self) -> str:
        if self.voice_engine.open_conversation:
            return "Open channel ready. No wake phrase required."
        return f'Awaiting “{self.voice_engine.wake_word.title()}” protocol.'

    def _persist_session_options(self) -> None:
        config = load_config()
        config["assistant_mode"] = self.session.mode
        config["agent_profile"] = self.session.profile_key
        save_config(config)

    def _change_profile(self, choice: str) -> None:
        self.session.set_profile(self._profile_by_name[choice])
        self._persist_session_options()
        self._append("SYSTEM", f"Agent profile changed to {choice}.")

    def _change_mode(self, choice: str) -> None:
        self.session.set_mode(choice.lower())
        self._persist_session_options()
        self._append("SYSTEM", f"Execution mode changed to {choice}.")

    def _select_knowledge(self) -> None:
        path = filedialog.askopenfilename(
            title="Add local knowledge to Nova",
            filetypes=[
                ("Knowledge files", "*.txt *.md *.pdf *.docx *.json *.csv *.py"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self._append("SYSTEM", "Indexing local knowledge...")

        def ingest() -> None:
            try:
                result = self.session.ingest_document(path)
            except Exception as exc:
                self.after(0, self._append, "FAULT", f"Knowledge import failed: {exc}")
            else:
                self.after(
                    0,
                    self._append,
                    "SYSTEM",
                    f"Indexed {result.filename}: {result.chunks} local memory chunks.",
                )

        threading.Thread(target=ingest, name="nova-knowledge-import", daemon=True).start()

    def send_typed(self, event=None):
        del event
        prompt = self.input_entry.get().strip()
        if prompt:
            self.input_entry.delete(0, "end")
            self._submit_prompt(prompt, False)
        return "break"

    def _submit_prompt(self, prompt: str, speak_response: bool) -> None:
        if self._closed:
            return
        if self._request_in_flight:
            self._append("SYSTEM", "A directive is already processing. Please hold.")
            return
        self._request_in_flight = True
        self._append("YOU", prompt)
        self.send_button.configure(state="disabled", text="PROCESSING")
        self.voice_status.configure(text="Analyzing directive...")

        def request() -> None:
            try:
                reply = self.session.respond(prompt)
            except Exception as exc:
                self.after(0, self._finish_response, None, str(exc), False)
            else:
                self.after(0, self._finish_response, reply, None, speak_response)

        threading.Thread(target=request, name="nova-command", daemon=True).start()

    def _finish_response(
        self,
        reply: AssistantReply | None,
        error: str | None,
        speak_response: bool,
    ) -> None:
        if self._closed:
            return
        if error:
            self._append("FAULT", error)
            self.core.set_state("error")
        else:
            assert reply is not None
            source = reply.command.upper() if reply.command else (reply.model or "LOCAL")
            self._append(f"NOVA [{source}]", reply.text)
            if speak_response:
                self.voice_engine.speak(reply.text)
        self._request_in_flight = False
        self.send_button.configure(state="normal", text="EXECUTE")
        self.input_entry.focus_set()
        self.voice_status.configure(text=self._voice_idle_text())

    def toggle_listening(self) -> None:
        if self._starting_voice:
            return
        if self.voice_engine.is_listening:
            self.voice_engine.stop_listening()
            self.listen_button.configure(text="ENGAGE VOICE")
            self.voice_status.configure(text="Voice channel suspended.")
            return
        self._starting_voice = True
        self.listen_button.configure(state="disabled", text="INITIALIZING...")

        def start() -> None:
            try:
                self.voice_engine.start_listening(self._on_voice_prompt)
            except Exception as exc:
                self.after(0, self._voice_failed, str(exc))
            else:
                self.after(0, self._voice_started)

        threading.Thread(target=start, name="nova-voice-start", daemon=True).start()

    def _on_voice_prompt(self, prompt: str) -> None:
        if not self._closed:
            self.after(0, self._submit_prompt, prompt, True)

    def _voice_started(self) -> None:
        if self._closed:
            self.voice_engine.stop_listening()
            return
        self._starting_voice = False
        self.listen_button.configure(state="normal", text="SUSPEND VOICE")
        self.voice_status.configure(text=self._voice_idle_text())

    def _voice_failed(self, error: str) -> None:
        if self._closed:
            return
        self._starting_voice = False
        self.listen_button.configure(state="normal", text="RETRY VOICE")
        self.voice_status.configure(text=f"Voice subsystem fault: {error}")
        self.core.set_state("error")

    def _refresh_runtime_state(self) -> None:
        if self._closed:
            return
        self.audio_level.set(self.voice_engine.current_audio_level)
        if self._request_in_flight:
            state = "thinking"
        elif self.voice_engine.tts_engine.is_speaking:
            state = "speaking"
        elif self.voice_engine.is_listening:
            state = "listening"
        else:
            state = "idle"
        self.core.set_state(state)
        self.after(80, self._refresh_runtime_state)

    def _poll_telemetry(self) -> None:
        if self._closed:
            return
        if not self._telemetry_in_flight:
            self._telemetry_in_flight = True

            def collect() -> None:
                try:
                    snapshot = self.session.monitor.snapshot()
                except Exception:
                    snapshot = None
                self.after(0, self._update_telemetry, snapshot)

            threading.Thread(target=collect, name="nova-telemetry", daemon=True).start()
        self.after(2500, self._poll_telemetry)

    def _update_telemetry(self, snapshot) -> None:
        self._telemetry_in_flight = False
        if self._closed or snapshot is None:
            return
        self.cpu_metric.update_value(snapshot.cpu_percent)
        memory_text = (
            f"{snapshot.memory_used_gb:.1f}G"
            if snapshot.memory_used_gb is not None
            else "--"
        )
        self.memory_metric.update_value(snapshot.memory_percent, memory_text)
        self.disk_metric.update_value(snapshot.disk_percent, f"{snapshot.disk_free_gb:.0f}G FREE")
        self.gpu_metric.update_value(
            snapshot.gpu_percent,
            snapshot.gpu_name[:16] if snapshot.gpu_name else "OFFLINE",
        )
        color = {
            "NOMINAL": styles["success"],
            "ELEVATED": styles["warning"],
            "CRITICAL": styles["error"],
        }[snapshot.health]
        self.health_label.configure(text=f"SYSTEM // {snapshot.health}", text_color=color)
        self.host_label.configure(
            text=f"NODE // {snapshot.hostname.upper()} // {snapshot.platform_name.upper()}"
        )

    def destroy(self) -> None:
        self._closed = True
        self.voice_engine.stop_listening()
        super().destroy()
