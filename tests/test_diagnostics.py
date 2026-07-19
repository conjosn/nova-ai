import json
import tempfile
import unittest
from pathlib import Path

from diagnose_nova import choose_test_model, piper_sample_rate


class DiagnosticsTests(unittest.TestCase):
    def test_model_selection_honors_installed_preference(self):
        models = ["other:3b", "gemma2:2b"]
        self.assertEqual(choose_test_model(models, "gemma2:2b"), "gemma2:2b")

    def test_model_selection_never_chooses_cloud(self):
        models = ["huge:120b-cloud", "local:2b"]
        self.assertEqual(choose_test_model(models, "huge:120b-cloud"), "local:2b")
        self.assertIsNone(choose_test_model(["huge:120b-cloud"], None))

    def test_piper_sample_rate_reads_companion_config(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "voice.onnx"
            Path(f"{model}.json").write_text(
                json.dumps({"audio": {"sample_rate": 16000}}), encoding="utf-8"
            )
            self.assertEqual(piper_sample_rate(model), 16000)

    def test_piper_sample_rate_has_safe_default(self):
        self.assertEqual(piper_sample_rate(Path("missing.onnx")), 22050)


if __name__ == "__main__":
    unittest.main()
