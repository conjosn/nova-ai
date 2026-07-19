from __future__ import annotations

import threading

import customtkinter as ctk

from core.ollama_manager import OllamaManager
from gui.components import NovaButton, NovaFrame, NovaLabel
from utils.logger import NovaLogger

logger = NovaLogger()


class ModelDiscovery(ctk.CTkFrame):
    def __init__(self, master, ollama_manager: OllamaManager | None = None):
        super().__init__(master, fg_color="#0a0e17")
        self.ollama_manager = ollama_manager or OllamaManager()

        NovaLabel(self, text="MODEL DISCOVERY", font_size=20, bold=True).pack(pady=15)
        self.status = NovaLabel(self, text="Checking local Ollama models...", font_size=12)
        self.status.pack(pady=(0, 5))
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#111827")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        threading.Thread(
            target=self._load_models_worker,
            name="nova-model-discovery",
            daemon=True,
        ).start()

    def _load_models_worker(self) -> None:
        try:
            installed = self.ollama_manager.get_installed_models(refresh=True)
            error = None
        except Exception as exc:
            installed = []
            error = str(exc)
        recommended = self.ollama_manager.get_recommended_models()
        self.after(0, self._render_models, recommended, installed, error)

    def _render_models(self, recommended, installed, error) -> None:
        if not self.winfo_exists():
            return
        for widget in self.scroll.winfo_children():
            widget.destroy()
        if error:
            self.status.configure(text=error, text_color="#f87171")
        else:
            self.status.configure(
                text=f"{len(installed)} local model(s) installed",
                text_color="#8ba1b0",
            )
        for model in recommended:
            self.create_model_card(model, model["name"] in installed)

    def create_model_card(self, model_info, is_installed):
        card = NovaFrame(self.scroll)
        card.pack(fill="x", padx=10, pady=8)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(10, 5))
        NovaLabel(header, text=model_info["name"], font_size=16).pack(side="left")
        NovaLabel(header, text=model_info["size"], font_size=12).pack(side="right")

        NovaLabel(card, text=model_info["description"], font_size=12).pack(
            anchor="w", padx=15
        )
        NovaLabel(
            card,
            text=f"Best for: {model_info['recommended_for']}",
            font_size=11,
        ).pack(anchor="w", padx=15, pady=(0, 10))

        status_frame = ctk.CTkFrame(card, fg_color="transparent")
        status_frame.pack(fill="x", padx=15, pady=(0, 10))
        if is_installed:
            NovaLabel(status_frame, text="✓ Installed", font_size=13).pack(anchor="w")
        else:
            NovaButton(
                status_frame,
                text="Download",
                command=lambda: self.download_model(model_info["name"], status_frame),
            ).pack(anchor="w")

    def download_model(self, model_name, status_frame):
        for widget in status_frame.winfo_children():
            widget.destroy()
        progress = ctk.CTkProgressBar(
            status_frame, width=300, height=14, progress_color="#00eaff"
        )
        progress.pack(anchor="w", pady=5)
        progress.set(0)
        label = NovaLabel(status_frame, text="Starting download...", font_size=12)
        label.pack(anchor="w")

        def update_progress(data):
            total = data.get("total", 0)
            completed = data.get("completed", 0)
            if total:
                percent = max(0.0, min(1.0, completed / total))
                self.after(0, progress.set, percent)
                self.after(0, label.configure, {"text": f"{int(percent * 100)}%"})
            elif data.get("status"):
                self.after(0, label.configure, {"text": data["status"]})

        def download_worker():
            try:
                self.ollama_manager.pull_model(model_name, update_progress)
            except Exception as exc:
                self.after(
                    0,
                    label.configure,
                    {"text": f"Failed: {exc}", "text_color": "#f87171"},
                )
            else:
                self.after(
                    0,
                    label.configure,
                    {"text": "✓ Download complete", "text_color": "#22c55e"},
                )

        threading.Thread(
            target=download_worker,
            name=f"nova-pull-{model_name}",
            daemon=True,
        ).start()
