"""Interruptible Piper text-to-speech playback."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import threading
from collections.abc import Callable, Iterable, Iterator
from contextlib import suppress
from pathlib import Path
from typing import Any

from utils.logger import NovaLogger
from utils.paths import VOICE_DIR

logger = NovaLogger()


class PiperTTSEngine:
    def __init__(
        self,
        model_path: str | None = None,
        output_device: int | None = None,
    ) -> None:
        self.model_path = str(
            Path(model_path).expanduser()
            if model_path
            else VOICE_DIR / "en_US-lessac-medium.onnx"
        )
        self.output_device = output_device
        self.is_speaking = False
        self._stop_event = threading.Event()
        self._state_lock = threading.RLock()
        self._worker: threading.Thread | None = None
        self._current_stream: Any | None = None
        self._current_process: subprocess.Popen[bytes] | None = None

    def set_output_device(self, device_index: int | None) -> None:
        self.output_device = device_index

    @staticmethod
    def _sentence_chunks(text: str) -> Iterator[str]:
        for chunk in re.split(r"(?<=[.!?;:])\s+", text.strip()):
            if chunk:
                yield chunk

    @classmethod
    def _normalize_source(
        cls,
        source: str | Iterable[str] | Callable[[], str | Iterable[str]],
    ) -> Iterator[str]:
        value = source() if callable(source) else source
        if isinstance(value, str):
            yield from cls._sentence_chunks(value)
            return

        buffer = ""
        for piece in value:
            buffer += str(piece)
            if len(buffer) >= 80 or re.search(r"[.!?;:]\s*$", buffer):
                yield buffer.strip()
                buffer = ""
        if buffer.strip():
            yield buffer.strip()

    def speak_streaming(
        self,
        source: str | Iterable[str] | Callable[[], str | Iterable[str]],
    ) -> threading.Thread:
        """Speak text or streamed chunks on a worker thread.

        Starting a new utterance interrupts the previous one. This accepts plain
        strings as well as the callable source used by the original implementation.
        """

        self.stop(wait=True)
        stop_event = threading.Event()
        self._stop_event = stop_event

        def worker() -> None:
            self.is_speaking = True
            try:
                for chunk in self._normalize_source(source):
                    if stop_event.is_set():
                        break
                    self._play_chunk(chunk, stop_event)
            except Exception as exc:
                logger.error("TTS error: %s", exc)
            finally:
                self.is_speaking = False
                with self._state_lock:
                    self._current_stream = None
                    self._current_process = None

        self._worker = threading.Thread(
            target=worker, name="nova-tts", daemon=True
        )
        self._worker.start()
        return self._worker

    def _sample_rate(self) -> int:
        config_path = Path(f"{self.model_path}.json")
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            return int(config.get("audio", {}).get("sample_rate", 22050))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 22050

    def _play_chunk(self, text: str, stop_event: threading.Event) -> None:
        if not text or stop_event.is_set():
            return

        executable = shutil.which("piper")
        if not executable:
            raise RuntimeError("Piper is not installed or is not on PATH")
        if not Path(self.model_path).is_file():
            raise FileNotFoundError(
                f"Piper voice model not found: {self.model_path}"
            )

        process = subprocess.Popen(
            [executable, "--model", self.model_path, "--output-raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        with self._state_lock:
            self._current_process = process
        stdout, stderr = process.communicate(input=text.encode("utf-8"))
        with self._state_lock:
            self._current_process = None

        if process.returncode != 0 and not stop_event.is_set():
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(detail or f"Piper exited with code {process.returncode}")
        if not stdout or stop_event.is_set():
            return

        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("Audio playback dependencies are not installed") from exc

        audio = np.frombuffer(stdout, dtype=np.int16)
        position = 0

        def audio_callback(outdata, frames, time_info, status) -> None:
            nonlocal position
            del time_info
            if status:
                logger.warning("Audio output status: %s", status)
            outdata.fill(0)
            if stop_event.is_set():
                raise sd.CallbackAbort

            frame_count = min(frames, len(audio) - position)
            if frame_count > 0:
                outdata[:frame_count, 0] = audio[position : position + frame_count]
                position += frame_count
            if position >= len(audio):
                raise sd.CallbackStop

        stream = sd.OutputStream(
            samplerate=self._sample_rate(),
            channels=1,
            dtype="int16",
            device=self.output_device,
            callback=audio_callback,
            blocksize=0,
        )
        with self._state_lock:
            self._current_stream = stream
        try:
            stream.start()
            while stream.active and not stop_event.wait(0.05):
                continue
        finally:
            try:
                stream.abort() if stop_event.is_set() else stream.stop()
            finally:
                stream.close()
                with self._state_lock:
                    self._current_stream = None

    def stop(self, wait: bool = False) -> None:
        self._stop_event.set()
        with self._state_lock:
            process = self._current_process
            stream = self._current_stream
        if process and process.poll() is None:
            with suppress(OSError):
                process.terminate()
        if stream:
            with suppress(Exception):
                stream.abort()
        worker = self._worker
        if (
            wait
            and worker
            and worker.is_alive()
            and worker is not threading.current_thread()
        ):
            worker.join(timeout=1.0)
        self.is_speaking = False
