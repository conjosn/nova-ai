#!/bin/bash
set -e
echo "Installing Nova..."
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p ~/.local/share/piper-tts && cd ~/.local/share/piper-tts
if [ ! -f "en_US-lessac-medium.onnx" ]; then
    wget -q --show-progress https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx || true
    wget -q --show-progress https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json || true
fi
cd - > /dev/null
echo "Run: python launch_nova.py"