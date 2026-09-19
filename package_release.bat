@echo off
title Package Tube Download JPRO Release ZIP
cd /d "%~dp0"

echo =========================================================
echo   Packaging Tube Download JPRO into Distributable ZIP
echo =========================================================
echo.

if not exist "dist\TubeDownloadJPRO\TubeDownloadJPRO.exe" (
    echo [ERROR] dist\TubeDownloadJPRO\TubeDownloadJPRO.exe not found!
    echo Please run build_exe.bat first.
    pause
    exit /b 1
)

echo [INFO] Creating dist\TubeDownloadJPRO.zip...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import shutil; shutil.make_archive('dist/TubeDownloadJPRO', 'zip', 'dist', 'TubeDownloadJPRO')"
) else (
    python -c "import shutil; shutil.make_archive('dist/TubeDownloadJPRO', 'zip', 'dist', 'TubeDownloadJPRO')"
)

if %errorlevel% equ 0 (
    echo.
    echo =========================================================
    echo [SUCCESS] Package created successfully!
    echo File: dist\TubeDownloadJPRO.zip
    echo This is the file you give to your customers.
    echo =========================================================
) else (
    echo [ERROR] Failed to create ZIP file.
)

pause
