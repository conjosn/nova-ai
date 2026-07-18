import sounddevice as sd
import numpy as np
import threading
from faster_whisper import WhisperModel
import torch
from utils.logger import NovaLogger
from core.tts_engine import PiperTTSEngine

logger = NovaLogger()

class VoiceEngine:
    def __init__(self, mic_index: int = None):
        self.mic_index = mic_index
        self.is_listening = False
        self.wake_word = "hey nova"
        self.on_wake_word_callback = None
        self.current_audio_level = 0.0

        self.whisper = WhisperModel("base", device="cpu", compute_type="int8")

        self.vad_model, self.vad_utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False
        )
        self.get_speech_timestamps = self.vad_utils[0]

        self.tts_engine = PiperTTSEngine()

        logger.info("VoiceEngine initialized")

    def set_microphone(self, mic_index: int):
        self.mic_index = mic_index

    def set_speaker(self, speaker_index: int):
        pass

    def set_voice(self, model_path: str):
        if self.tts_engine.is_speaking:
            self.stop_speaking()
        self.tts_engine = PiperTTSEngine(model_path=model_path)
        logger.info(f"Voice changed to {model_path}")

    def speak(self, text: str):
        self.tts_engine.speak_streaming(text)

    def stop_speaking(self):
        self.tts_engine.stop()

    def start_listening(self, on_wake_word_callback):
        self.on_wake_word_callback = on_wake_word_callback
        self.is_listening = True

        audio_buffer = []
        is_speaking = False
        silence_counter = 0
        SILENCE_THRESHOLD = int(1.2 * (16000 / 512))

        def audio_callback(indata, frames, time_info, status):
            if not self.is_listening: return
            chunk = indata.flatten().astype(np.float32)
            self.current_audio_level = min(np.sqrt(np.mean(chunk**2)) * 8, 1.0)

            try:
                timestamps = self.get_speech_timestamps(chunk, self.vad_model, sampling_rate=16000)
                if timestamps:
                    if not is_speaking:
                        is_speaking = True
                        audio_buffer.clear()
                    silence_counter = 0
                    audio_buffer.extend(chunk)
                else:
                    if is_speaking:
                        silence_counter += 1
                        if silence_counter >= SILENCE_THRESHOLD:
                            is_speaking = False
                            silence_counter = 0
                            if len(audio_buffer) > 1600:
                                audio = np.array(audio_buffer, dtype=np.float32)
                                text = self._transcribe(audio)
                                if self.wake_word in text:
                                    prompt = text.replace(self.wake_word, "").strip()
                                    if prompt and self.on_wake_word_callback:
                                        self.on_wake_word_callback(prompt)
                            audio_buffer.clear()
            except Exception as e:
                logger.error(f"VAD error: {e}")

        self.stream = sd.InputStream(
            samplerate=16000, channels=1, dtype='float32',
            callback=audio_callback, device=self.mic_index, blocksize=512
        )
        self.stream.start()

    def _transcribe(self, audio):
        segments, _ = self.whisper.transcribe(audio, language="en", vad_filter=True)
        return " ".join([s.text for s in segments]).strip().lower()

    def stop_listening(self):
        self.is_listening = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()