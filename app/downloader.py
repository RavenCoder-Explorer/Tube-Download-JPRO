import os
import re
import sys
import time
import uuid
import json
import shutil
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Tuple
import requests
import yt_dlp

from app.config import config
from app.ffmpeg_helper import get_ffmpeg_path, ensure_ffmpeg_in_path
from app.license_manager import verify_runtime_integrity


def parse_time_to_seconds(t_str: str) -> Optional[float]:
    """Parses timestamps like '01:30', '1:05:20', or '45' into seconds."""
    if not t_str or not t_str.strip():
        return None
    parts = t_str.strip().split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except Exception:
        return None
    return None


def check_engine_update() -> Tuple[bool, str, str]:
    """Checks if yt-dlp has a newer release on PyPI. Returns (has_update, current_ver, latest_ver)."""
    current_ver = yt_dlp.version.__version__
    try:
        resp = requests.get("https://pypi.org/pypi/yt-dlp/json", timeout=6).json()
        latest_ver = resp["info"]["version"]

        def _norm(v: str):
            return tuple(int(x) for x in v.replace("-", ".").split(".") if x.isdigit())

        has_update = _norm(latest_ver) > _norm(current_ver)
        return (has_update, current_ver, latest_ver)
    except Exception as e:
        return (False, current_ver, f"Check error: {e}")


def run_engine_update(callback: Optional[Callable[[bool, str], None]] = None) -> None:
    """Updates yt-dlp in a background thread and invokes callback(success, message)."""
    def _worker():
        try:
            import subprocess
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                if callback:
                    callback(True, "Engine successfully updated to latest version!")
            else:
                err = res.stderr.strip() or res.stdout.strip()
                if callback:
                    callback(False, f"Update failed: {err}")
        except Exception as e:
            if callback:
                callback(False, f"Update error: {e}")

    threading.Thread(target=_worker, daemon=True).start()


def execute_system_power_action(action: str) -> None:
    """Executes Sleep or Shutdown on Windows."""
    import subprocess
    if action == "Sleep PC":
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=True)
    elif action == "Shutdown PC":
        subprocess.run(["shutdown", "/s", "/t", "60", "/c", "Tube Download JPRO: Downloads complete. Shutting down in 60s..."], shell=True)


def scrape_channel_clips(channel_url: str, max_results: int = 40) -> List[Dict[str, Any]]:
    """Scrapes clip metadata (title, url, thumbnail, views, duration) from a channel or playlist."""
    ydl_opts: Dict[str, Any] = {
        "extract_flat": "in_playlist",
        "playlistend": max_results,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True
    }
    if shutil.which("node"):
        ydl_opts["js_runtimes"] = {"node": {}}

    clips = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
        entries = info.get("entries", []) if info else []
        for entry in entries:
            if not entry:
                continue
            url = entry.get("url") or entry.get("webpage_url")
            if not url and entry.get("id"):
                url = f"https://www.youtube.com/watch?v={entry['id']}"
            if url:
                thumb = entry.get("thumbnail")
                if not thumb and entry.get("thumbnails"):
                    thumb = entry.get("thumbnails")[-1].get("url", "")
                clips.append({
                    "id": entry.get("id", ""),
                    "title": entry.get("title", "Untitled Video"),
                    "url": url,
                    "thumbnail": thumb or "",
                    "duration": entry.get("duration", 0),
                    "view_count": entry.get("view_count", 0),
                    "channel": entry.get("uploader") or entry.get("channel") or (info.get("title") if info else "")
                })
    return clips


def format_duration(seconds: Optional[int]) -> str:
    """Formats duration in seconds to MM:SS or HH:MM:SS."""
    if not seconds or seconds < 0:
        return "Unknown"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_views(views: Optional[int]) -> str:
    """Formats view count to human readable (e.g. 1.2M)."""
    if not views or views < 0:
        return "Unknown views"
    if views >= 1_000_000_000:
        return f"{views / 1_000_000_000:.1f}B views"
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M views"
    if views >= 1_000:
        return f"{views / 1_000:.1f}K views"
    return f"{views} views"


def format_bytes(bytes_num: Optional[float]) -> str:
    """Formats bytes to KB, MB, or GB."""
    if not bytes_num or bytes_num <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_idx = 0
    val = float(bytes_num)
    while val >= 1024.0 and unit_idx < len(units) - 1:
        val /= 1024.0
        unit_idx += 1
    return f"{val:.1f} {units[unit_idx]}"


def sanitize_filename(name: str) -> str:
    """Removes invalid filesystem characters from filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


_pinterest_session: Optional[requests.Session] = None

def get_pinterest_session() -> requests.Session:
    global _pinterest_session
    if _pinterest_session is None:
        _pinterest_session = requests.Session()
        _pinterest_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        try:
            _pinterest_session.get("https://www.pinterest.com/", timeout=6)
        except Exception:
            pass
    return _pinterest_session


def reset_pinterest_session() -> requests.Session:
    global _pinterest_session
    _pinterest_session = None
    return get_pinterest_session()


def extract_pinterest_pin_data(url: str) -> Dict[str, Any]:
    """Extracts direct video or high-resolution image stream and metadata from any Pinterest Pin or pin.it link."""
    clean_url = resolve_media_url(url)
    s = get_pinterest_session()

    id_match = re.search(r'/(?:pin|idea)/(\d+)', clean_url)
    pin_id = id_match.group(1) if id_match else str(uuid.uuid4())
    canonical_url = f"https://www.pinterest.com/pin/{pin_id}/" if id_match else clean_url

    title = ""
    author = "Pinterest Creator"
    image_url = ""
    video_url = ""

    # Method 1: Query Pinterest PinResource API (highest accuracy for exact titles, master originals, and MP4 videos)
    if id_match:
        for attempt in range(2):
            try:
                api_url = "https://www.pinterest.com/resource/PinResource/get/"
                params = {
                    'data': json.dumps({
                        'options': {
                            'field_set_key': 'unauth_react_main_pin',
                            'id': pin_id
                        }
                    })
                }
                headers = {
                    'X-Pinterest-PWS-Handler': 'www/[username].js',
                    'Referer': f'https://www.pinterest.com/pin/{pin_id}/'
                }
                api_resp = s.get(api_url, params=params, headers=headers, timeout=8)
                if api_resp.status_code == 429 and attempt == 0:
                    s = reset_pinterest_session()
                    continue
                if api_resp.status_code == 200:
                    res_data = api_resp.json().get('resource_response', {}).get('data', {})
                    if res_data:
                        title = res_data.get('title') or res_data.get('grid_title') or res_data.get('closeup_unified_description') or ""
                        author = res_data.get('pinner', {}).get('full_name') or res_data.get('closeup_attribution', {}).get('full_name') or author

                        # Videos
                        videos_obj = res_data.get('videos') or {}
                        v_list = videos_obj.get('video_list', {}) if isinstance(videos_obj, dict) else {}
                        if isinstance(v_list, dict):
                            for q in ['V_720P', 'V_1080P', 'V_EXP7']:
                                if q in v_list and v_list[q].get('url') and v_list[q]['url'].endswith('.mp4'):
                                    video_url = v_list[q]['url']
                                    break
                            if not video_url:
                                for k, v in v_list.items():
                                    if isinstance(v, dict) and v.get('url') and v['url'].endswith('.mp4'):
                                        video_url = v['url']
                                        break

                        # Images
                        img_dict = res_data.get('images', {})
                        if isinstance(img_dict, dict):
                            orig = img_dict.get('orig')
                            if isinstance(orig, dict) and orig.get('url'):
                                image_url = orig['url']
                            if not image_url:
                                h736 = img_dict.get('736x')
                                if isinstance(h736, dict) and h736.get('url'):
                                    image_url = h736['url']
                        if video_url or image_url:
                            break
            except Exception as api_err:
                print(f"PinResource API attempt error: {api_err}")

    # Method 2: Fallback to HTML webpage scraping if API didn't get all media
    if not (video_url or image_url):
        resp = s.get(canonical_url, headers={"Referer": "https://www.pinterest.com/"}, timeout=12)
        if resp.status_code == 200:
            html = resp.text

            # Check JSON-LD metadata
            ld_matches = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
            for ld_text in ld_matches:
                try:
                    data = json.loads(ld_text)
                    if isinstance(data, dict):
                        if not title:
                            title = data.get("headline") or data.get("name") or data.get("articleBody") or ""
                        if not author or author == "Pinterest Creator":
                            auth_obj = data.get("author")
                            if isinstance(auth_obj, dict):
                                author = auth_obj.get("name") or author
                        if not image_url:
                            image_url = data.get("image") or ""
                        if not video_url:
                            video_url = data.get("contentUrl") or ""
                except Exception:
                    pass

            # Check for direct mp4 video links in page
            if not video_url:
                v_matches = re.findall(r'https://v\.pinimg\.com/videos/[^\"]+?\.mp4', html)
                if not v_matches:
                    v_matches = re.findall(r'https://[^\"]+?\.mp4', html)
                if v_matches:
                    video_url = v_matches[0]
                    for vm in v_matches:
                        if "720p" in vm or "1080p" in vm:
                            video_url = vm
                            break

            # Look for original master image if no image found yet
            if not image_url:
                orig_imgs = re.findall(r'https://i\.pinimg\.com/originals/[^\"]+?\.(?:jpg|png|webp|gif)', html)
                if orig_imgs:
                    image_url = orig_imgs[0]
                else:
                    hd_imgs = re.findall(r'https://i\.pinimg\.com/736x/[^\"]+?\.(?:jpg|png|webp|gif)', html)
                    if hd_imgs:
                        image_url = hd_imgs[0]

            if not title:
                t_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                if t_match:
                    title = t_match.group(1).replace(" | Pinterest", "").strip()

    if not title:
        title = f"Pinterest Pin {pin_id}"

    is_video = bool(video_url)
    download_url = video_url if is_video else image_url
    ext = "mp4" if is_video else ("png" if image_url.endswith(".png") else "jpg")

    return {
        "id": pin_id,
        "title": title,
        "uploader": author,
        "video_url": video_url,
        "image_url": image_url,
        "canonical_url": canonical_url,
        "is_video": is_video,
        "download_url": download_url,
        "ext": ext
    }


def resolve_media_url(url: str) -> str:
    """Expands redirect shortlinks (e.g. pin.it, youtu.be) into canonical URLs."""
    clean = url.strip()
    lower = clean.lower()
    if "pin.it/" in lower:
        s = get_pinterest_session()
        try:
            resp = s.head(clean, allow_redirects=True, timeout=8)
            if resp.url and ("pin" in resp.url.lower() or "idea" in resp.url.lower()):
                clean = resp.url
        except Exception:
            try:
                resp = s.get(clean, allow_redirects=True, timeout=8, stream=True)
                if resp.url and ("pin" in resp.url.lower() or "idea" in resp.url.lower()):
                    clean = resp.url
            except Exception:
                pass

    if "pinterest." in clean.lower() or "pin.it" in clean.lower():
        id_match = re.search(r'/(?:pin|idea)/(\d+)', clean)
        if id_match:
            clean = f"https://www.pinterest.com/pin/{id_match.group(1)}/"

    return clean


def detect_platform(url: str) -> str:
    """Detects if URL is YouTube Shorts, YouTube, TikTok, Instagram Reels, Pinterest, or other."""
    lower = url.lower()
    if "youtube.com/shorts/" in lower or "youtu.be/shorts/" in lower:
        return "shorts"
    elif "youtube.com" in lower or "youtu.be" in lower:
        return "youtube"
    elif "tiktok.com" in lower or "douyin.com" in lower:
        return "tiktok"
    elif "instagram.com/reel" in lower or "instagram.com/reels" in lower:
        return "instagram"
    elif "instagram.com" in lower:
        return "instagram"
    elif "pinterest." in lower or "pin.it" in lower:
        return "pinterest"
    return "other"


def get_platform_label(platform: str) -> str:
    """Returns user-facing formatted platform label."""
    mapping = {
        "shorts": "YouTube Shorts",
        "youtube": "YouTube Video",
        "tiktok": "TikTok",
        "instagram": "Instagram Reel",
        "pinterest": "Pinterest",
        "other": "Web Video"
    }
    return mapping.get(platform, "Video")


def extract_supported_urls(text: str) -> List[str]:
    """
    Extracts all supported YouTube, TikTok, Instagram, and Pinterest URLs from any multi-line or paragraph text.
    Deduplicates while preserving order.
    """
    url_pattern = re.compile(r"https?://[^\s\"\'<>]+", re.IGNORECASE)
    raw_urls = url_pattern.findall(text)
    cleaned_urls = []
    seen = set()

    for u in raw_urls:
        # Strip trailing punctuation often copied along with text
        u = u.rstrip(".,;!?)>]\'\"")
        lower = u.lower()
        if (
            "youtube.com" in lower
            or "youtu.be" in lower
            or "tiktok.com" in lower
            or "douyin.com" in lower
            or "instagram.com" in lower
            or "pinterest." in lower
            or "pin.it" in lower
        ):
            if u not in seen:
                seen.add(u)
                cleaned_urls.append(u)

    return cleaned_urls


def expand_channel_shorts(channel_or_playlist_url: str, max_items: int = 50) -> List[str]:
    """
    If a YouTube channel /shorts or playlist link is supplied, extracts individual video URLs.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlist_items": f"1-{max_items}",
    }
    extracted = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_or_playlist_url, download=False)
            if info and "entries" in info:
                for entry in info["entries"]:
                    if not entry:
                        continue
                    v_url = entry.get("url") or entry.get("webpage_url")
                    if not v_url and entry.get("id"):
                        v_url = f"https://www.youtube.com/shorts/{entry['id']}"
                    if v_url and v_url not in extracted:
                        extracted.append(v_url)
    except Exception as e:
        print(f"Error expanding shorts from channel/playlist: {e}")

    return extracted


def scrape_channel_clips(channel_or_playlist_url: str, max_items: int = 40) -> List[Dict[str, Any]]:
    """
    Extracts rich clip items (title, url, thumbnail, duration, views) from a YouTube channel/shorts,
    TikTok profile, or playlist without downloading media payloads, using fast flat extraction.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "playlist_items": f"1-{max_items}",
    }
    if shutil.which("node"):
        ydl_opts["js_runtimes"] = {"node": {}}

    results = []
    seen = set()
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_or_playlist_url, download=False)
            if info and "entries" in info:
                for entry in info["entries"]:
                    if not entry:
                        continue
                    v_url = entry.get("url") or entry.get("webpage_url")
                    vid = entry.get("id") or ""
                    if not v_url and vid:
                        if "/shorts" in channel_or_playlist_url:
                            v_url = f"https://www.youtube.com/shorts/{vid}"
                        else:
                            v_url = f"https://www.youtube.com/watch?v={vid}"

                    if not v_url or v_url in seen:
                        continue
                    seen.add(v_url)

                    dur_val = entry.get("duration") or 0
                    dur_str = format_duration(int(dur_val)) if dur_val else ""
                    views = entry.get("view_count") or 0
                    views_str = format_views(int(views)) if views else ""

                    thumb = entry.get("thumbnail") or ""
                    if not thumb and entry.get("thumbnails"):
                        thumbs = entry.get("thumbnails")
                        if isinstance(thumbs, list) and len(thumbs) > 0:
                            thumb = thumbs[-1].get("url", "")
                    if not thumb and vid:
                        thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                    results.append({
                        "id": vid,
                        "url": v_url,
                        "title": entry.get("title") or "Untitled Video",
                        "uploader": entry.get("uploader") or entry.get("channel") or info.get("title", ""),
                        "duration_str": dur_str,
                        "view_count_str": views_str,
                        "thumbnail_url": thumb,
                        "platform": detect_platform(v_url)
                    })
    except Exception as e:
        print(f"Error scraping channel clips: {e}")

    return results


@dataclass
class VideoInfo:
    url: str
    id: str
    title: str
    uploader: str
    duration: int
    duration_str: str
    view_count: int
    view_count_str: str
    thumbnail_url: str
    platform: str
    available_resolutions: List[str] = field(default_factory=list)
    raw_info: Dict[str, Any] = field(default_factory=dict)


def fetch_video_metadata(url: str) -> VideoInfo:
    """Extracts metadata from YouTube, Shorts, TikTok, Instagram, or Pinterest URL."""
    resolved_url = resolve_media_url(url)
    platform = detect_platform(resolved_url)

    if platform == "pinterest":
        try:
            p_data = extract_pinterest_pin_data(resolved_url)
            is_vid = p_data["is_video"]
            dl_url = p_data["download_url"]
            res_list = ["720p (HD)", "Best Quality"] if is_vid else ["Original Image (HD)"]
            return VideoInfo(
                url=url,
                id=p_data["id"],
                title=p_data["title"],
                uploader=p_data["uploader"],
                duration=0,
                duration_str="Video" if is_vid else "Image",
                view_count=0,
                view_count_str="📌 Pin",
                thumbnail_url=p_data["image_url"],
                platform="pinterest",
                available_resolutions=res_list,
                raw_info={
                    "pinterest_data": p_data,
                    "direct_download_url": dl_url,
                    "is_image": not is_vid,
                    "ext": p_data["ext"],
                    "uploader": p_data["uploader"]
                }
            )
        except Exception as pe:
            print(f"Pinterest custom extractor warning: {pe}, trying yt-dlp...")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }

    if shutil.which("node"):
        ydl_opts["js_runtimes"] = {"node": {}}

    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path:
        ydl_opts["ffmpeg_location"] = ffmpeg_path

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(resolved_url, download=False)
        if not info:
            raise RuntimeError("Could not retrieve video information.")

        # If playlist/entries, grab first entry
        if "entries" in info and info["entries"]:
            info = info["entries"][0]

        title = info.get("title") or info.get("description") or "Pinterest Pin"
        if len(title) > 90:
            title = title[:87] + "..."
        uploader = info.get("uploader") or info.get("creator") or info.get("channel") or info.get("uploader_id") or "Pinterest Creator"
        duration = info.get("duration", 0) or 0
        views = info.get("view_count", 0) or 0
        thumbnail = info.get("thumbnail", "")

        # Find available heights/resolutions
        formats = info.get("formats", [])
        heights = set()
        for f in formats:
            h = f.get("height")
            if h and isinstance(h, int) and h > 0:
                heights.add(h)

        sorted_heights = sorted(list(heights), reverse=True)
        res_list = ["Best Quality"]
        for h in sorted_heights:
            if h >= 2160:
                res_list.append(f"{h}p (4K)")
            elif h >= 1440:
                res_list.append(f"{h}p (2K)")
            elif h >= 1080:
                res_list.append(f"{h}p (Full HD)")
            elif h >= 720:
                res_list.append(f"{h}p (HD)")
            else:
                res_list.append(f"{h}p")

        # Deduplicate while preserving order
        seen = set()
        dedup_res = []
        for r in res_list:
            if r not in seen:
                seen.add(r)
                dedup_res.append(r)

        return VideoInfo(
            url=url,
            id=info.get("id", str(uuid.uuid4())),
            title=title,
            uploader=uploader,
            duration=duration,
            duration_str=format_duration(duration),
            view_count=views,
            view_count_str=format_views(views),
            thumbnail_url=thumbnail,
            platform=platform,
            available_resolutions=dedup_res if len(dedup_res) > 1 else ["Best Quality", "1080p", "720p", "480p"],
            raw_info=info
        )


NAMING_TEMPLATES: Dict[str, str] = {
    "Title + ID (Default)": "%(title)s [%(id)s].%(ext)s",
    "001 - Title": "%(playlist_index|{num:03d})03d - %(title)s.%(ext)s",
    "001 - Title + ID": "%(playlist_index|{num:03d})03d - %(title)s [%(id)s].%(ext)s",
    "001_Title": "%(playlist_index|{num:03d})03d_%(title)s.%(ext)s",
    "Title - 001": "%(title)s - %(playlist_index|{num:03d})03d.%(ext)s",
    "01 - Title": "%(playlist_index|{num:02d})02d - %(title)s.%(ext)s",
    "Title Only": "%(title)s.%(ext)s",
    "Creator - 001 - Title": "%(uploader)s - %(playlist_index|{num:03d})03d - %(title)s.%(ext)s",
    "Creator - Title": "%(uploader)s - %(title)s.%(ext)s",
    "Upload Date - Title": "%(upload_date)s - %(title)s.%(ext)s",
    "[Platform] 001 - Title": "[%(extractor)s] %(playlist_index|{num:03d})03d - %(title)s.%(ext)s",
    "[Platform] Title": "[%(extractor)s] %(title)s.%(ext)s"
}

NAMING_EXAMPLES: Dict[str, str] = {
    "Title + ID (Default)": "Amazing Video [dQw4w9WgXcQ].mp4",
    "001 - Title": "001 - Amazing Video.mp4",
    "001 - Title + ID": "001 - Amazing Video [dQw4w9WgXcQ].mp4",
    "001_Title": "001_Amazing Video.mp4",
    "Title - 001": "Amazing Video - 001.mp4",
    "01 - Title": "01 - Amazing Video.mp4",
    "Title Only": "Amazing Video.mp4",
    "Creator - 001 - Title": "Rick Astley - 001 - Amazing Video.mp4",
    "Creator - Title": "Rick Astley - Amazing Video.mp4",
    "Upload Date - Title": "2026-09-19 - Amazing Video.mp4",
    "[Platform] 001 - Title": "[YouTube] 001 - Amazing Video.mp4",
    "[Platform] Title": "[YouTube] Amazing Video.mp4"
}


@dataclass
class DownloadTask:
    task_id: str
    url: str
    title: str
    thumbnail_url: str
    platform: str
    mode: str  # "video" or "audio"
    resolution: str  # e.g. "1080p", "Best Quality"
    audio_format: str  # "mp3", "m4a", "wav"
    audio_bitrate: str  # "320k", "192k", "128k"
    save_dir: str
    naming_template: str = "Title + ID (Default)"
    order_num: int = 1
    time_range: Optional[Tuple[str, str]] = None  # (start, end)
    subtitles_mode: str = "None"  # "None", "Download .SRT", "Burn into Video"
    speed_limit: str = "Unlimited"  # "Unlimited", "15 MB/s", "10 MB/s", "5 MB/s", "2 MB/s"
    subfolder_rule: str = "None"  # "None", "By Platform", "By Creator", "By Platform & Creator"
    skip_existing: bool = True

    # State
    status: str = "queued"  # "queued", "downloading", "merging", "completed", "cancelled", "error"
    progress: float = 0.0  # 0.0 to 100.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed_str: str = "-- MB/s"
    eta_str: str = "--:--"
    size_str: str = "0 MB"
    error_message: str = ""
    target_filepath: str = ""
    cancel_requested: bool = False
    extra_info: Dict[str, Any] = field(default_factory=dict)


class DownloadManager:
    """Manages active downloads and batch queues in worker threads with thread-safe callbacks."""

    def __init__(self):
        self.tasks: Dict[str, DownloadTask] = {}
        self.queue: List[str] = []
        self.active_count: int = 0
        self.lock = threading.Lock()
        self.callbacks: List[Callable[[DownloadTask], None]] = []

    def register_callback(self, cb: Callable[[DownloadTask], None]) -> None:
        """Register a callback that fires whenever a task state updates."""
        self.callbacks.append(cb)

    def _notify(self, task: DownloadTask) -> None:
        for cb in self.callbacks:
            try:
                cb(task)
            except Exception as e:
                print(f"Error in download callback: {e}")

    def add_task(
        self,
        url: str,
        title: str,
        thumbnail_url: str = "",
        platform: Optional[str] = None,
        mode: str = "video",
        resolution: str = "Best Quality",
        audio_format: str = "mp3",
        audio_bitrate: str = "320k",
        save_dir: Optional[str] = None,
        naming_template: Optional[str] = None,
        order_num: int = 1,
        time_range: Optional[Tuple[str, str]] = None,
        subtitles_mode: Optional[str] = None,
        speed_limit: Optional[str] = None,
        subfolder_rule: Optional[str] = None,
        skip_existing: Optional[bool] = None,
        extra_info: Optional[Dict[str, Any]] = None
    ) -> DownloadTask:
        save_directory = save_dir or config.download_dir
        os.makedirs(save_directory, exist_ok=True)
        resolved_url = resolve_media_url(url)
        detected_plat = platform or detect_platform(resolved_url)
        template = naming_template or config.get("naming_template", "Title + ID (Default)")
        sub_mode = subtitles_mode or config.get("subtitles_mode", "None")
        s_limit = speed_limit or config.get("speed_limit", "Unlimited")
        s_rule = subfolder_rule or config.get("organize_subfolders", "None")
        s_skip = skip_existing if skip_existing is not None else config.get("skip_existing_files", True)

        # Deep Security Gating: Enforce Pro restrictions at the engine level
        if not verify_runtime_integrity():
            if "Best Quality" in resolution or any(k in resolution for k in ("1080", "2160", "1440", "4K", "2K", "4320", "8K", "Full HD")):
                resolution = "720p (HD)"
            if "320" in audio_bitrate:
                audio_bitrate = "192k"

        task = DownloadTask(
            task_id=str(uuid.uuid4()),
            url=url,
            title=title or "Loading metadata...",
            thumbnail_url=thumbnail_url,
            platform=detected_plat,
            mode=mode,
            resolution=resolution,
            audio_format=audio_format,
            audio_bitrate=audio_bitrate,
            save_dir=save_directory,
            naming_template=template,
            order_num=order_num,
            time_range=time_range,
            subtitles_mode=sub_mode,
            speed_limit=s_limit,
            subfolder_rule=s_rule,
            skip_existing=s_skip,
            extra_info=extra_info or {}
        )

        with self.lock:
            self.tasks[task.task_id] = task
            self.queue.append(task.task_id)

        self._notify(task)
        self._process_queue()
        return task

    def add_batch(
        self,
        urls: List[str],
        mode: str = "video",
        resolution: str = "Best Quality",
        audio_format: str = "mp3",
        audio_bitrate: str = "320k",
        save_dir: Optional[str] = None,
        naming_template: Optional[str] = None,
        start_num: int = 1,
        speed_limit: Optional[str] = None,
        subfolder_rule: Optional[str] = None,
        skip_existing: Optional[bool] = None
    ) -> List[DownloadTask]:
        """Queues multiple URLs as batch download tasks with sequential order numbers."""
        # Deep Security Gating: Limit batch queues to 5 items if not Pro
        if not verify_runtime_integrity() and len(urls) > 5:
            urls = urls[:5]

        batch_tasks = []
        for i, u in enumerate(urls, start=start_num):
            plat = detect_platform(u)
            plat_name = get_platform_label(plat)
            task = self.add_task(
                url=u,
                title=f"{plat_name} #{i}",
                platform=plat,
                mode=mode,
                resolution=resolution,
                audio_format=audio_format,
                audio_bitrate=audio_bitrate,
                save_dir=save_dir,
                naming_template=naming_template,
                order_num=i,
                speed_limit=speed_limit,
                subfolder_rule=subfolder_rule,
                skip_existing=skip_existing
            )
            batch_tasks.append(task)
        return batch_tasks

    def cancel_task(self, task_id: str) -> None:
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.cancel_requested = True
                if task.status == "queued":
                    task.status = "cancelled"
                    if task_id in self.queue:
                        self.queue.remove(task_id)
                self._notify(task)

    def cancel_all(self) -> None:
        with self.lock:
            for task in self.tasks.values():
                if task.status in ["queued", "downloading", "merging"]:
                    task.cancel_requested = True
                    if task.status == "queued":
                        task.status = "cancelled"
            self.queue.clear()

    def remove_task(self, task_id: str) -> None:
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status not in ["downloading", "merging"]:
                    if task_id in self.queue:
                        self.queue.remove(task_id)
                    del self.tasks[task_id]
                else:
                    task.cancel_requested = True

    def clear_finished_tasks(self) -> None:
        with self.lock:
            finished_ids = [
                tid for tid, task in self.tasks.items()
                if task.status in ["completed", "error", "cancelled"]
            ]
            for tid in finished_ids:
                del self.tasks[tid]

    def _process_queue(self) -> None:
        with self.lock:
            max_concurrent = config.get("max_concurrent", 3)
            while self.queue and self.active_count < max_concurrent:
                task_id = self.queue.pop(0)
                task = self.tasks.get(task_id)
                if not task or task.cancel_requested:
                    continue
                self.active_count += 1
                threading.Thread(target=self._run_download, args=(task,), daemon=True).start()

    def _build_ydl_options(self, task: DownloadTask) -> Dict[str, Any]:
        ffmpeg_path = ensure_ffmpeg_in_path()
        has_ffmpeg = ffmpeg_path is not None

        template_raw = NAMING_TEMPLATES.get(task.naming_template, "%(title)s [%(id)s].%(ext)s")
        num_val = getattr(task, "order_num", 1) or 1
        try:
            template_pattern = template_raw.format(num=num_val)
        except Exception:
            template_pattern = template_raw

        # Smart Subfolder Routing
        target_dir = task.save_dir
        rule = task.subfolder_rule or config.get("organize_subfolders", "None")
        if rule in ["By Platform", "By Platform & Creator"]:
            target_dir = os.path.join(target_dir, get_platform_label(task.platform))
        os.makedirs(target_dir, exist_ok=True)

        outtmpl = os.path.join(target_dir, template_pattern)

        ydl_opts: Dict[str, Any] = {
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [lambda d: self._progress_hook(task, d)],
        }

        # Duplicate Handling
        if task.skip_existing:
            ydl_opts["nooverwrites"] = True
            ydl_opts["continue_dl"] = True

        # Speed Limiter
        s_limit = task.speed_limit or config.get("speed_limit", "Unlimited")
        if s_limit and s_limit != "Unlimited":
            try:
                mb = float(s_limit.split()[0])
                ydl_opts["ratelimit"] = int(mb * 1024 * 1024)
            except Exception:
                pass

        # Timestamp Trimmer / Range Downloader
        if task.time_range:
            start_str, end_str = task.time_range
            s_sec = parse_time_to_seconds(start_str)
            e_sec = parse_time_to_seconds(end_str)
            if s_sec is not None or e_sec is not None:
                from yt_dlp.utils import download_range_func
                s = s_sec if s_sec is not None else 0
                e = e_sec if e_sec is not None else float("inf")
                ydl_opts["download_ranges"] = download_range_func(None, [(s, e)])
                ydl_opts["force_keyframes_at_cuts"] = True

        # Subtitles & Captions
        sub_mode = task.subtitles_mode or config.get("subtitles_mode", "None")
        if sub_mode in ["Download .SRT", "Burn into Video"]:
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = True
            ydl_opts["subtitleslangs"] = ["en.*", "en", "all"]
            ydl_opts["subtitlesformat"] = "srt/best"

        if shutil.which("node"):
            ydl_opts["js_runtimes"] = {"node": {}}

        if ffmpeg_path:
            ydl_opts["ffmpeg_location"] = ffmpeg_path

        if task.mode == "audio":
            # Extract Audio Mode
            if has_ffmpeg:
                ydl_opts["format"] = "bestaudio/best"
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": task.audio_format,
                    "preferredquality": task.audio_bitrate.replace("k", ""),
                }]
            else:
                ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        else:
            # Video Mode
            match = re.search(r"(\d+)p", task.resolution)
            target_dim = int(match.group(1)) if match else None

            # Deep Security Gating: Strictly limit Free Edition to 720p
            if not verify_runtime_integrity():
                if target_dim is None or target_dim > 720:
                    target_dim = 720

            if task.platform in ["tiktok", "instagram", "pinterest"]:
                # TikTok, Instagram Reels, and Pinterest are typically unified MP4 streams
                ydl_opts["format"] = "best/bestvideo+bestaudio"
            elif has_ffmpeg:
                if target_dim:
                    # Support both landscape (height<=dim) and portrait/vertical (width<=dim)
                    ydl_opts["format"] = (
                        f"bestvideo[height<={target_dim}][ext=mp4]+bestaudio[ext=m4a]/"
                        f"bestvideo[width<={target_dim}][ext=mp4]+bestaudio[ext=m4a]/"
                        f"bestvideo[height<={target_dim}]+bestaudio/"
                        f"bestvideo[width<={target_dim}]+bestaudio/"
                        f"bestvideo+bestaudio/"
                        f"best[height<={target_dim}]/"
                        f"best"
                    )
                else:
                    ydl_opts["format"] = (
                        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                        "bestvideo+bestaudio/"
                        "best[ext=mp4]/"
                        "best"
                    )
                ydl_opts["merge_output_format"] = "mp4"
            else:
                # Fallback without ffmpeg
                if target_dim:
                    ydl_opts["format"] = f"best[height<={target_dim}]/best[width<={target_dim}]/best"
                else:
                    ydl_opts["format"] = "best"

            # Subtitle burn-in if requested and ffmpeg is present
            if sub_mode == "Burn into Video" and has_ffmpeg:
                if "postprocessors" not in ydl_opts:
                    ydl_opts["postprocessors"] = []
                ydl_opts["postprocessors"].append({
                    "key": "FFmpegEmbedSubtitle",
                    "already_have_subtitle": False
                })

        # TikTok specific optimization: bypass watermarks
        if task.platform == "tiktok":
            ydl_opts["extractor_args"] = {"tiktok": {"api_hostname": "api22-core-c-useast1a.musical.ly"}}

        return ydl_opts

    def _progress_hook(self, task: DownloadTask, d: Dict[str, Any]) -> None:
        if task.cancel_requested:
            raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")

        status = d.get("status")
        if status == "downloading":
            task.status = "downloading"
            downloaded = d.get("downloaded_bytes", 0) or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0) or 0

            task.downloaded_bytes = downloaded
            task.total_bytes = total

            if total > 0:
                task.progress = min(99.0, (downloaded / total) * 100.0)
                task.size_str = f"{format_bytes(downloaded)} / {format_bytes(total)}"
            else:
                task.size_str = f"{format_bytes(downloaded)}"

            speed = d.get("speed")
            if speed:
                task.speed_str = f"{format_bytes(speed)}/s"

            eta = d.get("eta")
            if eta is not None:
                task.eta_str = format_duration(int(eta))

            self._notify(task)

        elif status == "finished":
            task.status = "merging"
            task.progress = 99.0
            task.speed_str = "Finishing..."
            task.eta_str = "00:00"
            if "filename" in d:
                task.target_filepath = d["filename"]
            self._notify(task)

    def _run_download(self, task: DownloadTask) -> None:
        try:
            # 1. Check if already downloaded in history or save folder (Duplicate Auto-Skip)
            if task.skip_existing and config.get("skip_existing_files", True):
                for h in config.history:
                    if h.get("url") == task.url and h.get("filepath") and os.path.exists(h["filepath"]):
                        task.target_filepath = h["filepath"]
                        if h.get("title") and task.title in ["", "Loading metadata..."]:
                            task.title = h["title"]
                        task.status = "completed"
                        task.progress = 100.0
                        task.speed_str = "Skipped (Exists)"
                        task.eta_str = "00:00"
                        self._notify(task)
                        with self.lock:
                            self.active_count = max(0, self.active_count - 1)
                        self._process_queue()
                        return

            task.status = "downloading"
            self._notify(task)

            # High-speed direct streaming for Pinterest (Videos and HD Images)
            if task.platform == "pinterest":
                self._run_pinterest_download(task)
                return

            ydl_opts = self._build_ydl_options(task)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                res_info = ydl.extract_info(task.url, download=True)
                final_path = ""
                if res_info:
                    # Update real title if we only had placeholder
                    if "title" in res_info and res_info["title"]:
                        task.title = res_info["title"]

                    requested_downloads = res_info.get("requested_downloads")
                    if requested_downloads and len(requested_downloads) > 0:
                        final_path = requested_downloads[0].get("filepath", "")
                    if not final_path or not os.path.exists(final_path):
                        prepared = ydl.prepare_filename(res_info)
                        base, _ = os.path.splitext(prepared)
                        for ext in [".mp4", ".mkv", ".mp3", ".m4a", ".webm", ".wav"]:
                            if os.path.exists(base + ext):
                                final_path = base + ext
                                break
                        if not final_path and os.path.exists(prepared):
                            final_path = prepared
                task.target_filepath = final_path or task.target_filepath

            if task.cancel_requested:
                task.status = "cancelled"
            else:
                task.status = "completed"
                task.progress = 100.0
                task.speed_str = "Done"
                task.eta_str = "00:00"

                # Record in history
                file_size = 0
                if task.target_filepath and os.path.exists(task.target_filepath):
                    file_size = os.path.getsize(task.target_filepath)

                config.add_history({
                    "id": task.task_id,
                    "title": task.title,
                    "url": task.url,
                    "platform": task.platform,
                    "filepath": task.target_filepath,
                    "mode": task.mode,
                    "resolution": task.resolution if task.mode == "video" else task.audio_format.upper(),
                    "filesize": format_bytes(file_size),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M"),
                    "status": "completed"
                })

                # Audio chime notification on completion
                if config.get("completion_sound", True):
                    try:
                        import winsound
                        winsound.MessageBeep(winsound.MB_ICONASTERISK)
                    except Exception:
                        pass

        except yt_dlp.utils.DownloadCancelled:
            task.status = "cancelled"
            task.error_message = "Cancelled"
        except Exception as e:
            task.status = "error"
            task.error_message = str(e)
            print(f"Download task error: {e}")
        finally:
            with self.lock:
                self.active_count = max(0, self.active_count - 1)
            self._notify(task)
            self._process_queue()

    def _run_pinterest_download(self, task: DownloadTask) -> None:
        """Direct streaming download worker for Pinterest Pins (Videos and HD Images)."""
        try:
            direct_url = ""
            ext = "mp4"
            creator = "Pinterest"
            if task.extra_info and task.extra_info.get("direct_download_url"):
                direct_url = task.extra_info["direct_download_url"]
                ext = task.extra_info.get("ext", "mp4")
                creator = task.extra_info.get("uploader") or "Pinterest"
                if not task.thumbnail_url and task.extra_info.get("image_url"):
                    task.thumbnail_url = task.extra_info["image_url"]
            else:
                p_data = extract_pinterest_pin_data(task.url)
                direct_url = p_data["download_url"]
                ext = p_data["ext"]
                creator = p_data.get("uploader") or "Pinterest"
                if not task.title or task.title == "Loading metadata...":
                    task.title = p_data["title"]
                if not task.thumbnail_url:
                    task.thumbnail_url = p_data["image_url"]

            if not direct_url:
                raise RuntimeError("Could not find direct media stream for Pinterest Pin.")

            target_dir = task.save_dir or config.download_dir
            sub_mode = task.subfolder_rule or config.get("organize_subfolders", "None")
            if sub_mode == "By Platform":
                target_dir = os.path.join(target_dir, "Pinterest")
            elif sub_mode == "By Creator" and creator:
                target_dir = os.path.join(target_dir, sanitize_filename(creator))
            elif sub_mode == "By Platform & Creator":
                target_dir = os.path.join(target_dir, "Pinterest", sanitize_filename(creator))
            os.makedirs(target_dir, exist_ok=True)

            clean_t = sanitize_filename(task.title)[:60].strip() or f"Pinterest_{task.task_id[:8]}"
            out_filename = f"{clean_t}.{ext}"
            out_filepath = os.path.join(target_dir, out_filename)

            counter = 1
            while os.path.exists(out_filepath):
                out_filepath = os.path.join(target_dir, f"{clean_t}_{counter}.{ext}")
                counter += 1

            task.target_filepath = out_filepath
            s = get_pinterest_session()
            r_stream = s.get(direct_url, stream=True, timeout=20, headers={"Referer": "https://www.pinterest.com/"})
            r_stream.raise_for_status()

            total_bytes = int(r_stream.headers.get("content-length", 0))
            task.total_bytes = total_bytes
            downloaded = 0
            start_time = time.time()
            last_notify = start_time

            with open(out_filepath, "wb") as f:
                for chunk in r_stream.iter_content(chunk_size=65536):
                    if task.cancel_requested:
                        raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        task.downloaded_bytes = downloaded

                        now = time.time()
                        if now - last_notify >= 0.25:
                            last_notify = now
                            elapsed = max(0.01, now - start_time)
                            speed = downloaded / elapsed
                            task.speed_str = f"{format_bytes(speed)}/s"
                            if total_bytes > 0:
                                task.progress = min(99.0, (downloaded / total_bytes) * 100.0)
                                task.size_str = f"{format_bytes(downloaded)} / {format_bytes(total_bytes)}"
                                rem_bytes = max(0, total_bytes - downloaded)
                                eta = rem_bytes / max(1, speed)
                                task.eta_str = format_duration(int(eta))
                            else:
                                task.size_str = format_bytes(downloaded)
                            self._notify(task)

            task.status = "completed"
            task.progress = 100.0
            task.speed_str = "Done"
            task.eta_str = "00:00"
            task.downloaded_bytes = downloaded
            task.size_str = format_bytes(downloaded)

            config.add_history({
                "id": task.task_id,
                "title": task.title,
                "url": task.url,
                "platform": "pinterest",
                "filepath": task.target_filepath,
                "mode": "image" if ext in ("jpg", "jpeg", "png", "webp") else "video",
                "resolution": "Original Image (HD)" if ext in ("jpg", "jpeg", "png", "webp") else "Video HD",
                "filesize": format_bytes(downloaded),
                "timestamp": time.strftime("%Y-%m-%d %H:%M"),
                "status": "completed"
            })

            if config.get("completion_sound", True):
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

        except yt_dlp.utils.DownloadCancelled:
            task.status = "cancelled"
            task.error_message = "Cancelled"
        except Exception as e:
            task.status = "error"
            task.error_message = str(e)
            print(f"Pinterest direct download error: {e}")
        finally:
            with self.lock:
                self.active_count = max(0, self.active_count - 1)
            self._notify(task)
            self._process_queue()


# Global download manager instance
download_manager = DownloadManager()
