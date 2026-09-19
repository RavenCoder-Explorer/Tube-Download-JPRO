@echo off
title Tube Download JPRO
cd /d "%~dp0"

echo ===================================================
echo       Launching Tube Download JPRO
echo ===================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Setting up virtual environment...
    python -m venv .venv
    echo [INFO] Installing required dependencies...
    .\.venv\Scripts\pip install -r requirements.txt
)

echo [INFO] Starting application...
start "" ".\.venv\Scripts\pythonw.exe" main.py
if %errorlevel% neq 0 (
    echo [WARNING] pythonw failed, launching with python.exe...
    .\.venv\Scripts\python.exe main.py
)
