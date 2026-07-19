import inspect
import unittest

from core.tts_engine import PiperTTSEngine


class TTSEngineTests(unittest.TestCase):
    def test_plain_string_is_split_into_sentences(self):
        chunks = list(PiperTTSEngine._normalize_source("First. Second!"))
        self.assertEqual(chunks, ["First.", "Second!"])

    def test_callable_stream_is_supported(self):
        chunks = list(PiperTTSEngine._normalize_source(lambda: ["hello ", "world."]))
        self.assertEqual(chunks, ["hello world."])

    def test_playback_uses_callback_api_instead_of_blocking_write(self):
        source = inspect.getsource(PiperTTSEngine._play_chunk)
        self.assertIn("callback=audio_callback", source)
        self.assertNotIn("stream.write", source)


if __name__ == "__main__":
    unittest.main()
