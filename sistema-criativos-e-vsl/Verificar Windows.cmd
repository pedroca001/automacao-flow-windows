@echo off
setlocal
cd /d "%~dp0"
call "%~dp0env.cmd"
python scripts\windows_launcher.py verificar
set "FLOW_EXIT=%ERRORLEVEL%"
pause
exit /b %FLOW_EXIT%
