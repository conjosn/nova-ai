"""Import conversation exports into Nova's local memory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.logger import NovaLogger

logger = NovaLogger()


class DataImporter:
    def __init__(self, memory: Any) -> None:
        self.memory = memory

    @staticmethod
    def _text_from_content(content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            return "\n".join(
                part.strip() for part in content if isinstance(part, str) and part.strip()
            )
        if isinstance(content, dict):
            parts = content.get("parts")
            if isinstance(parts, list):
                return DataImporter._text_from_content(parts)
            text = content.get("text")
            return text.strip() if isinstance(text, str) else ""
        return ""

    @classmethod
    def _chatgpt_messages(cls, conversation: dict[str, Any]) -> list[tuple[str, str]]:
        messages: list[tuple[str, str]] = []
        mapping = conversation.get("mapping")
        if isinstance(mapping, dict):
            nodes = sorted(
                mapping.values(),
                key=lambda node: (
                    (node.get("message") or {}).get("create_time") or 0
                    if isinstance(node, dict)
                    else 0
                ),
            )
            for node in nodes:
                message = node.get("message") if isinstance(node, dict) else None
                if not isinstance(message, dict):
                    continue
                author = message.get("author") or {}
                role = author.get("role", "unknown") if isinstance(author, dict) else "unknown"
                text = cls._text_from_content(message.get("content"))
                if text and role in {"user", "assistant"}:
                    messages.append((role, text))
            return messages

        for message in conversation.get("messages", []):
            if not isinstance(message, dict):
                continue
            role = message.get("role") or message.get("sender") or "unknown"
            text = cls._text_from_content(
                message.get("content", message.get("text", ""))
            )
            if text and role in {"user", "assistant", "human"}:
                messages.append(("user" if role == "human" else role, text))
        return messages

    @classmethod
    def _claude_messages(cls, conversation: dict[str, Any]) -> list[tuple[str, str]]:
        messages: list[tuple[str, str]] = []
        for message in conversation.get("chat_messages", []):
            if not isinstance(message, dict):
                continue
            sender = str(message.get("sender", "unknown")).lower()
            role = "user" if sender in {"human", "user"} else "assistant"
            text = cls._text_from_content(
                message.get("text", message.get("content", ""))
            )
            if text:
                messages.append((role, text))
        return messages

    def _store_conversation(
        self,
        messages: list[tuple[str, str]],
        *,
        source: str,
        title: str,
    ) -> int:
        count = 0
        for role, text in messages:
            memory_id = self.memory.add_memory(
                text,
                {
                    "type": role,
                    "source": source,
                    "conversation": title[:500],
                },
            )
            count += int(memory_id is not None)
        return count

    def import_file(self, path: str | Path) -> int:
        file_path = Path(path)
        data = json.loads(file_path.read_text(encoding="utf-8"))
        records = data if isinstance(data, list) else [data]
        count = 0
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            title = str(record.get("title") or record.get("name") or f"conversation-{index + 1}")
            if "chat_messages" in record:
                messages = self._claude_messages(record)
                source = "claude"
            else:
                messages = self._chatgpt_messages(record)
                source = "chatgpt"
            count += self._store_conversation(
                messages, source=source, title=title
            )
        return count

    def import_export(self, path: str | Path) -> int:
        export_path = Path(path).expanduser()
        if export_path.is_file():
            return self.import_file(export_path)
        if not export_path.is_dir():
            raise FileNotFoundError(f"Export path does not exist: {export_path}")

        candidates = sorted(
            {
                *export_path.rglob("conversations.json"),
                *export_path.rglob("chat_history.json"),
            }
        )
        if not candidates:
            candidates = sorted(export_path.glob("*.json"))
        if not candidates:
            raise FileNotFoundError("No supported conversation JSON file was found")

        total = 0
        errors: list[str] = []
        for candidate in candidates:
            try:
                total += self.import_file(candidate)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                logger.warning("Skipping %s: %s", candidate, exc)
                errors.append(candidate.name)
        if total == 0 and errors:
            raise ValueError("Conversation files were found but none could be imported")
        return total

    def import_chatgpt_export(self, path: str | Path) -> int:
        """Backward-compatible alias used by the original settings panel."""

        return self.import_export(path)
