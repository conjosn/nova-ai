import customtkinter as ctk
from gui.voice_mode import VoiceMode
from gui.text_mode import TextMode
from gui.settings_panel import SettingsPanel
from gui.model_discovery import ModelDiscovery
from gui.components import NovaButton, NovaLabel
from utils.styles import NovaStyles

styles = NovaStyles.apply()

class MainWindow(ctk.CTk):
    def __init__(self, voice_engine, model_router):
        super().__init__()
        self.voice_engine = voice_engine
        self.model_router = model_router

        self.title("Nova — Neural Omni-Versatile Assistant")
        self.geometry("1280x780")
        self.minsize(1100, 650)
        self.configure(fg_color=styles["bg_primary"])

        top_bar = ctk.CTkFrame(self, fg_color=styles["bg_secondary"], height=55, corner_radius=0)
        top_bar.pack(fill="x")

        NovaLabel(top_bar, text="NOVA", font_size=22, bold=True).pack(side="left", padx=25, pady=12)

        btn_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_frame.pack(side="right", padx=15)

        NovaButton(btn_frame, text="Discover Models", command=self.show_model_discovery).pack(side="left", padx=6)
        NovaButton(btn_frame, text="Settings", command=self.show_settings).pack(side="left", padx=6)

        self.content = ctk.CTkFrame(self, fg_color=styles["bg_primary"])
        self.content.pack(fill="both", expand=True, padx=15, pady=10)

        self.current_frame = None
        self.show_voice_mode()

    def show_voice_mode(self):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = VoiceMode(self.content, self.voice_engine, self.model_router)
        self.current_frame.pack(fill="both", expand=True)

    def show_text_mode(self):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = TextMode(self.content, self.model_router)
        self.current_frame.pack(fill="both", expand=True)

    def show_settings(self):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = SettingsPanel(self.content, self.voice_engine)
        self.current_frame.pack(fill="both", expand=True)

    def show_model_discovery(self):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = ModelDiscovery(self.content)
        self.current_frame.pack(fill="both", expand=True)