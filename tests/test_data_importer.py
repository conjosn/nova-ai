import json
import tempfile
import unittest
from pathlib import Path

from core.data_importer import DataImporter


class FakeMemory:
    def __init__(self):
        self.records = []

    def add_memory(self, content, metadata):
        self.records.append((content, metadata))
        return str(len(self.records))


class DataImporterTests(unittest.TestCase):
    def test_imports_chatgpt_mapping_export_in_order(self):
        export = [
            {
                "title": "Test chat",
                "mapping": {
                    "assistant": {
                        "message": {
                            "create_time": 2,
                            "author": {"role": "assistant"},
                            "content": {"parts": ["Hello back"]},
                        }
                    },
                    "user": {
                        "message": {
                            "create_time": 1,
                            "author": {"role": "user"},
                            "content": {"parts": ["Hello"]},
                        }
                    },
                },
            }
        ]
        memory = FakeMemory()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "conversations.json"
            path.write_text(json.dumps(export), encoding="utf-8")
            count = DataImporter(memory).import_export(directory)

        self.assertEqual(count, 2)
        self.assertEqual([record[0] for record in memory.records], ["Hello", "Hello back"])
        self.assertEqual(memory.records[0][1]["source"], "chatgpt")

    def test_imports_claude_export(self):
        export = [
            {
                "name": "Claude chat",
                "chat_messages": [
                    {"sender": "human", "text": "Question"},
                    {"sender": "assistant", "text": "Answer"},
                ],
            }
        ]
        memory = FakeMemory()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "conversations.json"
            path.write_text(json.dumps(export), encoding="utf-8")
            count = DataImporter(memory).import_file(path)
        self.assertEqual(count, 2)
        self.assertEqual(memory.records[0][1]["type"], "user")
        self.assertEqual(memory.records[1][1]["type"], "assistant")


if __name__ == "__main__":
    unittest.main()
