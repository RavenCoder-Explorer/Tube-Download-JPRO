import os
import json
from pathlib import Path
from typing import Dict, Any, List

DEFAULT_CONFIG_DIR = Path(os.path.expanduser("~")) / ".tube_download_jpro"
DEFAULT_DOWNLOAD_DIR = Path(os.path.expanduser("~")) / "Downloads" / "TubeDownloadJPRO"
CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
HISTORY_FILE = DEFAULT_CONFIG_DIR / "history.json"


class ConfigManager:
    """Manages application settings and download history."""

    def __init__(self):
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.settings: Dict[str, Any] = self._load_settings()
        self.history: List[Dict[str, Any]] = self._load_history()

    def _load_settings(self) -> Dict[str, Any]:
        default_settings = {
            "download_dir": str(DEFAULT_DOWNLOAD_DIR),
            "theme": "Dark",  # "Dark", "Light", "System"
            "color_theme": "blue",
            "auto_paste": True,
            "max_concurrent": 3,
            "preferred_video_res": "720p",
            "preferred_audio_format": "mp3",
            "preferred_audio_bitrate": "320k",
            "preferred_mode": "video",  # "video" or "audio"
            "custom_ffmpeg_path": "",
            "naming_template": "Title + ID (Default)",
            "skip_existing_files": True,
            "organize_subfolders": "None",
            "speed_limit": "Unlimited",
            "post_batch_action": "None",
            "clipboard_watcher": True,
            "subtitles_mode": "None",
            "auto_update_engine": True,
            "completion_sound": True,
            "is_pro": False,
            "license_key": "",
            "license_signature": "",
            "license_activated_at": "",
            "license_email": "",
            "store_url": "https://lemonsqueezy.com"
        }
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_settings.update(data)
            except Exception as e:
                print(f"Error loading config: {e}")
        return default_settings

    def save_settings(self) -> None:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self.save_settings()

    @property
    def download_dir(self) -> str:
        d = self.settings.get("download_dir", str(DEFAULT_DOWNLOAD_DIR))
        os.makedirs(d, exist_ok=True)
        return d

    @download_dir.setter
    def download_dir(self, path: str) -> None:
        self.set("download_dir", path)

    def _load_history(self) -> List[Dict[str, Any]]:
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading history: {e}")
        return []

    def save_history(self) -> None:
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history[:150], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving history: {e}")

    def add_history(self, item: Dict[str, Any]) -> None:
        # Prepend so newest is first
        self.history.insert(0, item)
        self.save_history()

    def clear_history(self) -> None:
        self.history = []
        self.save_history()

    def remove_history_item(self, item_id: str) -> None:
        self.history = [h for h in self.history if h.get("id") != item_id]
        self.save_history()


# Global instance
config = ConfigManager()
