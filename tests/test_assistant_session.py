import tempfile
import unittest
from pathlib import Path

from core.assistant_session import AssistantSession
from core.model_router import ModelRouter
from core.reminders import ReminderStore


class FakeManager:
    def __init__(self):
        self.models = ["gemma2:2b", "qwen-coder:7b"]
        self.calls = []

    def get_installed_models(self, refresh=False):
        del refresh
        return list(self.models)

    def chat(self, model, messages):
        self.calls.append((model, messages))
        return {"message": {"content": "Acknowledged."}}


class FakeSnapshot:
    def summary(self):
        return "System health is nominal."


class FakeMonitor:
    def snapshot(self):
        return FakeSnapshot()


class FakeMemory:
    def __init__(self):
        self.added = []

    def retrieve_relevant(self, prompt, n_results=3):
        del prompt, n_results
        return ["Connor prefers local tools."]

    def add_memory(self, content, metadata):
        self.added.append((content, metadata))
        return str(len(self.added))


class AssistantSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.manager = FakeManager()
        self.router = ModelRouter("gemma2:2b", self.manager)
        self.memory = FakeMemory()
        self.session = AssistantSession(
            self.router,
            monitor=FakeMonitor(),
            memory=self.memory,
            reminders=ReminderStore(Path(self.temp_dir.name) / "reminders.json"),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_local_skill_runs_without_model(self):
        reply = self.session.respond("/status")
        self.assertEqual(reply.source, "local")
        self.assertEqual(reply.command, "status")
        self.assertFalse(self.manager.calls)

    def test_model_response_uses_memory_and_records_turn(self):
        reply = self.session.respond("Help me plan dinner")
        self.assertEqual(reply.text, "Acknowledged.")
        self.assertEqual(len(self.session.history), 2)
        system_prompt = self.manager.calls[0][1][0]["content"]
        self.assertIn("Connor prefers local tools", system_prompt)
        self.assertEqual(len(self.memory.added), 1)

    def test_controlled_mode_blocks_unmatched_model_request(self):
        self.session.set_mode("controlled")
        reply = self.session.respond("write a poem")
        self.assertEqual(reply.command, "controlled")
        self.assertFalse(self.manager.calls)

    def test_engineer_profile_routes_to_coder(self):
        self.session.set_profile("engineer")
        reply = self.session.respond("make this faster")
        self.assertEqual(reply.model, "qwen-coder:7b")

    def test_reminder_skill_persists_reminder(self):
        reply = self.session.respond("remind me in 2 minutes to check the oven")
        self.assertEqual(reply.command, "reminder")
        self.assertEqual(self.session.reminders.pending()[0].text, "check the oven")


if __name__ == "__main__":
    unittest.main()
