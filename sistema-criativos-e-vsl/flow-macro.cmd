@echo off
setlocal
call "%~dp0env.cmd"
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\flow_macro_windows.py" %*
exit /b %ERRORLEVEL%
