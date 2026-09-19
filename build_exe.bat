@echo off
title Building Tube Download JPRO Standalone Executable
cd /d "%~dp0"

echo ===================================================
echo   Building Tube Download JPRO Executable with Icon
echo ===================================================
echo.

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo [INFO] Installing build dependencies...
    .\.venv\Scripts\pip install -r requirements.txt
)

echo [INFO] Compiling application with PyInstaller and embedding icon...
.\.venv\Scripts\pyinstaller.exe --noconsole --noconfirm --name="TubeDownloadJPRO" --icon="assets\icon.ico" --collect-all customtkinter --collect-all yt_dlp --clean main.py

echo.
echo ===================================================
if %errorlevel% equ 0 (
    echo [INFO] Copying assets and pre-installed FFmpeg binaries into dist...
    xcopy /E /I /Y "assets" "dist\TubeDownloadJPRO\assets" >nul
    xcopy /E /I /Y "bin" "dist\TubeDownloadJPRO\bin" >nul
    if not exist "dist\TubeDownloadJPRO\_internal\bin" mkdir "dist\TubeDownloadJPRO\_internal\bin"
    xcopy /E /I /Y "bin" "dist\TubeDownloadJPRO\_internal\bin" >nul
    echo [SUCCESS] Build completed successfully!
    echo Executable is located in: dist\TubeDownloadJPRO\TubeDownloadJPRO.exe
) else (
    echo [ERROR] Build encountered errors.
)
echo ===================================================
pause
