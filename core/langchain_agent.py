"""Conversation agent with retrieval memory and opt-in dataset refinement.

The historical class name is retained for compatibility. The implementation no
longer pulls in LangChain for a single Ollama call.
"""

from __future__ import annotations

import threading

from core.evol_instruct import EvolInstruct
from core.model_router import ModelRouter
from core.persistent_memory import PersistentMemory
from core.personality import Personality
from utils.logger import NovaLogger

logger = NovaLogger()


class LangChainAgent:
    def __init__(
        self,
        model_name: str = "gemma2:2b",
        auto_improve_interval_minutes: int = 60,
        *,
        auto_improve: bool = False,
    ) -> None:
        self.model_name = model_name
        self.model_router = ModelRouter(default_model=model_name)
        self.evolver = EvolInstruct(
            model=model_name,
            ollama_manager=self.model_router.ollama_manager,
        )
        self.persistent_memory = PersistentMemory()
        self.auto_improve_interval = max(5, auto_improve_interval_minutes) * 60
        self._stop_event = threading.Event()
        self._improvement_thread: threading.Thread | None = None

        if auto_improve:
            self._start_background_improvement()

    def _start_background_improvement(self) -> None:
        if self._improvement_thread and self._improvement_thread.is_alive():
            return
        self._stop_event.clear()
        self._improvement_thread = threading.Thread(
            target=self._background_loop,
            name="nova-refinement",
            daemon=True,
        )
        self._improvement_thread.start()
        logger.info("Opt-in background dataset refinement started")

    def _background_loop(self) -> None:
        # Wait before the first run so startup never triggers an expensive model call.
        while not self._stop_event.wait(self.auto_improve_interval):
            try:
                self.self_improve(8)
            except Exception:
                logger.exception("Background refinement failed")

    def shutdown(self) -> None:
        self._stop_event.set()
        if self._improvement_thread:
            self._improvement_thread.join(timeout=2.0)

    def self_improve(self, num_samples: int = 10) -> int:
        """Create deduplicated instruction variants; this does not train the model."""

        evolved = self.evolver.batch_evolve_from_memory(
            self.persistent_memory, num_samples
        )
        for text in evolved:
            self.persistent_memory.add_memory(text, {"type": "evolved"})
        return len(evolved)

    def evolve_skills(self, num_variations: int = 2) -> list[str]:
        return self.evolver.batch_evolve_from_memory(
            self.persistent_memory, max(1, num_variations)
        )

    def run(self, user_input: str) -> str:
        relevant = self.persistent_memory.retrieve_relevant(user_input, 4)
        context = "\n".join(f"- {item}" for item in relevant)
        messages = [
            {"role": "system", "content": Personality.get_system_prompt()},
        ]
        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Potentially relevant local memory:\n{context}",
                }
            )
        messages.append({"role": "user", "content": user_input})

        response = self.model_router.chat(messages, model=self.model_name)
        self.persistent_memory.add_memory(user_input, {"type": "user"})
        self.persistent_memory.add_memory(response, {"type": "assistant"})
        return response
