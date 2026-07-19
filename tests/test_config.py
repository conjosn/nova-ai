import json
import tempfile
import unittest
from pathlib import Path

from utils.config import DEFAULT_CONFIG, load_config, save_config


class ConfigTests(unittest.TestCase):
    def test_missing_config_uses_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.json")
        self.assertEqual(config["model_name"], DEFAULT_CONFIG["model_name"])

    def test_saved_values_merge_with_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_config({"model_name": "test:1b"}, path)
            config = load_config(path)
            parsed = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(config["model_name"], "test:1b")
        self.assertEqual(config["wake_word"], DEFAULT_CONFIG["wake_word"])
        self.assertEqual(parsed, {"model_name": "test:1b"})

    def test_invalid_json_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text("{broken", encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config["model_name"], DEFAULT_CONFIG["model_name"])


if __name__ == "__main__":
    unittest.main()
