@echo off
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python "%~dp0simlab.py" %*
) else (
    "%~dp0SimLabAI.exe" "%~dp0simlab.py" %*
)
