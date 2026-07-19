#!/usr/bin/env python3
"""Interactive hardware validation for a Nova installation."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from utils.config import load_config
from utils.paths import VOICE_DIR


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


def choose_test_model(installed: list[str], preferred: str | None) -> str | None:
    """Choose an installed local model without ever selecting a cloud tag."""

    local_models = sorted(model for model in installed if "cloud" not in model.lower())
    if preferred in local_models:
        return preferred
    return local_models[0] if local_models else None


def piper_sample_rate(model_path: Path) -> int:
    try:
        config = json.loads(Path(f"{model_path}.json").read_text(encoding="utf-8"))
        return int(config.get("audio", {}).get("sample_rate", 22050))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return 22050


class NovaDiagnostics:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.config = load_config()
        self.results: list[CheckResult] = []
        self.whisper: Any | None = None
        self.recorded_audio: Any | None = None

    def record(self, name: str, status: str, detail: str) -> None:
        result = CheckResult(name, status, detail)
        self.results.append(result)
        print(f"[{status:<4}] {name}: {detail}")

    @staticmethod
    def confirm(prompt: str) -> bool:
        try:
            return input(f"{prompt} [y/N]: ").strip().lower() in {"y", "yes"}
        except (EOFError, KeyboardInterrupt):
            return False

    def check_environment(self) -> None:
        self.record(
            "Environment",
            "PASS",
            f"Python {platform.python_version()} on {platform.platform()}",
        )
        dependencies = (
            "chromadb",
            "customtkinter",
            "ctranslate2",
            "faster_whisper",
            "numpy",
            "ollama",
            "sounddevice",
        )
        unavailable = []
        for dependency in dependencies:
            try:
                __import__(dependency)
            except Exception as exc:
                unavailable.append(f"{dependency} ({exc})")
        if unavailable:
            self.record("Dependencies", "FAIL", f"Unavailable: {', '.join(unavailable)}")
        else:
            self.record("Dependencies", "PASS", "All runtime packages import")

    def check_ollama(self) -> None:
        try:
            from core.model_router import ModelRouter
            from core.ollama_manager import OllamaManager

            manager = OllamaManager(host=self.config.get("ollama_host"))
            installed = manager.get_installed_models(refresh=True)
            selected = choose_test_model(
                installed, self.args.model or self.config.get("model_name")
            )
            if not selected:
                raise RuntimeError("No installed local model was found")
            router = ModelRouter(default_model=selected, ollama_manager=manager)
            response = router.chat(
                [
                    {
                        "role": "user",
                        "content": "Reply with exactly NOVA_OK and nothing else.",
                    }
                ],
                model=selected,
            )
            if not response.strip():
                raise RuntimeError("Ollama returned an empty response")
            exact = response.strip() == "NOVA_OK"
            detail = f"{selected} replied: {response.strip()[:120]}"
            self.record("Live Ollama", "PASS" if exact else "WARN", detail)
        except Exception as exc:
            self.record("Live Ollama", "FAIL", str(exc))

    def check_cuda_whisper(self) -> None:
        try:
            import ctranslate2
            import numpy as np
            from faster_whisper import WhisperModel

            device_count = ctranslate2.get_cuda_device_count()
            if device_count < 1:
                raise RuntimeError("CTranslate2 found no CUDA devices")
            model_name = self.args.whisper_model or self.config.get(
                "whisper_model", "base"
            )
            print(f"Loading faster-whisper '{model_name}' on CUDA...")
            self.whisper = WhisperModel(
                model_name, device="cuda", compute_type="float16"
            )
            # Force a real inference so missing CUDA/cuDNN libraries cannot hide
            # behind successful model construction.
            segments, _ = self.whisper.transcribe(
                np.zeros(16000, dtype=np.float32),
                language="en",
                beam_size=1,
                vad_filter=False,
            )
            list(segments)
            self.record(
                "CUDA Whisper",
                "PASS",
                f"Inference completed on {device_count} CUDA device(s)",
            )
        except Exception as exc:
            self.whisper = None
            self.record("CUDA Whisper", "FAIL", str(exc))

    def check_audio_devices(self) -> None:
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            inputs = [device for device in devices if device["max_input_channels"] > 0]
            outputs = [device for device in devices if device["max_output_channels"] > 0]
            if not inputs or not outputs:
                raise RuntimeError(
                    f"Found {len(inputs)} input and {len(outputs)} output devices"
                )
            self.record(
                "Audio devices",
                "PASS",
                f"Found {len(inputs)} input and {len(outputs)} output devices",
            )
        except Exception as exc:
            self.record("Audio devices", "FAIL", str(exc))

    def check_microphone(self) -> None:
        if self.args.non_interactive:
            self.record("Microphone", "SKIP", "Requires interactive hardware mode")
            return
        try:
            import numpy as np
            import sounddevice as sd

            seconds = self.args.seconds
            print(
                f'For the next {seconds:g} seconds, say: "Hey Nova, hardware test."'
            )
            self.recorded_audio = sd.rec(
                int(seconds * 16000),
                samplerate=16000,
                channels=1,
                dtype="float32",
                device=self.config.get("mic_index"),
            )
            sd.wait()
            self.recorded_audio = self.recorded_audio[:, 0]
            rms = float(np.sqrt(np.mean(np.square(self.recorded_audio))))
            if rms < 0.002:
                raise RuntimeError(f"Signal was nearly silent (RMS {rms:.5f})")
            self.record("Microphone", "PASS", f"Captured signal at RMS {rms:.5f}")
        except Exception as exc:
            self.recorded_audio = None
            self.record("Microphone", "FAIL", str(exc))

    def check_recorded_transcription(self) -> None:
        if self.args.non_interactive:
            self.record("Mic transcription", "SKIP", "No interactive recording")
            return
        if self.recorded_audio is None:
            self.record("Mic transcription", "SKIP", "Microphone capture failed")
            return
        if self.whisper is None:
            self.record("Mic transcription", "SKIP", "CUDA Whisper failed")
            return
        try:
            segments, _ = self.whisper.transcribe(
                self.recorded_audio,
                language="en",
                beam_size=1,
                vad_filter=True,
            )
            text = " ".join(segment.text for segment in segments).strip()
            if not text:
                raise RuntimeError("Whisper returned no text")
            self.record("Mic transcription", "PASS", text[:200])
        except Exception as exc:
            self.record("Mic transcription", "FAIL", str(exc))

    def check_speaker(self) -> None:
        if self.args.non_interactive:
            self.record("Speaker", "SKIP", "Requires interactive confirmation")
            return
        try:
            import numpy as np
            import sounddevice as sd

            sample_rate = 44100
            timeline = np.arange(sample_rate, dtype=np.float32) / sample_rate
            tone = (0.12 * np.sin(2 * np.pi * 440 * timeline)).astype(np.float32)
            print("Playing a one-second speaker test tone...")
            sd.play(
                tone,
                samplerate=sample_rate,
                device=self.config.get("speaker_index"),
            )
            sd.wait()
            heard = self.confirm("Did you hear the tone?")
            self.record(
                "Speaker",
                "PASS" if heard else "FAIL",
                "User confirmed playback" if heard else "Playback was not confirmed",
            )
        except Exception as exc:
            self.record("Speaker", "FAIL", str(exc))

    def check_piper(self) -> None:
        if self.args.non_interactive:
            self.record("Piper TTS", "SKIP", "Requires interactive confirmation")
            return
        try:
            import numpy as np
            import sounddevice as sd

            executable = shutil.which("piper")
            if not executable:
                raise RuntimeError("The piper executable is not on PATH")
            configured = self.config.get("voice_model")
            model_path = (
                Path(configured).expanduser()
                if configured
                else VOICE_DIR / "en_US-lessac-medium.onnx"
            )
            if not model_path.is_file():
                raise FileNotFoundError(f"Voice model not found: {model_path}")
            process = subprocess.run(
                [executable, "--model", str(model_path), "--output-raw"],
                input=b"Nova speech hardware test successful.",
                capture_output=True,
                check=True,
                timeout=45,
            )
            audio = np.frombuffer(process.stdout, dtype=np.int16)
            if not len(audio):
                raise RuntimeError("Piper produced no audio")
            sd.play(
                audio,
                samplerate=piper_sample_rate(model_path),
                device=self.config.get("speaker_index"),
            )
            sd.wait()
            heard = self.confirm("Did you hear Nova speak?")
            self.record(
                "Piper TTS",
                "PASS" if heard else "FAIL",
                f"Rendered {len(audio)} samples; playback "
                + ("confirmed" if heard else "not confirmed"),
            )
        except Exception as exc:
            self.record("Piper TTS", "FAIL", str(exc))

    def finish(self) -> int:
        failures = sum(result.status == "FAIL" for result in self.results)
        warnings = sum(result.status in {"WARN", "SKIP"} for result in self.results)
        print(f"\nSummary: {len(self.results) - failures - warnings} passed, "
              f"{warnings} warnings/skips, {failures} failed")
        if self.args.output:
            output = Path(self.args.output).expanduser()
            output.write_text(
                json.dumps([asdict(result) for result in self.results], indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Report written to {output}")
        return 1 if failures else 0

    def run(self) -> int:
        print("Nova hardware diagnostics\n")
        self.check_environment()
        self.check_ollama()
        self.check_cuda_whisper()
        self.check_audio_devices()
        self.check_microphone()
        self.check_recorded_transcription()
        self.check_speaker()
        self.check_piper()
        return self.finish()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Nova's local Ollama, CUDA, microphone, speaker, and Piper setup."
    )
    parser.add_argument("--model", help="Installed Ollama model to test")
    parser.add_argument("--whisper-model", help="faster-whisper model to test")
    parser.add_argument(
        "--seconds", type=float, default=4.0, help="Microphone recording duration"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip microphone capture and audible playback",
    )
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be greater than zero")
    return args


if __name__ == "__main__":
    sys.exit(NovaDiagnostics(parse_args()).run())
