"""Shared conversational brain for Nova's voice and text surfaces."""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.agent_profiles import AGENT_PROFILES, get_profile
from core.model_router import ModelRouter
from core.personality import Personality
from core.reminders import ReminderStore
from core.system_monitor import SystemMonitor
from utils.logger import NovaLogger

logger = NovaLogger()


@dataclass(frozen=True)
class AssistantReply:
    text: str
    source: str
    model: str | None = None
    command: str | None = None


@dataclass(frozen=True)
class LocalCommandResult:
    text: str
    command: str
    clear_history: bool = False


class LocalCommandRegistry:
    """Small allowlisted command layer; no arbitrary shell execution."""

    def __init__(
        self,
        monitor: SystemMonitor,
        model_router: ModelRouter,
        reminders: ReminderStore,
    ) -> None:
        self.monitor = monitor
        self.model_router = model_router
        self.reminders = reminders

    @staticmethod
    def _is(prompt: str, slash_command: str, phrases: tuple[str, ...]) -> bool:
        normalized = re.sub(r"[^a-z0-9/ ]+", "", prompt.lower()).strip()
        return normalized == slash_command or any(phrase in normalized for phrase in phrases)

    def execute(self, prompt: str) -> LocalCommandResult | None:
        if self._is(prompt, "/help", ("what can you do", "show commands")):
            return LocalCommandResult(
                "Available local commands: /status, /models, /time, /reminders, "
                "/remind me in 10 minutes to…, /clear, and /help. "
                "Everything else is routed to your installed local Ollama models.",
                "help",
            )
        if self._is(prompt, "/status", ("system status", "system health", "status report")):
            return LocalCommandResult(self.monitor.snapshot().summary(), "status")
        if self._is(prompt, "/time", ("what time is it", "current time", "todays date")):
            now = datetime.now().astimezone()
            time_text = now.strftime("%I:%M %p").lstrip("0")
            date_text = now.strftime("%A, %B %d, %Y").replace(" 0", " ")
            return LocalCommandResult(
                f"It is {time_text} on {date_text}.",
                "time",
            )
        if self._is(prompt, "/models", ("list models", "installed models", "model status")):
            try:
                models = self.model_router.ollama_manager.get_installed_models(refresh=True)
            except Exception as exc:
                return LocalCommandResult(f"I could not reach local Ollama: {exc}", "models")
            if not models:
                return LocalCommandResult("No local Ollama models are installed.", "models")
            return LocalCommandResult(
                f"{len(models)} local model(s) online: {', '.join(models)}.", "models"
            )
        reminder_match = re.fullmatch(
            r"(?:/remind|remind)\s+(?:me\s+)?in\s+(\d+)\s*"
            r"(seconds?|minutes?|hours?)\s+(?:to\s+)?(.+)",
            prompt.strip(),
            flags=re.IGNORECASE,
        )
        if reminder_match:
            amount = int(reminder_match.group(1))
            unit = reminder_match.group(2).lower()
            multiplier = 3600 if unit.startswith("hour") else 60 if unit.startswith("minute") else 1
            reminder = self.reminders.add_after(amount * multiplier, reminder_match.group(3))
            due = reminder.due_datetime.astimezone().strftime("%I:%M %p").lstrip("0")
            return LocalCommandResult(
                f"Reminder {reminder.id} armed for {due}: {reminder.text}", "reminder"
            )
        if self._is(prompt, "/reminders", ("list reminders", "pending reminders")):
            pending = self.reminders.pending()
            if not pending:
                return LocalCommandResult("No reminders are currently armed.", "reminders")
            details = "; ".join(
                f"{item.id} at {item.due_datetime.astimezone():%I:%M %p}: {item.text}"
                for item in pending[:8]
            )
            return LocalCommandResult(f"Pending reminders: {details}", "reminders")
        if self._is(prompt, "/clear", ("clear conversation", "new conversation")):
            return LocalCommandResult("Conversation context cleared.", "clear", True)
        return None


class AssistantSession:
    """Serialize responses and share context between every interaction surface."""

    def __init__(
        self,
        model_router: ModelRouter,
        *,
        monitor: SystemMonitor | None = None,
        memory: Any | None = None,
        reminders: ReminderStore | None = None,
        enable_memory: bool = True,
        max_history_messages: int = 16,
        mode: str = "smart",
        profile: str = "general",
    ) -> None:
        self.model_router = model_router
        self.monitor = monitor or SystemMonitor()
        self.reminders = reminders or ReminderStore()
        self.commands = LocalCommandRegistry(self.monitor, model_router, self.reminders)
        self.max_history_messages = max(4, max_history_messages)
        self._history: list[dict[str, str]] = []
        self._history_lock = threading.RLock()
        self._response_lock = threading.Lock()
        self._memory = memory
        self._memory_enabled = enable_memory
        self._memory_initialized = memory is not None or not enable_memory
        self.mode = mode if mode in {"smart", "controlled", "chat"} else "smart"
        self.profile_key = profile if profile in AGENT_PROFILES else "general"

    @property
    def history(self) -> list[dict[str, str]]:
        with self._history_lock:
            return [message.copy() for message in self._history]

    def clear(self) -> None:
        with self._history_lock:
            self._history.clear()

    def set_mode(self, mode: str) -> None:
        if mode not in {"smart", "controlled", "chat"}:
            raise ValueError(f"Unsupported assistant mode: {mode}")
        self.mode = mode

    def set_profile(self, profile: str) -> None:
        if profile not in AGENT_PROFILES:
            raise ValueError(f"Unknown agent profile: {profile}")
        self.profile_key = profile

    def ingest_document(self, path: str) -> Any:
        memory = self._get_memory()
        if memory is None:
            raise RuntimeError("Long-term memory is unavailable")
        from core.workspace import WorkspaceLibrary

        return WorkspaceLibrary(memory).ingest_file(path)

    def due_reminders(self) -> list[Any]:
        return self.reminders.pop_due()

    def _get_memory(self) -> Any | None:
        if self._memory_initialized:
            return self._memory
        self._memory_initialized = True
        try:
            from core.persistent_memory import PersistentMemory

            self._memory = PersistentMemory()
        except Exception:
            logger.exception("Long-term memory is unavailable; continuing without it")
            self._memory = None
        return self._memory

    def _append_turn(self, prompt: str, response: str) -> None:
        with self._history_lock:
            self._history.extend(
                [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": response},
                ]
            )
            overflow = len(self._history) - self.max_history_messages
            if overflow > 0:
                del self._history[:overflow]

    def _memory_context(self, prompt: str) -> list[str]:
        memory = self._get_memory()
        if memory is None:
            return []
        try:
            return memory.retrieve_relevant(prompt, n_results=3)
        except Exception:
            logger.exception("Memory retrieval failed")
            return []

    def _remember(self, prompt: str, response: str) -> None:
        memory = self._get_memory()
        if memory is None:
            return
        try:
            memory.add_memory(
                f"User: {prompt}\nNova: {response}",
                {"type": "conversation", "source": "nova-v2"},
            )
        except Exception:
            logger.exception("Conversation memory write failed")

    def respond(self, prompt: str) -> AssistantReply:
        normalized = prompt.strip()
        if not normalized:
            raise ValueError("Prompt cannot be empty")

        with self._response_lock:
            command = None if self.mode == "chat" else self.commands.execute(normalized)
            if command:
                if command.clear_history:
                    self.clear()
                else:
                    self._append_turn(normalized, command.text)
                return AssistantReply(
                    text=command.text,
                    source="local",
                    command=command.command,
                )
            if self.mode == "controlled":
                response = (
                    "No allowlisted local skill matched that directive. Switch to Smart or Chat "
                    "mode to route unmatched requests to a language model."
                )
                self._append_turn(normalized, response)
                return AssistantReply(response, source="local", command="controlled")

            memory_context = self._memory_context(normalized)
            profile = get_profile(self.profile_key)
            context_message = ""
            if memory_context:
                context_message = (
                    "\n\nRelevant private memory (use only when useful):\n- "
                    + "\n- ".join(memory_context)
                )
            with self._history_lock:
                messages = [
                    {
                        "role": "system",
                        "content": (
                            Personality.get_system_prompt()
                            + "\n\nActive agent profile: "
                            + profile.system_prompt
                            + context_message
                        ),
                    },
                    *[message.copy() for message in self._history],
                    {"role": "user", "content": normalized},
                ]
            selected_model = None
            if profile.routing_hint:
                selected_model = self.model_router.choose_model(
                    f"{normalized} {profile.routing_hint}"
                )
            response = self.model_router.chat(messages, model=selected_model)
            self._append_turn(normalized, response)
            self._remember(normalized, response)
            return AssistantReply(
                text=response,
                source="model",
                model=self.model_router.last_selected_model,
            )
