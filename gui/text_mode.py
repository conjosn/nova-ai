import customtkinter as ctk
import ollama
from gui.components import NovaButton, NovaLabel
from core.model_router import ModelRouter
from core.personality import Personality
from utils.styles import NovaStyles

styles = NovaStyles.apply()

class TextMode(ctk.CTkFrame):
    def __init__(self, master, model_router: ModelRouter):
        super().__init__(master, fg_color=styles["bg_primary"])

        self.model_router = model_router

        NovaLabel(self, text="TEXT MODE", font_size=18, bold=True).pack(pady=15)

        self.chat_box = ctk.CTkTextbox(self, font=("Segoe UI", 14), height=400)
        self.chat_box.pack(fill="both", expand=True, padx=30, pady=10)

        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=30, pady=10)

        self.input_entry = ctk.CTkEntry(input_frame, placeholder_text="Type your message...", height=40)
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input_entry.bind("<Return>", self.send_message)

        NovaButton(input_frame, text="Send", command=self.send_message).pack(side="right")

    def send_message(self, event=None):
        message = self.input_entry.get().strip()
        if not message:
            return

        self.chat_box.insert("end", f"You: {message}\n\n")
        self.input_entry.delete(0, "end")

        try:
            chosen_model = self.model_router.choose_model(message)
            response = ollama.chat(
                model=chosen_model,
                messages=[
                    {"role": "system", "content": Personality.get_system_prompt()},
                    {"role": "user", "content": message}
                ]
            )['message']['content']

            self.chat_box.insert("end", f"Nova: {response}\n\n")
        except Exception as e:
            self.chat_box.insert("end", f"Error: {str(e)}\n\n")

        self.chat_box.see("end")