@echo off
chcp 65001 >nul
set "FLOW_SYSTEM_DIR=%~dp0"
set "SISTEMA_CRIATIVOS_DIR=%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"
set "PATH=%~dp0;%~dp0.venv\Scripts;%~dp0.local-bin;%USERPROFILE%\.local\bin;%PATH%"
set "PYTHONPATH=%~dp0scripts;%PYTHONPATH%"
if exist "%~dp0.local-bin\whisper-path.txt" set /p "FLOW_WHISPER_BIN=" < "%~dp0.local-bin\whisper-path.txt"
if defined FLOW_WHISPER_BIN set "PATH=%FLOW_WHISPER_BIN%;%PATH%"
if not defined FLOW_LOCK set "FLOW_LOCK=%~dp0.flow_lane.lock"
if not defined WHISPER_MODEL set "WHISPER_MODEL=%~dp0.local-cache\whisper\ggml-small.bin"
if not defined RVM_DIR set "RVM_DIR=%~dp0.local-cache\rvm"
