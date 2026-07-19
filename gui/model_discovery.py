import customtkinter as ctk
import threading
from gui.components import NovaFrame, NovaLabel, NovaButton
from core.ollama_manager import OllamaManager
from utils.logger import NovaLogger

logger = NovaLogger()

class ModelDiscovery(ctk.CTkFrame):
    def __init__(self, master, ollama_manager: OllamaManager = None):
        super().__init__(master, fg_color="#0a0e17")

        self.ollama_manager = ollama_manager or OllamaManager()
        self.ollama_manager.refresh_installed_models()

        NovaLabel(self, text="MODEL DISCOVERY", font_size=20, bold=True).pack(pady=15)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#111827")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self.load_models()

    def load_models(self):
        recommended = self.ollama_manager.get_recommended_models()
        installed = self.ollama_manager.get_installed_models()

        for model in recommended:
            is_installed = model["name"] in installed
            self.create_model_card(model, is_installed)

    def create_model_card(self, model_info, is_installed):
        card = NovaFrame(self.scroll)
        card.pack(fill="x", padx=10, pady=8)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(10, 5))

        NovaLabel(header, text=model_info["name"], font_size=16).pack(side="left")
        NovaLabel(header, text=model_info["size"], font_size=12).pack(side="right")

        NovaLabel(card, text=model_info["description"], font_size=12).pack(anchor="w", padx=15)
        NovaLabel(card, text=f"Best for: {model_info['recommended_for']}", font_size=11).pack(anchor="w", padx=15, pady=(0, 10))

        status_frame = ctk.CTkFrame(card, fg_color="transparent")
        status_frame.pack(fill="x", padx=15, pady=(0, 10))

        if is_installed:
            NovaLabel(status_frame, text="✓ Installed", font_size=13).pack(anchor="w")
        else:
            btn = NovaButton(status_frame, text="Download", command=lambda: self.download_model(model_info["name"], status_frame))
            btn.pack(anchor="w")

    def download_model(self, model_name, status_frame):
        for widget in status_frame.winfo_children():
            widget.destroy()

        progress = ctk.CTkProgressBar(status_frame, width=300, height=14, progress_color="#00eaff")
        progress.pack(anchor="w", pady=5)
        progress.set(0)

        label = NovaLabel(status_frame, text="Starting download...", font_size=12)
        label.pack(anchor="w")

        def progress_callback(data):
            if 'total' in data and data['total'] > 0:
                percent = data['completed'] / data['total']
                progress.set(percent)
                label.configure(text=f"{int(percent*100)}%")

        def download_thread():
            try:
                self.ollama_manager.pull_model(model_name, progress_callback=progress_callback)
                label.configure(text="✓ Download Complete")
            except Exception as e:
                label.configure(text=f"Failed: {str(e)}")

        threading.Thread(target=download_thread, daemon=True).start()