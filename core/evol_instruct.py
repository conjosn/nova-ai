import ollama
import random
from utils.logger import NovaLogger

logger = NovaLogger()

class EvolInstruct:
    def __init__(self, model="gemma2:9b"):
        self.model = model

    def evolve(self, instruction, method="in_depth"):
        prompt = f"Make this instruction more complex and high-quality:\n\n{instruction}"
        try:
            response = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            return response['message']['content'].strip()
        except:
            return instruction

    def batch_evolve_from_memory(self, memory, num_samples=5):
        memories = memory.retrieve_relevant("recent conversation", n_results=num_samples)
        return [self.evolve(m) for m in memories]