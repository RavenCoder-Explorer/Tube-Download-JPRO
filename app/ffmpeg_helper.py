import os
import sys
import shutil
import zipfile
import threading
from pathlib import Path
from typing import Optional, Callable
import requests
from app.config import config

# Base directory resolution supporting PyInstaller frozen mode
def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent

APP_ROOT = get_base_dir()
LOCAL_BIN = APP_ROOT / "bin"
FFMPEG_EXE_NAME = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
FFPROBE_EXE_NAME = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"

# High-reliability direct download for Windows static ffmpeg
FFMPEG_WIN64_ZIP_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"


def get_ffmpeg_path() -> Optional[str]:
    """Returns the path to the ffmpeg executable if found, else None."""
    # 1. Custom configured path
    custom = config.get("custom_ffmpeg_path")
    if custom and os.path.exists(custom):
        return custom

    # 2. Candidate bin locations
    candidates = [
        LOCAL_BIN / FFMPEG_EXE_NAME,
        Path.cwd() / "bin" / FFMPEG_EXE_NAME,
        Path(__file__).resolve().parent.parent / "bin" / FFMPEG_EXE_NAME,
    ]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend([
            exe_dir / "bin" / FFMPEG_EXE_NAME,
            exe_dir / "_internal" / "bin" / FFMPEG_EXE_NAME,
            exe_dir / FFMPEG_EXE_NAME,
        ])

    for c in candidates:
        if c.exists():
            return str(c)

    # 3. System PATH
    system_path = shutil.which("ffmpeg")
    if system_path:
        return system_path

    # 4. Common Windows installation locations
    common_locations = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
        Path("C:/Program Files/ffmpeg/bin"),
        Path("C:/ffmpeg/bin"),
    ]
    for loc in common_locations:
        candidate = loc / FFMPEG_EXE_NAME
        if candidate.exists():
            return str(candidate)
        # Search winget subdirectories if existing
        if loc.exists() and "WinGet" in str(loc):
            found = list(loc.glob(f"**/{FFMPEG_EXE_NAME}"))
            if found:
                return str(found[0])

    return None


def ensure_ffmpeg_in_path() -> Optional[str]:
    """Ensures the directory containing ffmpeg and ffprobe is prepended to os.environ['PATH']."""
    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path and os.path.exists(ffmpeg_path):
        ffmpeg_dir = str(Path(ffmpeg_path).resolve().parent)
        current_path = os.environ.get("PATH", "")
        paths = current_path.split(os.pathsep)
        if ffmpeg_dir not in paths:
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + current_path
    return ffmpeg_path


# Automatically ensure FFmpeg is in PATH on module load
ensure_ffmpeg_in_path()


def is_ffmpeg_available() -> bool:
    """Checks whether FFmpeg is available on the system or in the app's bin."""
    return get_ffmpeg_path() is not None


def download_and_setup_ffmpeg(
    progress_callback: Optional[Callable[[float, str], None]] = None,
    completion_callback: Optional[Callable[[bool, str], None]] = None
) -> None:
    """
    Downloads static FFmpeg binary in a background thread and extracts it to the local bin/ folder.
    """
    def _worker():
        try:
            LOCAL_BIN.mkdir(parents=True, exist_ok=True)
            temp_zip = LOCAL_BIN / "ffmpeg_temp.zip"

            if progress_callback:
                progress_callback(0.05, "Connecting to FFmpeg repository...")

            headers = {"User-Agent": "TubeDownloadJPRO/1.0"}
            response = requests.get(FFMPEG_WIN64_ZIP_URL, stream=True, headers=headers, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB

            with open(temp_zip, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and progress_callback:
                        percent = min(0.90, 0.05 + (downloaded / total_size) * 0.85)
                        mb_done = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        progress_callback(percent, f"Downloading FFmpeg: {mb_done:.1f} MB / {mb_total:.1f} MB")

            if progress_callback:
                progress_callback(0.92, "Extracting FFmpeg binaries...")

            # Extract only ffmpeg.exe and ffprobe.exe
            with zipfile.ZipFile(temp_zip, "r") as zf:
                for member in zf.namelist():
                    filename = os.path.basename(member)
                    if filename.lower() in [FFMPEG_EXE_NAME.lower(), FFPROBE_EXE_NAME.lower()]:
                        with zf.open(member) as source:
                            target_file = LOCAL_BIN / filename
                            with open(target_file, "wb") as target:
                                shutil.copyfileobj(source, target)

            # Cleanup temp zip safely
            try:
                if temp_zip.exists():
                    temp_zip.unlink()
            except Exception as clean_err:
                print(f"Warning cleaning temp zip: {clean_err}")

            local_ffmpeg = LOCAL_BIN / FFMPEG_EXE_NAME
            if local_ffmpeg.exists():
                if progress_callback:
                    progress_callback(1.0, "FFmpeg installed successfully!")
                if completion_callback:
                    completion_callback(True, str(local_ffmpeg))
            else:
                raise RuntimeError("Extracted archive did not contain ffmpeg executable.")

        except Exception as e:
            if completion_callback:
                completion_callback(False, str(e))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
