"""Choose among installed local models without silently using the cloud."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from core.ollama_manager import OllamaManager
from utils.config import load_config


class ModelRouter:
    CODE_TERMS = {
        "bug",
        "code",
        "compile",
        "debug",
        "error",
        "function",
        "python",
        "javascript",
        "typescript",
        "sql",
    }
    REASONING_TERMS = {
        "analyze",
        "compare",
        "design",
        "explain",
        "plan",
        "reason",
        "research",
        "tradeoff",
    }

    def __init__(
        self,
        default_model: str | None = None,
        ollama_manager: OllamaManager | None = None,
    ) -> None:
        config = load_config()
        self.default_model = default_model or config["model_name"]
        self.ollama_manager = ollama_manager or OllamaManager(
            host=config.get("ollama_host")
        )
        self.last_selected_model: str | None = None

    @staticmethod
    def _parameter_billions(model_name: str) -> float:
        matches = re.findall(r"(?:^|[:_-])(\d+(?:\.\d+)?)b(?:$|[:_-])", model_name.lower())
        return float(matches[-1]) if matches else 0.0

    @staticmethod
    def _response_content(response: Any) -> str:
        message = (
            response.get("message")
            if isinstance(response, Mapping)
            else getattr(response, "message", None)
        )
        if isinstance(message, Mapping):
            content = message.get("content")
        else:
            content = getattr(message, "content", None)
        if not isinstance(content, str):
            raise RuntimeError("Ollama returned a response without text content")
        return content

    def choose_model(self, prompt: str) -> str:
        installed = self.ollama_manager.get_installed_models()
        if not installed:
            raise RuntimeError(
                "No local Ollama models are installed. Pull one from Model Discovery first."
            )
        if len(installed) == 1:
            return installed[0]

        words = set(re.findall(r"[a-z0-9_+.-]+", prompt.lower()))
        code_task = bool(words & self.CODE_TERMS)
        reasoning_task = bool(words & self.REASONING_TERMS) or len(prompt) > 500

        def score(model: str) -> tuple[float, str]:
            lowered = model.lower()
            size = self._parameter_billions(model)
            default_weight = 1.0 if code_task or reasoning_task else 4.0
            value = default_weight if model == self.default_model else 0.0
            if code_task and any(term in lowered for term in ("code", "coder", "starcoder")):
                value += 10.0
            if reasoning_task:
                value += min(size, 20.0) / 4.0
            elif size:
                # Voice and short chat favor latency over parameter count.
                value += max(0.0, 4.0 - size / 3.0)
            if "cloud" in lowered:
                value -= 100.0
            return value, model

        return max(installed, key=score)

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
    ) -> str:
        user_prompt = next(
            (
                message["content"]
                for message in reversed(messages)
                if message.get("role") == "user"
            ),
            "",
        )
        selected = model or self.choose_model(user_prompt)
        self.last_selected_model = selected
        response = self.ollama_manager.chat(selected, messages)
        return self._response_content(response).strip()
