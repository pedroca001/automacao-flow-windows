@echo off
setlocal
call "%~dp0env.cmd"
"%~dp0.venv\Scripts\python.exe" -u "%~dp0automacao-personagens\macro_personagens.py" %*
exit /b %ERRORLEVEL%
