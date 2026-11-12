@echo off
cd /d "%~dp0"
call env.cmd
start "Gravador de movimentos Flow" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0automacao-personagens\gravar_movimentos.py" %*
