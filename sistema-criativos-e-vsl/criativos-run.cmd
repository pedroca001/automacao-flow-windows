@echo off
setlocal
call "%~dp0env.cmd"
if "%~1"=="verificar" goto special
if "%~1"=="driver" goto special
if "%~1"=="download" goto special
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\windows_launcher.py" script %*
exit /b %ERRORLEVEL%
:special
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\windows_launcher.py" %*
exit /b %ERRORLEVEL%
