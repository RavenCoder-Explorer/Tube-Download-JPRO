# Tube Download JPRO

**Tube Download JPRO** is a high-performance desktop media downloader for Windows built for content creators, video editors, and digital archivists. It supports high-speed downloads from **YouTube**, **YouTube Shorts**, **TikTok** (watermark-free), and **Instagram Reels**, complete with high-resolution presets, audio extraction, timestamp trimming, subtitle burning, and visual channel scraping.

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20(64--bit)-0078D4?style=flat-square&logo=windows)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter%20(Obsidian)-0284C7?style=flat-square)
![License](https://img.shields.io/badge/License-Commercial%20%2F%20Free%20Tier-10B981?style=flat-square)

---

## ⚡ Free Edition vs. 👑 Pro Edition

Tube Download JPRO offers a generous **Free Edition** alongside the commercial **Pro Edition**:

| Capability / Feature | Free Edition | 👑 Pro Edition |
| :--- | :--- | :--- |
| **Maximum Video Resolution** | **720p (HD)** | **✔ 1080p (Full HD), 4K & 8K Ultra HD** |
| **Batch Queue Capacity** | 5 items per batch | **✔ Unlimited bulk queue** |
| **Channel & Playlist Scraper** | 5 clips preview | **✔ Scrape 100+ clips in 1 click** |
| **Audio Bitrate (MP3)** | 192kbps Standard | **✔ 320kbps High Fidelity Studio** |
| **Watermark-Free TikTok & Reels** | ✔ Supported | **✔ Supported (Original CDN Stream)** |
| **Timestamp Video Trimmer** | ✔ Supported | **✔ Supported (Precision Keyframe Slicing)** |
| **Subtitles / CC Burning** | ✔ Supported | **✔ Supported (Embedded .SRT or Burned-in)** |
| **Smart Clipboard Watcher** | ✔ Supported | **✔ Supported** |
| **Duplicate Auto-Skip** | ✔ Supported | **✔ Supported** |
| **Engine Auto-Updates** | Standard | **✔ Priority PyPI Extraction Patches** |
| **Device Activation** | Unlimited Free PCs | 1 Hardware-Locked PC License |

---

## 🌟 Key Features

### 1. 📥 Universal Single Media Downloader
- **YouTube**: 720p HD (Free), and 1080p Full HD, 1440p (2K), 2160p (4K), 4320p (8K) (Pro).
- **TikTok**: Automatic watermark-free video extraction directly from source CDN streams.
- **Instagram Reels**: Direct high-definition Reels extraction.
- **Audio Extraction**: Studio-quality MP3 (up to 320kbps), M4A, or WAV with embedded metadata and cover artwork.
- **Instant Media Preview**: Shows high-resolution thumbnail, duration, view count, and creator info before downloading.

### 2. ⚡ Batch Shorts & Reels Downloader
- Bulk queue dozens or hundreds of URLs simultaneously.
- Automatic multi-URL parser extracting valid links from multi-line text or pasted lists.
- Individual progress cards displaying download speed (MB/s), ETA, and file size.
- Post-batch actions: optional **Sleep PC** or **Shutdown PC** when overnight batches complete.

### 3. 👥 Interactive Channel & Playlist Scraper (Pro Exclusive)
- Paste any YouTube channel (e.g., `/@creator/shorts`), TikTok profile, or playlist link.
- Fast metadata scraper retrieves up to 100 clips in 3–4 seconds.
- Visual grid interface with thumbnails, video titles, durations, and view counts.
- 1-Click select-all and bulk import directly into the Batch Queue.

### 4. ✂️ Timestamp Range Trimmer
- Download only the specific section of a video you need (e.g., `01:15` to `02:45`).
- Uses `yt-dlp` stream-level keyframe slicing so you don't waste bandwidth downloading the entire video.

### 5. 📝 Subtitles & Closed Captions (CC)
- Auto-extract English and multi-language subtitles.
- Choose between downloading standalone `.srt` files or permanently burning subtitles into the MP4 video via FFmpeg.

### 6. 📋 Smart Clipboard Watcher
- Monitors your clipboard in the background.
- Copying any video link from your web browser displays an instant obsidian drop-down banner:
  - `[ 📥 Single Download ]`
  - `[ ➕ Add to Batch ]`
  - `[ ✕ Dismiss ]`

### 7. ⏭️ Duplicate Detection & Auto-Skip
- Automatically detects if a video has already been downloaded in previous sessions or exists in your target directory, preventing duplicate files and wasted bandwidth.

### 8. 🔄 1-Click yt-dlp Engine Auto-Updater
- When YouTube or TikTok alters their backend algorithms, update your extraction engine directly within **Settings > Engine Updates** with 1 click without reinstalling the application.

---

## 🚀 Quick Start

### Option A: Portable Standalone Executable (Zero Setup)
1. Download **`TubeDownloadJPRO.zip`** from the [Releases](https://github.com/RavenCoder-Explorer/Tube-Download-JPRO/releases) section.
2. Extract the folder to any location on your Windows computer.
3. Double-click **`TubeDownloadJPRO.exe`**.

### Option B: Run from Source
```powershell
# 1. Clone the repository
git clone https://github.com/RavenCoder-Explorer/Tube-Download-JPRO.git
cd "Tube Download JPRO"

# 2. Set up virtual environment and install dependencies
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 3. Launch application
python main.py
```

### Option C: Build Standalone Executable (.exe)
```powershell
.\build_exe.bat
```
The compiled, standalone portable package will be generated in `dist\TubeDownloadJPRO\TubeDownloadJPRO.exe`.

---

## 🛡️ Requirements

- **Operating System**: Windows 10 or Windows 11 (64-bit).
- **FFmpeg**: Pre-bundled static portable binaries are included in `bin/` for stream merging and MP3 conversion. Zero additional configuration required.

---

## 📄 License & Support

- **Free Edition**: Free for personal use.
- **Pro Edition**: Commercial licenses available with instant digital delivery via [Lemon Squeezy](https://jprosoftware.lemonsqueezy.com).
- **Support**: `jprosoftware.support@gmail.com`
