#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

VOICE_DIR="${NOVA_DATA_DIR:-$HOME/.nova}/voices"
mkdir -p "$VOICE_DIR"
BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium"

if [[ ! -f "$VOICE_DIR/en_US-lessac-medium.onnx" ]]; then
    python - "$BASE_URL" "$VOICE_DIR" <<'PY'
from pathlib import Path
from urllib.request import urlretrieve
import sys

base_url, output_dir = sys.argv[1], Path(sys.argv[2])
for filename in ("en_US-lessac-medium.onnx", "en_US-lessac-medium.onnx.json"):
    destination = output_dir / filename
    print(f"Downloading {filename}...")
    urlretrieve(f"{base_url}/{filename}", destination)
PY
fi

echo "Nova is installed. Make sure Ollama is running, then use:"
echo "  source .venv/bin/activate && python launch_nova.py"
