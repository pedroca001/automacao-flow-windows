param([switch]$SemWhisper, [switch]$Rvm)
$ErrorActionPreference = 'Stop'
$flowSystem = Join-Path $PSScriptRoot 'sistema-criativos-e-vsl'
$flowPython = Join-Path $flowSystem '.venv\Scripts\python.exe'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Instale uv (https://docs.astral.sh/uv/getting-started/installation/) e execute novamente.'
}
if (-not (Test-Path -LiteralPath $flowPython)) {
    & uv venv (Join-Path $flowSystem '.venv') --python 3.11
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o ambiente Python.' }
}
& uv pip install --python $flowPython -r (Join-Path $flowSystem 'requirements-windows.txt')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependencias.' }
. (Join-Path $flowSystem 'env.ps1')
foreach ($flowTool in @('ffmpeg', 'ffprobe')) {
    if (-not (Get-Command $flowTool -ErrorAction SilentlyContinue)) {
        throw "Instale FFmpeg com libass e coloque no PATH. Ferramenta ausente: $flowTool"
    }
}
if (-not (Get-Command browser-harness -ErrorAction SilentlyContinue)) {
    & uv tool install --python 3.12 browser-harness
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar browser-harness.' }
}
$flowInstallArgs = @((Join-Path $flowSystem 'scripts\install_windows.py'))
if ($SemWhisper) { $flowInstallArgs += '--sem-whisper' }
if ($Rvm) { $flowInstallArgs += '--rvm' }
& $flowPython @flowInstallArgs
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as ferramentas locais.' }
. (Join-Path $flowSystem 'env.ps1')
& $flowPython (Join-Path $flowSystem 'scripts\windows_launcher.py') verificar
if ($LASTEXITCODE -ne 0 -and -not $SemWhisper) { throw 'Verifique as pendencias acima.' }
