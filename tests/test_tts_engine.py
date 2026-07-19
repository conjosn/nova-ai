import unittest

from core.tts_engine import PiperTTSEngine


class TTSEngineTests(unittest.TestCase):
    def test_plain_string_is_split_into_sentences(self):
        chunks = list(PiperTTSEngine._normalize_source("First. Second!"))
        self.assertEqual(chunks, ["First.", "Second!"])

    def test_callable_stream_is_supported(self):
        chunks = list(PiperTTSEngine._normalize_source(lambda: ["hello ", "world."]))
        self.assertEqual(chunks, ["hello world."])


if __name__ == "__main__":
    unittest.main()
