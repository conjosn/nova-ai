$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
& $Python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

$DataDir = if ($env:NOVA_DATA_DIR) { $env:NOVA_DATA_DIR } else { Join-Path $HOME ".nova" }
$VoiceDir = Join-Path $DataDir "voices"
New-Item -ItemType Directory -Force -Path $VoiceDir | Out-Null

$BaseUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium"
$ModelPath = Join-Path $VoiceDir "en_US-lessac-medium.onnx"
if (-not (Test-Path $ModelPath)) {
    Write-Host "Downloading Piper voice..."
    Invoke-WebRequest "$BaseUrl/en_US-lessac-medium.onnx" -OutFile $ModelPath
    Invoke-WebRequest "$BaseUrl/en_US-lessac-medium.onnx.json" -OutFile "$ModelPath.json"
}

Write-Host "Nova is installed. Make sure Ollama is running, then use:"
Write-Host "  .\.venv\Scripts\python.exe launch_nova.py"
