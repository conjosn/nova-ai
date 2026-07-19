"""Generate instruction variants for opt-in local refinement datasets."""

from __future__ import annotations

from typing import Any

from core.ollama_manager import OllamaManager
from utils.logger import NovaLogger

logger = NovaLogger()


class EvolInstruct:
    METHODS = {
        "in_depth": (
            "Rewrite the instruction to require deeper reasoning while preserving its "
            "original intent. Return only the rewritten instruction."
        ),
        "constraints": (
            "Rewrite the instruction with useful, testable constraints. Preserve its "
            "intent and return only the rewritten instruction."
        ),
    }

    def __init__(
        self,
        model: str = "gemma2:2b",
        ollama_manager: OllamaManager | None = None,
    ) -> None:
        self.model = model
        self.ollama_manager = ollama_manager or OllamaManager()

    @staticmethod
    def _content(response: Any) -> str:
        message = response.get("message") if isinstance(response, dict) else response.message
        content = message.get("content") if isinstance(message, dict) else message.content
        return str(content).strip()

    def evolve(self, instruction: str, method: str = "in_depth") -> str:
        guidance = self.METHODS.get(method, self.METHODS["in_depth"])
        prompt = f"{guidance}\n\nInstruction:\n{instruction.strip()}"
        try:
            response = self.ollama_manager.chat(
                self.model, [{"role": "user", "content": prompt}]
            )
            evolved = self._content(response)
            return evolved or instruction
        except Exception:
            logger.exception("Instruction evolution failed")
            return instruction

    def batch_evolve_from_memory(
        self, memory: Any, num_samples: int = 5
    ) -> list[str]:
        memories = memory.retrieve_relevant(
            "recent user requests", n_results=num_samples, memory_type="user"
        )
        return [self.evolve(item) for item in memories]
