@echo off
setlocal
cd /d "%~dp0"
call "%~dp0env.cmd"
python scripts\flow_integrado.py %*
set "FLOW_EXIT=%ERRORLEVEL%"
exit /b %FLOW_EXIT%
