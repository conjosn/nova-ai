import threading
import time
from core.evol_instruct import EvolInstruct
from core.persistent_memory import PersistentMemory
from utils.logger import NovaLogger

logger = NovaLogger()

class LangChainAgent:
    def __init__(self, model_name: str = "gemma2:9b", auto_improve_interval_minutes: int = 30):
        self.model_name = model_name
        self.evolver = EvolInstruct(model=model_name)
        self.persistent_memory = PersistentMemory()

        self.auto_improve_interval = auto_improve_interval_minutes * 60
        self._stop_improvement_thread = False
        self._improvement_thread = None

        self._start_background_improvement()

    def _start_background_improvement(self):
        self._stop_improvement_thread = False
        self._improvement_thread = threading.Thread(target=self._background_loop, daemon=True)
        self._improvement_thread.start()
        logger.info("Background self-improvement started")

    def _background_loop(self):
        while not self._stop_improvement_thread:
            try:
                self.self_improve(8)
            except Exception as e:
                logger.error(f"Background error: {e}")
            time.sleep(self.auto_improve_interval)

    def shutdown(self):
        self._stop_improvement_thread = True

    def self_improve(self, num_samples=10):
        evolved = self.evolver.batch_evolve_from_memory(self.persistent_memory, num_samples)
        for text in evolved:
            self.persistent_memory.add_memory(text, {"type": "evolved"})

    def evolve_skills(self, num_variations=2):
        pass

    def run(self, user_input: str):
        relevant = self.persistent_memory.retrieve_relevant(user_input, 4)
        context = "\n".join(relevant) if relevant else ""
        prompt = f"Context:\n{context}\n\nUser: {user_input}\nNova:"
        try:
            import ollama
            response = ollama.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}])
            return response['message']['content']
        except Exception as e:
            return f"Error: {str(e)}"