@echo off
setlocal
call "%~dp0env.cmd"
"%~dp0.venv\Scripts\python.exe" "%~dp0automacao-personagens\cli.py" iniciar %*
if errorlevel 1 pause
