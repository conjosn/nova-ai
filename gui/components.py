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
            "font": ("Segoe UI", 12, "bold"),
            "border_width": 0,
        }
        defaults.update(kwargs)
        super().__init__(master, text=text, command=command, **defaults)

class NovaLabel(ctk.CTkLabel):
    def __init__(self, master, text, font_size=14, bold=False, **kwargs):
        font_weight = "bold" if bold else "normal"
        super().__init__(master, text=text, font=("Segoe UI", font_size, font_weight), **kwargs)

class NovaFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        defaults = {
            "fg_color": styles["bg_card"],
            "corner_radius": 12,
            "border_width": 1,
            "border_color": styles["border"],
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class GhostButton(NovaButton):
    def __init__(self, master, text, command=None, **kwargs):
        defaults = {
            "fg_color": "transparent",
            "hover_color": styles["bg_tertiary"],
            "text_color": styles["text_secondary"],
            "border_width": 1,
            "border_color": styles["border"],
        }
        defaults.update(kwargs)
        super().__init__(master, text=text, command=command, **defaults)


class SectionTitle(ctk.CTkFrame):
    def __init__(self, master, title: str, detail: str = ""):
        super().__init__(master, fg_color="transparent")
        NovaLabel(
            self,
            text=title.upper(),
            font_size=13,
            bold=True,
            text_color=styles["accent"],
        ).pack(side="left")
        if detail:
            NovaLabel(
                self,
                text=detail,
                font_size=11,
                text_color=styles["text_muted"],
            ).pack(side="right")
