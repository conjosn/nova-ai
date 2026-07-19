import customtkinter as ctk

from utils.styles import NovaStyles

styles = NovaStyles.apply()

class NovaButton(ctk.CTkButton):
    def __init__(self, master, text, command=None, **kwargs):
        defaults = {
            "fg_color": styles["accent"],
            "hover_color": styles["accent_hover"],
            "text_color": "black",
            "corner_radius": 8,
            "height": 36,
        }
        defaults.update(kwargs)
        super().__init__(master, text=text, command=command, **defaults)

class NovaLabel(ctk.CTkLabel):
    def __init__(self, master, text, font_size=14, bold=False, **kwargs):
        font_weight = "bold" if bold else "normal"
        super().__init__(master, text=text, font=("Segoe UI", font_size, font_weight), **kwargs)

class NovaFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=styles["bg_card"], corner_radius=12, **kwargs)
