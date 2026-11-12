$env:FLOW_SYSTEM_DIR = $PSScriptRoot
$env:SISTEMA_CRIATIVOS_DIR = $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PATH = "$PSScriptRoot;$PSScriptRoot\.venv\Scripts;$PSScriptRoot\.local-bin;$HOME\.local\bin;$env:PATH"
$env:PYTHONPATH = "$PSScriptRoot\scripts;$env:PYTHONPATH"
$flowWhisperPath = Join-Path $PSScriptRoot '.local-bin\whisper-path.txt'
if (Test-Path -LiteralPath $flowWhisperPath) {
    $env:PATH = "$(Get-Content -LiteralPath $flowWhisperPath -Raw);$env:PATH"
}
if (-not $env:FLOW_LOCK) { $env:FLOW_LOCK = Join-Path $PSScriptRoot '.flow_lane.lock' }
if (-not $env:FFMPEG) {
    $flowFFmpeg = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
    if ($flowFFmpeg) { $env:FFMPEG = $flowFFmpeg.Source }
}
if (-not $env:WHISPER_MODEL) { $env:WHISPER_MODEL = Join-Path $PSScriptRoot '.local-cache\whisper\ggml-small.bin' }
if (-not $env:RVM_DIR) { $env:RVM_DIR = Join-Path $PSScriptRoot '.local-cache\rvm' }
