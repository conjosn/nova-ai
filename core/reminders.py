"""Persistent, local reminder queue for Nova's proactive pulse."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from utils.paths import REMINDERS_PATH


@dataclass(frozen=True)
class Reminder:
    id: str
    text: str
    due_at: str
    created_at: str

    @property
    def due_datetime(self) -> datetime:
        return datetime.fromisoformat(self.due_at)


class ReminderStore:
    def __init__(self, path: Path = REMINDERS_PATH) -> None:
        self.path = path
        self._lock = threading.RLock()

    def _load(self) -> list[Reminder]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [Reminder(**item) for item in data if isinstance(item, dict)]
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return []

    def _save(self, reminders: list[Reminder]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump([asdict(reminder) for reminder in reminders], handle, indent=2)
                handle.write("\n")
            os.replace(temporary_name, self.path)
        except Exception:
            with suppress(OSError):
                os.unlink(temporary_name)
            raise

    def add_after(self, seconds: int, text: str) -> Reminder:
        if seconds <= 0:
            raise ValueError("Reminder delay must be positive")
        normalized = text.strip()
        if not normalized:
            raise ValueError("Reminder text cannot be empty")
        now = datetime.now(timezone.utc)
        reminder = Reminder(
            id=uuid.uuid4().hex[:8],
            text=normalized,
            due_at=(now + timedelta(seconds=seconds)).isoformat(),
            created_at=now.isoformat(),
        )
        with self._lock:
            reminders = self._load()
            reminders.append(reminder)
            self._save(reminders)
        return reminder

    def pending(self) -> list[Reminder]:
        with self._lock:
            return sorted(self._load(), key=lambda reminder: reminder.due_at)

    def cancel(self, reminder_id: str) -> bool:
        with self._lock:
            reminders = self._load()
            remaining = [item for item in reminders if item.id != reminder_id]
            if len(remaining) == len(reminders):
                return False
            self._save(remaining)
            return True

    def pop_due(self, now: datetime | None = None) -> list[Reminder]:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        with self._lock:
            reminders = self._load()
            due = [item for item in reminders if item.due_datetime <= current]
            if due:
                due_ids = {item.id for item in due}
                self._save([item for item in reminders if item.id not in due_ids])
            return due
