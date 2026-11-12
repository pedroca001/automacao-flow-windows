@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Instalar Windows.ps1" %*
set "FLOW_EXIT=%ERRORLEVEL%"
pause
exit /b %FLOW_EXIT%
