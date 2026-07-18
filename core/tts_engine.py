import subprocess
import threading
import numpy as np
import sounddevice as sd
import re
import os
from utils.logger import NovaLogger

logger = NovaLogger()

class PiperTTSEngine:
    def __init__(self, model_path: str = None):
        self.model_path = model_path or os.path.expanduser("~/.local/share/piper-tts/en_US-lessac-medium.onnx")
        self.is_speaking = False
        self.stop_requested = False
        self.current_stream = None

    def speak_streaming(self, text_getter):
        def worker():
            self.is_speaking = True
            self.stop_requested = False
            buffer = ""
            for chunk in text_getter():
                if self.stop_requested: break
                buffer += chunk
                if len(buffer) > 35 or re.search(r'[.!?,;:]\s*$', buffer):
                    self._stream_play(buffer.strip())
                    buffer = ""
            if buffer.strip() and not self.stop_requested:
                self._stream_play(buffer.strip())
            self.is_speaking = False
        threading.Thread(target=worker, daemon=True).start()

    def _stream_play(self, text):
        if not text or self.stop_requested: return
        try:
            cmd = ["piper", "--model", self.model_path, "--output-raw"]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            stdout, _ = proc.communicate(input=text.encode())
            if stdout and not self.stop_requested:
                audio = np.frombuffer(stdout, dtype=np.int16)
                stream = sd.OutputStream(samplerate=22050, channels=1, dtype='int16')
                stream.start()
                self.current_stream = stream
                stream.write(audio)
                stream.stop()
                stream.close()
                self.current_stream = None
        except Exception as e:
            logger.error(f"TTS error: {e}")

    def stop(self):
        self.stop_requested = True
        if self.current_stream:
            try:
                self.current_stream.stop()
                self.current_stream.close()
            except: pass
        self.is_speaking = False