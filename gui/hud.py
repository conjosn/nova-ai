"""Code-native HUD widgets used by the Nova command center."""

from __future__ import annotations

import math
import tkinter as tk

import customtkinter as ctk

from gui.components import NovaFrame, NovaLabel
from utils.styles import NovaStyles

styles = NovaStyles.apply()


class NeuralCore(tk.Canvas):
    COLORS = {
        "idle": styles["accent_dim"],
        "listening": styles["accent"],
        "thinking": styles["warning"],
        "speaking": styles["success"],
        "error": styles["error"],
    }

    def __init__(self, master, size: int = 250) -> None:
        super().__init__(
            master,
            width=size,
            height=size,
            bg=styles["bg_card"],
            highlightthickness=0,
            bd=0,
        )
        self.size = size
        self.center = size / 2
        self.state = "idle"
        self.phase = 0.0
        self._closed = False
        self._rings: list[int] = []
        self._arcs: list[int] = []
        self._build()
        self.after(40, self._animate)

    def _build(self) -> None:
        c = self.center
        for radius in (108, 88, 66):
            self._rings.append(
                self.create_oval(
                    c - radius,
                    c - radius,
                    c + radius,
                    c + radius,
                    outline=styles["grid"],
                    width=1,
                )
            )
        for index in range(12):
            self._arcs.append(
                self.create_arc(
                    25,
                    25,
                    self.size - 25,
                    self.size - 25,
                    start=index * 30,
                    extent=17,
                    style="arc",
                    outline=styles["accent_dim"],
                    width=3,
                )
            )
        self._core_glow = self.create_oval(78, 78, 172, 172, fill="#092e39", outline="")
        self._core = self.create_oval(
            91, 91, 159, 159, fill=styles["bg_secondary"], outline=styles["accent"], width=2
        )
        self._name = self.create_text(
            c,
            c - 5,
            text="NOVA",
            fill=styles["text_primary"],
            font=("Segoe UI", 17, "bold"),
        )
        self._state_text = self.create_text(
            c,
            c + 18,
            text="STANDBY",
            fill=styles["text_secondary"],
            font=("Consolas", 8, "bold"),
        )

    def set_state(self, state: str) -> None:
        self.state = state if state in self.COLORS else "idle"
        self.itemconfigure(self._state_text, text=self.state.upper())

    def _animate(self) -> None:
        if self._closed:
            return
        self.phase += 0.08
        color = self.COLORS[self.state]
        speed = 2.0 if self.state in {"thinking", "speaking"} else 1.0
        for index, arc in enumerate(self._arcs):
            self.itemconfigure(
                arc,
                start=index * 30 + self.phase * 18 * speed,
                outline=color if index % 2 == 0 else styles["accent_dim"],
            )
        pulse = (math.sin(self.phase * (2.2 if self.state != "idle" else 1.0)) + 1) / 2
        inset = 75 - pulse * 4
        self.coords(self._core_glow, inset, inset, self.size - inset, self.size - inset)
        self.itemconfigure(self._core, outline=color)
        self.after(40, self._animate)

    def destroy(self) -> None:
        self._closed = True
        super().destroy()


class MetricCard(NovaFrame):
    def __init__(self, master, label: str, color: str | None = None) -> None:
        super().__init__(master, fg_color=styles["bg_card_alt"], corner_radius=9)
        self.color = color or styles["accent"]
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(9, 3))
        NovaLabel(
            header, text=label.upper(), font_size=10, bold=True, text_color=styles["text_muted"]
        ).pack(side="left")
        self.value = NovaLabel(
            header, text="--", font_size=12, bold=True, text_color=styles["text_primary"]
        )
        self.value.pack(side="right")
        self.bar = ctk.CTkProgressBar(
            self,
            height=5,
            progress_color=self.color,
            fg_color=styles["bg_secondary"],
        )
        self.bar.pack(fill="x", padx=12, pady=(3, 10))
        self.bar.set(0)

    def update_value(self, value: float | None, text: str | None = None) -> None:
        self.bar.set(0 if value is None else max(0.0, min(1.0, value / 100.0)))
        self.value.configure(text=text or ("--" if value is None else f"{value:.0f}%"))
