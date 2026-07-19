import customtkinter as ctk

from gui.components import NovaButton, NovaLabel
from gui.model_discovery import ModelDiscovery
from gui.settings_panel import SettingsPanel
from gui.text_mode import TextMode
from gui.voice_mode import VoiceMode
from utils.styles import NovaStyles

styles = NovaStyles.apply()


class MainWindow(ctk.CTk):
    def __init__(self, voice_engine, model_router):
        super().__init__()
        self.voice_engine = voice_engine
        self.model_router = model_router

        self.title("Nova — Neural Omni-Versatile Assistant")
        self.geometry("1280x780")
        self.minsize(980, 620)
        self.configure(fg_color=styles["bg_primary"])
        self.protocol("WM_DELETE_WINDOW", self._shutdown)

        top_bar = ctk.CTkFrame(
            self, fg_color=styles["bg_secondary"], height=55, corner_radius=0
        )
        top_bar.pack(fill="x")
        NovaLabel(top_bar, text="NOVA", font_size=22, bold=True).pack(
            side="left", padx=25, pady=12
        )

        navigation = ctk.CTkFrame(top_bar, fg_color="transparent")
        navigation.pack(side="right", padx=15)
        for label, command in (
            ("Voice", self.show_voice_mode),
            ("Text", self.show_text_mode),
            ("Models", self.show_model_discovery),
            ("Settings", self.show_settings),
        ):
            NovaButton(navigation, text=label, command=command).pack(
                side="left", padx=5
            )

        self.content = ctk.CTkFrame(self, fg_color=styles["bg_primary"])
        self.content.pack(fill="both", expand=True, padx=15, pady=10)
        self.current_frame = None
        self.show_voice_mode()

    def _show(self, frame_type, *args) -> None:
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = frame_type(self.content, *args)
        self.current_frame.pack(fill="both", expand=True)

    def show_voice_mode(self):
        self._show(VoiceMode, self.voice_engine, self.model_router)

    def show_text_mode(self):
        self._show(TextMode, self.model_router)

    def show_settings(self):
        self._show(SettingsPanel, self.voice_engine)

    def show_model_discovery(self):
        self._show(ModelDiscovery, self.model_router.ollama_manager)

    def _shutdown(self) -> None:
        self.voice_engine.shutdown()
        self.destroy()
