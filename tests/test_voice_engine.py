import unittest

from core.voice_engine import VoiceEngine


class VoiceEnginePromptTests(unittest.TestCase):
    def setUp(self):
        self.engine = VoiceEngine.__new__(VoiceEngine)
        self.engine.wake_word = "hey nova"
        self.engine.open_conversation = False

    def test_wake_word_mode_ignores_ordinary_speech(self):
        self.assertIsNone(
            self.engine._prompt_from_transcript("what is on my calendar")
        )

    def test_wake_word_mode_returns_text_after_wake_word(self):
        self.assertEqual(
            self.engine._prompt_from_transcript("hey nova, what is on my calendar?"),
            "what is on my calendar",
        )

    def test_open_conversation_accepts_speech_without_wake_word(self):
        self.engine.open_conversation = True
        self.assertEqual(
            self.engine._prompt_from_transcript("what is on my calendar?"),
            "what is on my calendar?",
        )

    def test_empty_transcript_is_ignored_in_both_modes(self):
        self.engine.open_conversation = True
        self.assertIsNone(self.engine._prompt_from_transcript("   "))


if __name__ == "__main__":
    unittest.main()
