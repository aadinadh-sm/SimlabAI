@echo off
title SIMLAB AI - Your Offline Simulation Lab Copilot
cd /d "%~dp0"
echo Starting SIMLAB AI Desktop Copilot...
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python SimLabAI.py
) else if exist "SimLabAI.exe" (
    start "" "SimLabAI.exe"
) else (
    echo [ERROR] Neither Python nor SimLabAI.exe was found.
    pause
)
