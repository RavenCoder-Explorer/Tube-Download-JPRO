import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Enable high-DPI awareness on Windows for ultra-crisp fonts and modern rendering
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

from app.ffmpeg_helper import ensure_ffmpeg_in_path
ensure_ffmpeg_in_path()

from app.ui.main_window import MainWindow


def main():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
