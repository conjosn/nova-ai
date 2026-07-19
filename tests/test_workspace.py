import tempfile
import unittest
from pathlib import Path

from core.workspace import WorkspaceLibrary


class FakeMemory:
    def __init__(self):
        self.records = []

    def add_memory(self, content, metadata):
        self.records.append((content, metadata))
        return str(len(self.records))


class WorkspaceLibraryTests(unittest.TestCase):
    def test_text_document_is_chunked_and_indexed_with_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.md"
            path.write_text("alpha " * 700, encoding="utf-8")
            memory = FakeMemory()
            result = WorkspaceLibrary(memory).ingest_file(path)
        self.assertGreater(result.chunks, 1)
        self.assertEqual(result.chunks, len(memory.records))
        self.assertIn("Document: notes.md", memory.records[0][0])
        self.assertEqual(memory.records[0][1]["type"], "document")

    def test_unsupported_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.zip"
            path.write_bytes(b"not a document")
            with self.assertRaisesRegex(ValueError, "Unsupported knowledge file"):
                WorkspaceLibrary.read_text(path)


if __name__ == "__main__":
    unittest.main()
