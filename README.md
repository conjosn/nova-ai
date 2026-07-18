# Nova — Neural Omni-Versatile Assistant

**Nova** is a powerful, fully local, privacy-first personal AI assistant designed to feel like a true Jarvis-style counterpart.

## Features

- Advanced Voice with VAD + Streaming TTS + Interruption
- Reactive Visual Interface
- Hybrid Intelligence (Custom Skills + LangChain Agent)
- Persistent Memory + RAG + Auto Summary
- Background Self-Improvement (Evol-Instruct)
- Data Import from ChatGPT, Claude, Gemini
- Clean, Modular Architecture

## Quick Start

```bash
chmod +x install_and_run.sh
./install_and_run.sh
source .venv/bin/activate
python launch_nova.py
```

## Architecture

- `core/voice_engine.py`: Real-time VAD, Whisper, Piper TTS
- `core/langchain_agent.py`: Agent with memory and self-improvement
- `core/persistent_memory.py`: ChromaDB RAG memory
- `gui/`: CustomTkinter interface

Built for local-first, intelligent personal AI.