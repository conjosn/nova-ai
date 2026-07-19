from __future__ import annotations

from datetime import datetime

import customtkinter as ctk

from core.assistant_session import AssistantSession
from gui.command_center import CommandCenter
from gui.components import GhostButton, NovaLabel
from gui.model_discovery import ModelDiscovery
from gui.settings_panel import SettingsPanel
from gui.text_mode import TextMode
from utils.config import load_config
from utils.styles import NovaStyles

styles = NovaStyles.apply()


class MainWindow(ctk.CTk):
    def __init__(self, voice_engine, model_router):
        super().__init__()
        self.voice_engine = voice_engine
        self.model_router = model_router
        config = load_config()
        self.session = AssistantSession(
            model_router,
            mode=config.get("assistant_mode", "smart"),
            profile=config.get("agent_profile", "general"),
        )
        self.current_frame = None
        self._nav_buttons: dict[str, GhostButton] = {}

        self.title("Nova // Local Intelligence Command Center")
        self.geometry("1440x860")
        self.minsize(1120, 700)
        self.configure(fg_color=styles["bg_primary"])
        self.protocol("WM_DELETE_WINDOW", self._shutdown)

        self.shell = ctk.CTkFrame(self, fg_color=styles["bg_primary"], corner_radius=0)
        self.shell.pack(fill="both", expand=True)
        self._build_sidebar()
        self._build_workspace()
        self.show_command_center()
        self.after(250, self._refresh_clock)
        self.after(1000, self._poll_reminders)

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(
            self.shell,
            width=205,
            fg_color=styles["bg_secondary"],
            corner_radius=0,
            border_width=0,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(24, 30))
        NovaLabel(
            brand,
            text="N O V A",
            font_size=22,
            bold=True,
            text_color=styles["accent"],
        ).pack(anchor="w")
        NovaLabel(
            brand,
            text="LOCAL INTELLIGENCE",
            font_size=9,
            bold=True,
            text_color=styles["text_muted"],
        ).pack(anchor="w", pady=(2, 0))

        for key, label, command in (
            ("center", "COMMAND CENTER", self.show_command_center),
            ("console", "NEURAL CONSOLE", self.show_text_mode),
            ("models", "MODEL ARMORY", self.show_model_discovery),
            ("settings", "SYSTEM CONFIG", self.show_settings),
        ):
            button = GhostButton(
                sidebar,
                text=label,
                command=command,
                anchor="w",
                height=42,
                corner_radius=6,
            )
            button.pack(fill="x", padx=14, pady=4)
            self._nav_buttons[key] = button

        privacy = ctk.CTkFrame(sidebar, fg_color="transparent")
        privacy.pack(side="bottom", fill="x", padx=18, pady=20)
        NovaLabel(
            privacy,
            text="●  PRIVATE NODE",
            font_size=10,
            bold=True,
            text_color=styles["success"],
        ).pack(anchor="w")
        NovaLabel(
            privacy,
            text="No cloud routing",
            font_size=9,
            text_color=styles["text_muted"],
        ).pack(anchor="w", pady=(2, 0))

    def _build_workspace(self) -> None:
        workspace = ctk.CTkFrame(
            self.shell, fg_color=styles["bg_primary"], corner_radius=0
        )
        workspace.pack(side="right", fill="both", expand=True)

        top_bar = ctk.CTkFrame(
            workspace,
            fg_color=styles["bg_primary"],
            height=66,
            corner_radius=0,
            border_width=0,
        )
        top_bar.pack(fill="x", padx=18)
        top_bar.pack_propagate(False)
        self.page_title = NovaLabel(
            top_bar,
            text="COMMAND CENTER",
            font_size=16,
            bold=True,
            text_color=styles["text_primary"],
        )
        self.page_title.pack(side="left", pady=20)
        self.alert_banner = NovaLabel(
            top_bar,
            text="",
            font_size=10,
            bold=True,
            text_color=styles["warning"],
        )
        self.alert_banner.pack(side="left", padx=30, pady=20)
        self.clock = NovaLabel(
            top_bar,
            text="",
            font_size=11,
            bold=True,
            text_color=styles["text_secondary"],
        )
        self.clock.pack(side="right", pady=20)

        self.content = ctk.CTkFrame(workspace, fg_color=styles["bg_primary"])
        self.content.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def _set_active(self, key: str, title: str) -> None:
        for name, button in self._nav_buttons.items():
            if name == key:
                button.configure(
                    fg_color=styles["bg_tertiary"],
                    text_color=styles["accent"],
                    border_color=styles["accent_dim"],
                )
            else:
                button.configure(
                    fg_color="transparent",
                    text_color=styles["text_secondary"],
                    border_color=styles["border"],
                )
        self.page_title.configure(text=title)

    def _show(self, key: str, title: str, frame_type, *args) -> None:
        if self.current_frame:
            self.current_frame.destroy()
        self._set_active(key, title)
        self.current_frame = frame_type(self.content, *args)
        self.current_frame.pack(fill="both", expand=True)

    def show_command_center(self) -> None:
        self._show(
            "center",
            "COMMAND CENTER  //  OVERVIEW",
            CommandCenter,
            self.voice_engine,
            self.session,
        )

    def show_text_mode(self) -> None:
        self._show("console", "NEURAL CONSOLE  //  SESSION", TextMode, self.session)

    def show_settings(self) -> None:
        self._show("settings", "SYSTEM CONFIGURATION", SettingsPanel, self.voice_engine)

    def show_model_discovery(self) -> None:
        self._show(
            "models",
            "MODEL ARMORY  //  LOCAL OLLAMA",
            ModelDiscovery,
            self.model_router.ollama_manager,
        )

    def _refresh_clock(self) -> None:
        if not self.winfo_exists():
            return
        self.clock.configure(text=datetime.now().astimezone().strftime("%A  //  %H:%M:%S"))
        self.after(1000, self._refresh_clock)

    def _poll_reminders(self) -> None:
        if not self.winfo_exists():
            return
        for reminder in self.session.due_reminders():
            message = f"Reminder: {reminder.text}"
            self.alert_banner.configure(text=f"ALERT // {reminder.text.upper()}")
            if hasattr(self.current_frame, "show_alert"):
                self.current_frame.show_alert(message)
            self.voice_engine.speak(message)
            self.after(12000, self.alert_banner.configure, {"text": ""})
        self.after(1000, self._poll_reminders)

    def _shutdown(self) -> None:
        self.voice_engine.shutdown()
        self.destroy()
