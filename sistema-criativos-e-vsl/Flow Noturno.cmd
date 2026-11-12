@echo off
setlocal
cd /d "%~dp0"
call "%~dp0env.cmd"
python retomada-macro\noturno.py iniciar %*
set "FLOW_EXIT=%ERRORLEVEL%"
pause
exit /b %FLOW_EXIT%
