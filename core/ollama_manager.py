"""Compatibility wrapper around the local Ollama Python client."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from utils.logger import NovaLogger

logger = NovaLogger()


class OllamaUnavailableError(RuntimeError):
    """Raised when the local Ollama service cannot be reached."""


class OllamaManager:
    RECOMMENDED_MODELS = (
        {
            "name": "gemma2:2b",
            "size": "~1.6 GB",
            "description": "Fast general model for small local nodes.",
            "recommended_for": "voice, chat, and lightweight tasks",
        },
        {
            "name": "gemma2:9b",
            "size": "~5.4 GB",
            "description": "Higher-quality general model for a stronger GPU.",
            "recommended_for": "reasoning and longer responses",
        },
        {
            "name": "qwen2.5-coder:7b",
            "size": "~4.7 GB",
            "description": "Coding-focused model for Nova's development tasks.",
            "recommended_for": "code generation and debugging",
        },
    )

    def __init__(
        self,
        host: str | None = None,
        cache_seconds: float = 15.0,
        client: Any | None = None,
    ) -> None:
        self.host = host or os.environ.get(
            "OLLAMA_HOST", "http://127.0.0.1:11434"
        )
        self.cache_seconds = cache_seconds
        self._client = client
        self._installed_models: list[str] = []
        self._last_refresh = 0.0

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from ollama import Client
            except ImportError as exc:
                raise OllamaUnavailableError(
                    "The 'ollama' Python package is not installed."
                ) from exc
            self._client = Client(host=self.host)
        return self._client

    @staticmethod
    def _field(value: Any, *names: str) -> Any:
        for name in names:
            if isinstance(value, Mapping) and name in value:
                return value[name]
            if hasattr(value, name):
                return getattr(value, name)
        return None

    def refresh_installed_models(self, force: bool = False) -> list[str]:
        now = time.monotonic()
        if not force and now - self._last_refresh < self.cache_seconds:
            return list(self._installed_models)

        try:
            response = self._get_client().list()
            models = self._field(response, "models") or []
            names = {
                str(name)
                for model in models
                if (name := self._field(model, "model", "name"))
            }
            self._installed_models = sorted(names)
            self._last_refresh = now
        except Exception as exc:
            raise OllamaUnavailableError(
                f"Cannot reach Ollama at {self.host}. Is the service running?"
            ) from exc
        return list(self._installed_models)

    def get_installed_models(self, refresh: bool = False) -> list[str]:
        if refresh or not self._installed_models:
            return self.refresh_installed_models(force=refresh)
        return list(self._installed_models)

    def get_recommended_models(self) -> list[dict[str, str]]:
        return [dict(model) for model in self.RECOMMENDED_MODELS]

    def pull_model(
        self,
        model_name: str,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        try:
            stream: Iterable[Any] = self._get_client().pull(
                model=model_name, stream=True
            )
            for update in stream:
                data = {
                    "status": self._field(update, "status") or "",
                    "total": self._field(update, "total") or 0,
                    "completed": self._field(update, "completed") or 0,
                }
                if progress_callback:
                    progress_callback(data)
            self.refresh_installed_models(force=True)
        except Exception as exc:
            raise OllamaUnavailableError(
                f"Failed to download Ollama model '{model_name}': {exc}"
            ) from exc

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        stream: bool = False,
        keep_alive: str = "10m",
    ) -> Any:
        try:
            return self._get_client().chat(
                model=model,
                messages=messages,
                stream=stream,
                keep_alive=keep_alive,
            )
        except Exception as exc:
            raise OllamaUnavailableError(
                f"Ollama could not run '{model}': {exc}"
            ) from exc
