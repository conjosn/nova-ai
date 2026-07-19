import customtkinter as ctk


class NovaStyles:
    @staticmethod
    def apply():
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        return {
            "bg_primary": "#03090f",
            "bg_secondary": "#06131c",
            "bg_tertiary": "#0a1d29",
            "bg_card": "#071722",
            "bg_card_alt": "#0a202d",
            "accent": "#45e6ff",
            "accent_hover": "#18bfd8",
            "accent_dim": "#14798a",
            "glow": "#8af3ff",
            "text_primary": "#e9fbff",
            "text_secondary": "#80a7b3",
            "text_muted": "#4d727d",
            "success": "#22c55e",
            "warning": "#fbbf24",
            "error": "#f87171",
            "border": "#123947",
            "grid": "#0d2d3a",
        }
