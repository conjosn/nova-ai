# Nova — Neural Omni-Versatile Assistant

Nova is a private, local-first desktop command assistant built around Ollama. The
v2 command center combines voice, text, system telemetry, deterministic local
skills, document knowledge, persistent memory, agent profiles, and proactive
reminders without silently routing prompts to a cloud model.

## What works

- Text chat against installed local Ollama models
- Automatic routing between installed general and coding models
- "Hey Nova" voice capture or optional open conversation without a wake word
- Animated command-center HUD with live CPU, RAM, storage, NVIDIA GPU, and node health
- One shared conversation across voice and text with serialized request handling
- General, Analyst, Engineer, and Operator agent profiles
- Smart, Controlled, and Chat execution modes
- Allowlisted local skills for status, models, time, reminders, and session control
- Local RAG ingestion for TXT, Markdown, PDF, Word, JSON, CSV, and source files
- Persistent spoken reminders with an on-device proactive pulse
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

To speak without saying "Hey Nova," open **Settings → Conversation mode** and
select **Open conversation (no wake word)**. Nova ignores microphone input while
its own voice is playing, then resumes listening automatically.
The adjacent opt-in setting can open the voice channel automatically when Nova
starts; it remains off by default so launching the app never activates a microphone
without the operator choosing that behavior.

## Command center

The default screen is a three-panel command center:

- **Neural Core** — animated voice state, microphone level, agent profile, and
  execution-mode controls
- **Command Stream** — one persistent session shared by typed and spoken prompts
- **Telemetry** — live system health, GPU status, quick directives, and local
  knowledge ingestion

Execution modes deliberately separate capability from authority:

- **Smart** checks deterministic local skills first, then uses the best installed
  Ollama model when no skill matches.
- **Controlled** runs only allowlisted local skills; unmatched requests never reach
  a model or operating-system command.
- **Chat** bypasses local skills and speaks directly with the selected local model.

Useful local commands:

```text
/help
/status
/models
/time
/reminders
remind me in 10 minutes to check the oven
/clear
```

Use **Ingest Knowledge** to index local documents in ChromaDB. Retrieved chunks are
identified by filename in the private context passed to Ollama. PDF and DOCX parsing
also happen locally.

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
- `core/assistant_session.py` — shared context, skill routing, profiles, and memory
- `core/system_monitor.py` — local CPU/RAM/disk/NVIDIA telemetry
- `core/workspace.py` — document parsing, chunking, and local RAG ingestion
- `core/reminders.py` — persistent proactive reminder queue
- `core/voice_engine.py` — wake-word/open-conversation capture and faster-whisper transcription
- `core/tts_engine.py` — interruptible Piper playback
- `core/persistent_memory.py` — offline retrieval memory
- `core/data_importer.py` — ChatGPT and Claude export parsing
- `gui/` — CustomTkinter voice, text, model, and settings views
- `gui/command_center.py` — unified voice/text/telemetry command surface
- `gui/hud.py` — animated, code-native HUD components

## Open-source design influences

Nova's v2 architecture adapts public product patterns from Open WebUI, Khoj,
AnythingLLM, Leon, OpenVoiceOS, and Open Interpreter. No source code or branded
assets were copied. See [`docs/OPEN_SOURCE_FEATURE_MAP.md`](docs/OPEN_SOURCE_FEATURE_MAP.md)
for the feature-by-feature map and safety boundaries.

## About "self-improvement"

The optional background refinement job generates deduplicated instruction variants
for a future training dataset. It does **not** pretend that saving model-written text
back into memory is training. Automatic code mutation is intentionally not enabled;
that needs tests, review gates, and rollback before it should touch a live assistant.
