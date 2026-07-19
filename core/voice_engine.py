"""Low-latency wake-word capture with GPU-first transcription."""

from __future__ import annotations

import os
import queue
import threading
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from core.tts_engine import PiperTTSEngine
from utils.config import load_config
from utils.logger import NovaLogger

logger = NovaLogger()


class VoiceEngine:
    SAMPLE_RATE = 16000
    BLOCK_SIZE = 512

    def __init__(
        self,
        mic_index: int | None = None,
        speaker_index: int | None = None,
        *,
        whisper_model: str | None = None,
        whisper_device: str | None = None,
        wake_word: str | None = None,
        energy_threshold: float = 0.012,
    ) -> None:
        config = load_config()
        self.mic_index = mic_index
        self.speaker_index = speaker_index
        self.whisper_model_name = whisper_model or config["whisper_model"]
        self.whisper_device = whisper_device or config["whisper_device"]
        self.wake_word = (wake_word or config["wake_word"]).strip().lower()
        self.energy_threshold = max(0.001, float(energy_threshold))

        self.is_listening = False
        self.on_wake_word_callback: Callable[[str], None] | None = None
        self.current_audio_level = 0.0
        self.stream: Any | None = None
        self._whisper: Any | None = None
        self._audio_queue: queue.Queue[Any] = queue.Queue(maxsize=4)
        self._stop_event = threading.Event()
        self._transcription_thread: threading.Thread | None = None
        self._state_lock = threading.RLock()

        self.tts_engine = PiperTTSEngine(
            model_path=config.get("voice_model"), output_device=speaker_index
        )
        logger.info("Voice engine ready; speech models will load on first listen")

    def set_microphone(self, mic_index: int | None) -> None:
        self.mic_index = mic_index

    def set_speaker(self, speaker_index: int | None) -> None:
        self.speaker_index = speaker_index
        self.tts_engine.set_output_device(speaker_index)

    def set_voice(self, model_path: str) -> None:
        self.stop_speaking()
        self.tts_engine = PiperTTSEngine(
            model_path=model_path, output_device=self.speaker_index
        )
        logger.info("Voice changed to %s", model_path)

    def speak(self, text: str) -> threading.Thread:
        return self.tts_engine.speak_streaming(text)

    def stop_speaking(self) -> None:
        self.tts_engine.stop()

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import ctranslate2

            return ctranslate2.get_cuda_device_count() > 0
        except (ImportError, RuntimeError):
            return False

    def _ensure_whisper(self) -> Any:
        if self._whisper is not None:
            return self._whisper
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("faster-whisper is not installed") from exc

        requested = os.environ.get("NOVA_WHISPER_DEVICE", self.whisper_device)
        device = "cuda" if requested == "auto" and self._cuda_available() else requested
        if device == "auto":
            device = "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        try:
            self._whisper = WhisperModel(
                self.whisper_model_name, device=device, compute_type=compute_type
            )
        except Exception:
            if device != "cuda":
                raise
            logger.exception("CUDA Whisper initialization failed; falling back to CPU")
            device, compute_type = "cpu", "int8"
            self._whisper = WhisperModel(
                self.whisper_model_name, device=device, compute_type=compute_type
            )
        logger.info(
            "Whisper loaded on %s with %s compute", device, compute_type
        )
        return self._whisper

    def start_listening(self, on_wake_word_callback: Callable[[str], None]) -> None:
        with self._state_lock:
            if self.is_listening:
                return

        self._stop_event.clear()

        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("Voice input dependencies are not installed") from exc

        self._ensure_whisper()
        if self._stop_event.is_set():
            return
        self.on_wake_word_callback = on_wake_word_callback
        self._audio_queue = queue.Queue(maxsize=4)
        self._transcription_thread = threading.Thread(
            target=self._transcription_loop,
            name="nova-transcription",
            daemon=True,
        )
        self._transcription_thread.start()

        state: dict[str, Any] = {
            "audio": [],
            "speaking": False,
            "silence_blocks": 0,
            "sample_count": 0,
        }
        silence_limit = max(1, int(0.9 * self.SAMPLE_RATE / self.BLOCK_SIZE))
        maximum_samples = 30 * self.SAMPLE_RATE

        def enqueue_utterance() -> None:
            if state["sample_count"] < self.SAMPLE_RATE // 8:
                state["audio"].clear()
                state["sample_count"] = 0
                return
            utterance = np.concatenate(state["audio"]).astype(np.float32, copy=False)
            state["audio"].clear()
            state["sample_count"] = 0
            try:
                self._audio_queue.put_nowait(utterance)
            except queue.Full:
                logger.warning("Dropping utterance because transcription is behind")

        def audio_callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            del frames, time_info
            if status:
                logger.warning("Audio input status: %s", status)
            if not self.is_listening:
                return

            chunk = indata[:, 0].astype(np.float32, copy=True)
            rms = float(np.sqrt(np.mean(np.square(chunk))))
            self.current_audio_level = min(rms * 10.0, 1.0)

            if rms >= self.energy_threshold:
                state["speaking"] = True
                state["silence_blocks"] = 0
                state["audio"].append(chunk)
                state["sample_count"] += len(chunk)
            elif state["speaking"]:
                state["silence_blocks"] += 1
                state["audio"].append(chunk)
                state["sample_count"] += len(chunk)
                if state["silence_blocks"] >= silence_limit:
                    enqueue_utterance()
                    state["speaking"] = False
                    state["silence_blocks"] = 0

            if state["sample_count"] >= maximum_samples:
                enqueue_utterance()
                state["speaking"] = False
                state["silence_blocks"] = 0

        try:
            stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=audio_callback,
                device=self.mic_index,
                blocksize=self.BLOCK_SIZE,
            )
            stream.start()
            if self._stop_event.is_set():
                stream.close()
                return
        except Exception:
            self._stop_event.set()
            with self._state_lock:
                self.is_listening = False
            raise

        with self._state_lock:
            self.stream = stream
            self.is_listening = True
        logger.info("Wake-word listening started")

    def _transcription_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                audio = self._audio_queue.get(timeout=0.25)
            except queue.Empty:
                continue
            if audio is None:
                break
            try:
                text = self._transcribe(audio)
                before, separator, after = text.partition(self.wake_word)
                del before
                if separator:
                    prompt = after.strip(" ,.!?")
                    if prompt and self.on_wake_word_callback:
                        self.on_wake_word_callback(prompt)
            except Exception:
                logger.exception("Speech transcription failed")

    def _transcribe(self, audio: Any) -> str:
        whisper = self._ensure_whisper()
        segments, _ = whisper.transcribe(
            audio, language="en", vad_filter=True, beam_size=1
        )
        return " ".join(segment.text for segment in segments).strip().lower()

    def stop_listening(self) -> None:
        with self._state_lock:
            self.is_listening = False
            stream = self.stream
            self.stream = None
        self._stop_event.set()
        with suppress(queue.Full):
            self._audio_queue.put_nowait(None)
        if stream:
            try:
                stream.stop()
            finally:
                stream.close()
        worker = self._transcription_thread
        if worker and worker is not threading.current_thread():
            worker.join(timeout=1.0)
        self.current_audio_level = 0.0
        logger.info("Wake-word listening stopped")

    def shutdown(self) -> None:
        self.stop_listening()
        self.stop_speaking()
