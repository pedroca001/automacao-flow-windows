@echo off
setlocal
cd /d "%~dp0"
call "%~dp0env.cmd"
python retomada-macro\noturno.py relatorio %*
set "FLOW_EXIT=%ERRORLEVEL%"
pause
exit /b %FLOW_EXIT%
