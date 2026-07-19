import unittest
from types import SimpleNamespace

from core.ollama_manager import OllamaManager


class FakeClient:
    def list(self):
        return SimpleNamespace(
            models=[SimpleNamespace(model="zeta:2b"), {"name": "alpha:1b"}]
        )

    def pull(self, model, stream):
        self.pulled = (model, stream)
        return iter(
            [
                {"status": "pulling", "total": 10, "completed": 5},
                SimpleNamespace(status="done", total=10, completed=10),
            ]
        )

    def chat(self, **kwargs):
        return kwargs


class OllamaManagerTests(unittest.TestCase):
    def test_handles_object_and_mapping_response_shapes(self):
        manager = OllamaManager(client=FakeClient())
        self.assertEqual(
            manager.refresh_installed_models(), ["alpha:1b", "zeta:2b"]
        )

    def test_pull_reports_normalized_progress(self):
        manager = OllamaManager(client=FakeClient())
        updates = []
        manager.pull_model("alpha:1b", updates.append)
        self.assertEqual(updates[-1]["completed"], 10)

    def test_chat_stays_on_configured_host_client(self):
        manager = OllamaManager(client=FakeClient())
        result = manager.chat("alpha:1b", [{"role": "user", "content": "hi"}])
        self.assertEqual(result["model"], "alpha:1b")
        self.assertEqual(result["keep_alive"], "10m")


if __name__ == "__main__":
    unittest.main()
