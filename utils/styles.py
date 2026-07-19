import customtkinter as ctk


class NovaStyles:
    @staticmethod
    def apply():
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        return {
            "bg_primary": "#0a0c14",
            "bg_secondary": "#11151f",
            "bg_tertiary": "#161c2e",
            "bg_card": "#121826",
            "accent": "#00eaff",
            "accent_hover": "#00c4d4",
            "text_primary": "#e8f4f8",
            "text_secondary": "#8ba1b0",
            "success": "#22c55e",
            "error": "#f87171",
            "border": "#2a3245"
        }