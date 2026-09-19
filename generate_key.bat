@echo off
title Tube Download JPRO - 1-Device License Generator
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" tools\license_generator.py
) else (
    python tools\license_generator.py
)
