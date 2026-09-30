@echo off
title SIMLAB AI - Offline Simulation Lab Copilot
echo ========================================================
echo  SIMLAB AI - Your Offline Simulation Lab Copilot
echo  Authoritative Manual: 23EEP20B Simulation Lab Manual
echo  Mode: 100%% Offline · Portable USB Run
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/3] Verifying SQLite Knowledge Base...
if not exist "knowledge\manual_db.sqlite" (
    echo [*] Generating SQLite FTS5 database from manual...
    python scripts\ingest_manual.py
) else (
    echo [OK] Manual SQLite database ready ^(14 experiments indexed^).
)

echo [2/3] Verifying Domain-Adaptation Knowledge ^& Index...
if not exist "knowledge\domain_index.sqlite" (
    echo [*] Building domain knowledge, canonical circuits, and FTS5 index...
    python simlab.py train-data
) else (
    echo [OK] Domain-Adaptation index ready ^(14 experiments, 22 circuits, 140 viva Q^&As^).
)

echo.
echo [3/3] Launching SIMLAB AI Desktop Window...
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python SimLabAI.py
) else if exist "SimLabAI.exe" (
    echo [*] Using portable bundled runtime ^(SimLabAI.exe^)...
    "SimLabAI.exe"
) else (
    echo [ERROR] Python is not installed and SimLabAI.exe is missing.
    pause
)
