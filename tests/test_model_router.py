import unittest

from core.model_router import ModelRouter


class FakeManager:
    def __init__(self, models):
        self.models = models
        self.calls = []

    def get_installed_models(self):
        return list(self.models)

    def chat(self, model, messages):
        self.calls.append((model, messages))
        return {"message": {"content": "  response text  "}}


class ModelRouterTests(unittest.TestCase):
    def test_default_model_handles_short_general_prompt(self):
        manager = FakeManager(["gemma2:2b", "qwen2.5-coder:7b"])
        router = ModelRouter("gemma2:2b", manager)
        self.assertEqual(router.choose_model("hello there"), "gemma2:2b")

    def test_coding_prompt_uses_installed_coder(self):
        manager = FakeManager(["gemma2:2b", "qwen2.5-coder:7b"])
        router = ModelRouter("gemma2:2b", manager)
        self.assertEqual(
            router.choose_model("debug this Python function"),
            "qwen2.5-coder:7b",
        )

    def test_reasoning_prompt_favors_larger_model(self):
        manager = FakeManager(["small:2b", "large:12b"])
        router = ModelRouter("small:2b", manager)
        self.assertEqual(router.choose_model("analyze these tradeoffs"), "large:12b")

    def test_cloud_model_is_never_automatically_selected(self):
        manager = FakeManager(["local:2b", "huge:120b-cloud"])
        router = ModelRouter("local:2b", manager)
        self.assertEqual(router.choose_model("analyze a hard problem"), "local:2b")

    def test_chat_returns_content_and_records_selected_model(self):
        manager = FakeManager(["gemma2:2b"])
        router = ModelRouter("gemma2:2b", manager)
        result = router.chat([{"role": "user", "content": "hello"}])
        self.assertEqual(result, "response text")
        self.assertEqual(manager.calls[0][0], "gemma2:2b")

    def test_no_installed_models_has_actionable_error(self):
        router = ModelRouter("gemma2:2b", FakeManager([]))
        with self.assertRaisesRegex(RuntimeError, "No local Ollama models"):
            router.choose_model("hello")


if __name__ == "__main__":
    unittest.main()
