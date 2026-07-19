# Nova — Neural Omni-Versatile Assistant

Nova is a private, local-first desktop assistant built around Ollama. It supports
text chat, wake-word voice input, interruptible Piper speech, local model routing,
persistent retrieval memory, and conversation-export imports.

## What works

- Text chat against installed local Ollama models
- Automatic routing between installed general and coding models
- "Hey Nova" voice capture with non-blocking transcription
- GPU-first faster-whisper with automatic CPU fallback
- Interruptible Piper TTS and selectable audio devices
- Offline ChromaDB memory with deterministic, no-download embeddings
- ChatGPT and Claude conversation JSON imports
- Opt-in instruction-dataset refinement (disabled by default)

Nova never selects Ollama cloud-tagged models automatically. Ollama itself manages
GPU placement for chat models; voice transcription selects CUDA when available.

## Requirements

- Python 3.10–3.12
- [Ollama](https://ollama.com/download), running locally
- At least one local model, for example `ollama pull gemma2:2b`
- A working microphone/speaker for voice mode
- NVIDIA CUDA runtime libraries supported by faster-whisper for GPU transcription

## Windows / Windows Server

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install_and_run.ps1
.\.venv\Scripts\python.exe launch_nova.py
```

## Linux

```bash
chmod +x install_and_run.sh
./install_and_run.sh
source .venv/bin/activate
python launch_nova.py
```

The installer downloads the default Piper voice. It does not install Ollama or
pull a language model for you.

## Configuration and data

Runtime data is stored in `~/.nova` by default:

- `config.json` — selected model and audio settings
- `memory/` — ChromaDB retrieval memory
- `voices/` — Piper voice models

Set `NOVA_DATA_DIR` to move all runtime data. Set `NOVA_WHISPER_DEVICE` to `cpu`
or `cuda` to override automatic transcription-device selection.

## Hardware validation

Run the interactive diagnostic on the computer that will actually run Nova:

```powershell
.\.venv\Scripts\python.exe diagnose_nova.py --output hardware-report.json
```

It performs a live local Ollama response, forces a real faster-whisper CUDA
inference, records and transcribes a spoken microphone phrase, plays a speaker test
tone, and renders a Piper sentence for audible confirmation. It exits with a nonzero
status if any required check fails and can save a shareable JSON report.

Use `--non-interactive` to check Ollama, CUDA, dependencies, and audio-device
discovery without recording or audible playback.

## Architecture

- `core/model_router.py` — installed-model selection and Ollama chat
- `core/voice_engine.py` — wake-word capture and faster-whisper transcription
- `core/tts_engine.py` — interruptible Piper playback
- `core/persistent_memory.py` — offline retrieval memory
- `core/data_importer.py` — ChatGPT and Claude export parsing
- `gui/` — CustomTkinter voice, text, model, and settings views

## About "self-improvement"

The optional background refinement job generates deduplicated instruction variants
for a future training dataset. It does **not** pretend that saving model-written text
back into memory is training. Automatic code mutation is intentionally not enabled;
that needs tests, review gates, and rollback before it should touch a live assistant.
