import os
import threading
import customtkinter as ctk

from app.config import config
from app.downloader import NAMING_TEMPLATES, NAMING_EXAMPLES, check_engine_update, run_engine_update
from app.ffmpeg_helper import get_ffmpeg_path, is_ffmpeg_available, download_and_setup_ffmpeg
from app.license_manager import is_pro_active, deactivate_license, get_license_info, register_license_callback, get_formatted_device_id
from app.ui.pro_dialog import ProDialog
from app.ui.theme import (
    COLOR_WINDOW_BG, COLOR_CARD_BG, COLOR_CARD_BORDER, NEON_CYAN, NEON_CYAN_MID, NEON_CYAN_DEEP,
    NEON_EMERALD, CROWN_GOLD, style_crown_gold_button, style_glass_button,
    style_danger_glass_button, style_neon_cyan_button, style_card
)


class SettingsView(ctk.CTkFrame):
    """Professional settings panel for Tube Download JPRO."""

    def __init__(self, master, on_theme_change=None, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=COLOR_WINDOW_BG, **kwargs)
        self.on_theme_change = on_theme_change
        self.is_downloading_ffmpeg = False

        self._build_ui()
        register_license_callback(lambda is_pro: self._update_license_display())
        self._update_license_display()
        if config.get("auto_update_engine", True):
            self.after(3000, self._check_engine_silent)

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(20, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        title = ctk.CTkLabel(
            title_box,
            text="Preferences & System",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(anchor="w")

        sub = ctk.CTkLabel(
            title_box,
            text="Manage storage locations, themes, concurrency, and FFmpeg engine integration",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8")
        )
        sub.pack(anchor="w")

        # Scrollable container for settings
        scroll = ctk.CTkScrollableFrame(self, fg_color=COLOR_WINDOW_BG)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # 0. Commercial Pro Licensing Card (Highlighted in Crown Gold)
        self.license_card = ctk.CTkFrame(
            scroll,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=("#F59E0B", "#B45309")
        )
        self.license_card.pack(fill="x", padx=10, pady=(0, 15))

        lic_header = ctk.CTkFrame(self.license_card, fg_color="transparent")
        lic_header.pack(fill="x", padx=20, pady=(15, 4))

        lic_title = ctk.CTkLabel(
            lic_header,
            text="Pro License & Commercial Activation",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lic_title.pack(side="left")

        self.lic_badge = ctk.CTkLabel(
            lic_header,
            text="FREE EDITION",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=("#64748B", "#475569"),
            text_color="white",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.lic_badge.pack(side="right")

        self.lic_desc = ctk.CTkLabel(
            self.license_card,
            text="You are using the Free Edition (limited to 720p HD and 5 batch items). Upgrade to Pro for 1080p Full HD, 4K UHD, and channel scraping.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8"),
            anchor="w",
            wraplength=540,
            justify="left"
        )
        self.lic_desc.pack(fill="x", padx=20, pady=(0, 10))

        # Action Buttons Row
        self.lic_actions = ctk.CTkFrame(self.license_card, fg_color="transparent")
        self.lic_actions.pack(fill="x", padx=20, pady=(0, 15))

        self.lic_upgrade_btn = ctk.CTkButton(
            self.lic_actions,
            text="⭐ Upgrade to Pro ($19.00)",
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._open_pro_dialog
        )
        style_crown_gold_button(self.lic_upgrade_btn)
        self.lic_upgrade_btn.pack(side="left", padx=(0, 8))

        self.lic_enter_key_btn = ctk.CTkButton(
            self.lic_actions,
            text="🔑 Enter License Key",
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._open_pro_dialog
        )
        style_glass_button(self.lic_enter_key_btn)
        self.lic_enter_key_btn.pack(side="left", padx=(0, 8))

        self.lic_deactivate_btn = ctk.CTkButton(
            self.lic_actions,
            text="✕ Deactivate License",
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_deactivate_clicked
        )
        style_danger_glass_button(self.lic_deactivate_btn)

        # Device ID for 1-Device Locking
        dev_row = ctk.CTkFrame(self.license_card, fg_color="transparent")
        dev_row.pack(fill="x", padx=20, pady=(0, 15))

        dev_id = get_formatted_device_id()
        ctk.CTkLabel(
            dev_row,
            text=f"💻 Device ID (1-Device Lock): {dev_id}",
            font=ctk.CTkFont(size=11, family="Consolas"),
            text_color=("gray40", "#94A3B8")
        ).pack(side="left")

        def _copy_settings_dev_id():
            self.clipboard_clear()
            self.clipboard_append(dev_id)
            dev_copy_btn.configure(text="✔ Copied!", fg_color="#10B981")
            self.after(2000, lambda: dev_copy_btn.configure(text="📋 Copy ID"))

        dev_copy_btn = ctk.CTkButton(
            dev_row,
            text="📋 Copy ID",
            width=75,
            height=26,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=_copy_settings_dev_id
        )
        style_glass_button(dev_copy_btn)
        dev_copy_btn.pack(side="left", padx=10)

        # 1. Download Location Card
        dir_card = ctk.CTkFrame(
            scroll,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        dir_card.pack(fill="x", padx=10, pady=(0, 15))

        d_title = ctk.CTkLabel(
            dir_card,
            text="Default Save Directory",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        d_title.pack(anchor="w", padx=20, pady=(15, 4))

        d_desc = ctk.CTkLabel(
            dir_card,
            text="Downloaded videos, shorts, reels, and audio tracks are saved to this folder.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8")
        )
        d_desc.pack(anchor="w", padx=20, pady=(0, 10))

        d_row = ctk.CTkFrame(dir_card, fg_color="transparent")
        d_row.pack(fill="x", padx=20, pady=(0, 15))

        self.dir_entry = ctk.CTkEntry(
            d_row,
            height=38,
            font=ctk.CTkFont(size=12),
            fg_color=("white", "#0F172A")
        )
        self.dir_entry.insert(0, config.download_dir)
        self.dir_entry.configure(state="disabled")
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_btn = ctk.CTkButton(
            d_row,
            text="Browse...",
            width=90,
            height=38,
            font=ctk.CTkFont(size=12),
            fg_color=("gray80", "#334155"),
            text_color=("black", "white"),
            command=self._choose_directory
        )
        browse_btn.pack(side="right")

        # 2. Smart Organization & Rules Card
        rules_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=("gray90", "#1E293B"))
        rules_card.pack(fill="x", padx=10, pady=(0, 15))

        r_title = ctk.CTkLabel(
            rules_card,
            text="Smart Organization & Automation",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        r_title.pack(anchor="w", padx=20, pady=(15, 6))

        r_desc = ctk.CTkLabel(
            rules_card,
            text="Automate subfolder sorting, avoid re-downloading files, and detect copied video links.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8")
        )
        r_desc.pack(anchor="w", padx=20, pady=(0, 10))

        # Subfolder rule
        sub_row = ctk.CTkFrame(rules_card, fg_color="transparent")
        sub_row.pack(fill="x", padx=20, pady=6)

        sub_lbl = ctk.CTkLabel(sub_row, text="Organize Subfolders:", width=180, anchor="w", font=ctk.CTkFont(size=13))
        sub_lbl.pack(side="left")

        subfolder_options = ["None", "By Platform", "By Creator", "By Platform & Creator"]
        cur_subfolder = config.get("organize_subfolders", "None")
        if cur_subfolder not in subfolder_options:
            cur_subfolder = "None"

        self.subfolder_menu = ctk.CTkOptionMenu(
            sub_row,
            values=subfolder_options,
            command=self._change_subfolder_rule,
            width=220,
            height=32
        )
        self.subfolder_menu.set(cur_subfolder)
        self.subfolder_menu.pack(side="left")

        # Duplicate detection checkbox
        dup_row = ctk.CTkFrame(rules_card, fg_color="transparent")
        dup_row.pack(fill="x", padx=20, pady=(10, 4))

        self.dup_var = ctk.BooleanVar(value=bool(config.get("skip_existing_files", True)))
        self.dup_cb = ctk.CTkCheckBox(
            dup_row,
            text="Skip duplicate downloads if media file or history already exists",
            variable=self.dup_var,
            command=self._change_dup_skip,
            font=ctk.CTkFont(size=13),
            checkbox_width=20,
            checkbox_height=20
        )
        self.dup_cb.pack(anchor="w")

        # Clipboard watcher checkbox
        clip_row = ctk.CTkFrame(rules_card, fg_color="transparent")
        clip_row.pack(fill="x", padx=20, pady=(6, 8))

        self.clip_var = ctk.BooleanVar(value=bool(config.get("clipboard_watcher", True)))
        self.clip_cb = ctk.CTkCheckBox(
            clip_row,
            text="Smart Clipboard Watcher (auto-detect YouTube, Shorts, TikTok, Reels & Pinterest links)",
            variable=self.clip_var,
            command=self._change_clipboard_watcher,
            font=ctk.CTkFont(size=13),
            checkbox_width=20,
            checkbox_height=20
        )
        self.clip_cb.pack(anchor="w")

        # Sound effects checkbox
        sound_row = ctk.CTkFrame(rules_card, fg_color="transparent")
        sound_row.pack(fill="x", padx=20, pady=(0, 15))

        self.sound_var = ctk.BooleanVar(value=bool(config.get("completion_sound", True)))
        self.sound_cb = ctk.CTkCheckBox(
            sound_row,
            text="🔔 Sound Chime: Play audio chime notification when download completes",
            variable=self.sound_var,
            command=self._change_completion_sound,
            font=ctk.CTkFont(size=13),
            checkbox_width=20,
            checkbox_height=20
        )
        self.sound_cb.pack(anchor="w")

        # 3. Appearance & Preferences Card
        pref_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=("gray90", "#1E293B"))
        pref_card.pack(fill="x", padx=10, pady=(0, 15))

        p_title = ctk.CTkLabel(
            pref_card,
            text="Interface & Concurrency",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        p_title.pack(anchor="w", padx=20, pady=(15, 10))

        # Theme Selector
        t_row = ctk.CTkFrame(pref_card, fg_color="transparent")
        t_row.pack(fill="x", padx=20, pady=6)

        t_lbl = ctk.CTkLabel(t_row, text="Color Scheme:", width=180, anchor="w", font=ctk.CTkFont(size=13))
        t_lbl.pack(side="left")

        self.theme_segment = ctk.CTkSegmentedButton(
            t_row,
            values=["Dark", "Light", "System"],
            command=self._change_theme,
            height=32
        )
        self.theme_segment.set(config.get("theme", "Dark"))
        self.theme_segment.pack(side="left", fill="x", expand=True)

        # Max Concurrent Downloads
        mc_row = ctk.CTkFrame(pref_card, fg_color="transparent")
        mc_row.pack(fill="x", padx=20, pady=(8, 8))

        mc_lbl = ctk.CTkLabel(mc_row, text="Simultaneous Downloads:", width=180, anchor="w", font=ctk.CTkFont(size=13))
        mc_lbl.pack(side="left")

        self.mc_menu = ctk.CTkOptionMenu(
            mc_row,
            values=["1", "2", "3", "5"],
            command=self._change_concurrent,
            width=100,
            height=32
        )
        self.mc_menu.set(str(config.get("max_concurrent", 3)))
        self.mc_menu.pack(side="left")

        # Global Speed Limit
        speed_row = ctk.CTkFrame(pref_card, fg_color="transparent")
        speed_row.pack(fill="x", padx=20, pady=(6, 8))

        speed_lbl = ctk.CTkLabel(speed_row, text="Default Speed Limit:", width=180, anchor="w", font=ctk.CTkFont(size=13))
        speed_lbl.pack(side="left")

        speed_options = ["Unlimited", "25 MB/s", "15 MB/s", "10 MB/s", "5 MB/s", "2 MB/s"]
        cur_speed = config.get("speed_limit", "Unlimited")
        if cur_speed not in speed_options:
            cur_speed = "Unlimited"

        self.speed_menu = ctk.CTkOptionMenu(
            speed_row,
            values=speed_options,
            command=self._change_speed_limit,
            width=140,
            height=32
        )
        self.speed_menu.set(cur_speed)
        self.speed_menu.pack(side="left")

        # File Naming Format
        name_row = ctk.CTkFrame(pref_card, fg_color="transparent")
        name_row.pack(fill="x", padx=20, pady=(6, 4))

        name_lbl = ctk.CTkLabel(name_row, text="Default Video Naming:", width=180, anchor="w", font=ctk.CTkFont(size=13))
        name_lbl.pack(side="left")

        self.naming_menu = ctk.CTkOptionMenu(
            name_row,
            values=list(NAMING_TEMPLATES.keys()),
            command=self._change_naming,
            width=220,
            height=32
        )
        cur_naming = config.get("naming_template", "Title + ID (Default)")
        if cur_naming not in NAMING_TEMPLATES:
            cur_naming = "Title + ID (Default)"
        self.naming_menu.set(cur_naming)
        self.naming_menu.pack(side="left")

        ex_str = NAMING_EXAMPLES.get(cur_naming, "")
        self.naming_example_lbl = ctk.CTkLabel(
            pref_card,
            text=f"Example: {ex_str}" if ex_str else f"Format: {cur_naming}",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color=("gray40", "#94A3B8"),
            anchor="w"
        )
        self.naming_example_lbl.pack(anchor="w", padx=20, pady=(0, 15))

        # 4. Engine & Updates Card (yt-dlp core updater)
        engine_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=("gray90", "#1E293B"))
        engine_card.pack(fill="x", padx=10, pady=(0, 15))

        e_title = ctk.CTkLabel(
            engine_card,
            text="yt-dlp Core Engine & Updates",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        e_title.pack(anchor="w", padx=20, pady=(15, 4))

        e_desc = ctk.CTkLabel(
            engine_card,
            text="YouTube and TikTok frequently update their video algorithms. Keep your downloader engine updated to fix broken downloads instantly.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8"),
            wraplength=600,
            justify="left"
        )
        e_desc.pack(anchor="w", padx=20, pady=(0, 10))

        # Engine Version Banner
        self.engine_status_frame = ctk.CTkFrame(engine_card, corner_radius=8, fg_color=("gray85", "#0F172A"))
        self.engine_status_frame.pack(fill="x", padx=20, pady=(0, 10))

        try:
            import yt_dlp
            cur_ytdlp_version = getattr(yt_dlp.version, "__version__", "Installed")
        except Exception:
            cur_ytdlp_version = "Unknown"

        self.engine_status_label = ctk.CTkLabel(
            self.engine_status_frame,
            text=f"Current Engine Version: yt-dlp v{cur_ytdlp_version}",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            padx=14,
            pady=10
        )
        self.engine_status_label.pack(fill="x")

        # Engine Update Action Row
        e_btn_row = ctk.CTkFrame(engine_card, fg_color="transparent")
        e_btn_row.pack(fill="x", padx=20, pady=(0, 15))

        self.update_engine_btn = ctk.CTkButton(
            e_btn_row,
            text="🔄  Check & Update Engine Now",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#1f6aa5", "#2563EB"),
            hover_color=("#185584", "#1D4ED8"),
            command=self._start_engine_update
        )
        self.update_engine_btn.pack(side="left", padx=(0, 15))

        self.auto_update_var = ctk.BooleanVar(value=bool(config.get("auto_update_engine", True)))
        self.auto_update_cb = ctk.CTkCheckBox(
            e_btn_row,
            text="Auto-check updates on app startup",
            variable=self.auto_update_var,
            command=self._change_auto_update,
            font=ctk.CTkFont(size=12),
            checkbox_width=18,
            checkbox_height=18
        )
        self.auto_update_cb.pack(side="left")

        # 5. FFmpeg Engine Card
        self.ffmpeg_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=("gray90", "#1E293B"))
        self.ffmpeg_card.pack(fill="x", padx=10, pady=(0, 15))

        f_title = ctk.CTkLabel(
            self.ffmpeg_card,
            text="FFmpeg Audio/Video Engine",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        f_title.pack(anchor="w", padx=20, pady=(15, 4))

        f_desc = ctk.CTkLabel(
            self.ffmpeg_card,
            text="FFmpeg powers high-resolution stream merging (4K/1080p video + audio), lossless audio transcoding, and subtitle embedding.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8"),
            wraplength=600,
            justify="left"
        )
        f_desc.pack(anchor="w", padx=20, pady=(0, 10))

        # Status banner
        self.ffmpeg_status_frame = ctk.CTkFrame(self.ffmpeg_card, corner_radius=8, fg_color=("gray85", "#0F172A"))
        self.ffmpeg_status_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.ffmpeg_status_label = ctk.CTkLabel(
            self.ffmpeg_status_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            padx=14,
            pady=10
        )
        self.ffmpeg_status_label.pack(fill="x")

        # Progress bar for FFmpeg install
        self.ffmpeg_progress = ctk.CTkProgressBar(self.ffmpeg_card, height=10, corner_radius=5)
        self.ffmpeg_progress.set(0)

        # Download / Setup FFmpeg button
        self.ffmpeg_btn = ctk.CTkButton(
            self.ffmpeg_card,
            text="⚡  Download & Setup FFmpeg Automatically",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#1f6aa5", "#2563EB"),
            hover_color=("#185584", "#1D4ED8"),
            command=self._start_ffmpeg_download
        )
        self.ffmpeg_btn.pack(anchor="w", padx=20, pady=(0, 15))

        self._update_ffmpeg_status()

        # 6. About Tube Download JPRO
        about_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=("gray90", "#1E293B"))
        about_card.pack(fill="x", padx=10, pady=(0, 10))

        a_title = ctk.CTkLabel(
            about_card,
            text="About Tube Download JPRO",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        a_title.pack(anchor="w", padx=20, pady=(15, 6))

        a_text = (
            "Tube Download JPRO v1.3.0 Professional Edition\n"
            "• Universal Downloader: YouTube (4K/1080p), YouTube Shorts, TikTok (No Watermark), Instagram Reels\n"
            "• Advanced Tools: Channel Scraper Grid, Subtitle Extractor & Burn-in, Timestamp Trimmer\n"
            "• Smart Management: Auto-Skip Duplicates, Folder Sorting, Speed Limiter, Auto-Shutdown / Sleep\n"
            "• Engine Core: Self-updating yt-dlp & FFmpeg portable suite"
        )
        a_lbl = ctk.CTkLabel(
            about_card,
            text=a_text,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8"),
            justify="left",
            anchor="w"
        )
        a_lbl.pack(anchor="w", padx=20, pady=(0, 15))

    def _update_ffmpeg_status(self):
        path = get_ffmpeg_path()
        if path:
            self.ffmpeg_status_label.configure(
                text=f"✔ FFmpeg Engine is active and operational\nPath: {path}",
                text_color="#10B981"
            )
            self.ffmpeg_btn.configure(text="✔ FFmpeg Engine Ready", state="disabled", fg_color=("gray70", "#334155"))
            self.ffmpeg_progress.pack_forget()
        else:
            self.ffmpeg_status_label.configure(
                text="⚠ FFmpeg is NOT detected.\n(1080p+ merging and MP3 conversion will be limited until installed)",
                text_color="#F59E0B"
            )
            self.ffmpeg_btn.configure(
                text="⚡  Download & Setup FFmpeg (One-Click)",
                state="normal",
                fg_color=("#1f6aa5", "#2563EB")
            )

    def _start_ffmpeg_download(self):
        if self.is_downloading_ffmpeg:
            return

        self.is_downloading_ffmpeg = True
        self.ffmpeg_btn.configure(state="disabled", text="⏳ Downloading FFmpeg...")
        self.ffmpeg_progress.pack(fill="x", padx=20, pady=(0, 10), before=self.ffmpeg_btn)
        self.ffmpeg_progress.set(0.05)

        def on_progress(percent: float, status: str):
            self.after(0, lambda: self._on_ffmpeg_progress(percent, status))

        def on_complete(success: bool, msg: str):
            self.after(0, lambda: self._on_ffmpeg_complete(success, msg))

        download_and_setup_ffmpeg(progress_callback=on_progress, completion_callback=on_complete)

    def _on_ffmpeg_progress(self, percent: float, status: str):
        self.ffmpeg_progress.set(percent)
        self.ffmpeg_status_label.configure(text=f"⏳ {status}", text_color=("#1f6aa5", "#38BDF8"))

    def _on_ffmpeg_complete(self, success: bool, msg: str):
        self.is_downloading_ffmpeg = False
        if success:
            self.ffmpeg_progress.set(1.0)
            self._update_ffmpeg_status()
        else:
            self.ffmpeg_status_label.configure(text=f"❌ Failed to download FFmpeg: {msg}", text_color="#EF4444")
            self.ffmpeg_btn.configure(state="normal", text="🔄 Retry FFmpeg Download")

    def _choose_directory(self):
        folder = ctk.filedialog.askdirectory(initialdir=config.download_dir)
        if folder:
            config.download_dir = folder
            self.dir_entry.configure(state="normal")
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, folder)
            self.dir_entry.configure(state="disabled")

    def _change_theme(self, theme: str):
        config.set("theme", theme)
        ctk.set_appearance_mode(theme)
        if self.on_theme_change:
            self.on_theme_change(theme)

    def _change_concurrent(self, val: str):
        try:
            config.set("max_concurrent", int(val))
        except ValueError:
            pass

    def _change_naming(self, val: str):
        config.set("naming_template", val)
        ex = NAMING_EXAMPLES.get(val, "")
        self.naming_example_lbl.configure(text=f"Example: {ex}" if ex else f"Format: {val}")

    def _change_subfolder_rule(self, val: str):
        config.set("organize_subfolders", val)

    def _change_dup_skip(self):
        config.set("skip_existing_files", self.dup_var.get())

    def _change_clipboard_watcher(self):
        config.set("clipboard_watcher", self.clip_var.get())

    def _change_completion_sound(self):
        config.set("completion_sound", self.sound_var.get())
        if self.sound_var.get():
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def _change_speed_limit(self, val: str):
        config.set("speed_limit", val)

    def _change_auto_update(self):
        config.set("auto_update_engine", self.auto_update_var.get())

    def _start_engine_update(self):
        self.update_engine_btn.configure(state="disabled", text="⏳ Checking & Updating...")
        self.engine_status_label.configure(
            text="⏳ Checking PyPI repository for the latest yt-dlp release...",
            text_color=("#1f6aa5", "#38BDF8")
        )

        def worker():
            has_update, cur_v, latest_v = check_engine_update()
            if not has_update:
                self.after(0, lambda: self._on_engine_update_status(
                    f"✔ Engine is up to date! (yt-dlp v{cur_v})",
                    "#10B981"
                ))
                return

            self.after(0, lambda: self.engine_status_label.configure(
                text=f"⚡ Upgrading yt-dlp from v{cur_v} to v{latest_v} in background...",
                text_color=("#1f6aa5", "#38BDF8")
            ))
            success, msg = run_engine_update()
            if success:
                self.after(0, lambda: self._on_engine_update_status(
                    f"✔ Successfully upgraded engine to v{latest_v}! Downloads now use latest extractor patches.",
                    "#10B981"
                ))
            else:
                self.after(0, lambda: self._on_engine_update_status(
                    f"❌ Update error: {msg}",
                    "#EF4444"
                ))

        threading.Thread(target=worker, daemon=True).start()

    def _on_engine_update_status(self, msg: str, color: str):
        self.engine_status_label.configure(text=msg, text_color=color)
        self.update_engine_btn.configure(state="normal", text="🔄  Check & Update Engine Now")

    def _check_engine_silent(self):
        def worker():
            try:
                has_update, cur_v, latest_v = check_engine_update()
                if has_update:
                    self.after(0, lambda: self.engine_status_label.configure(
                        text=f"⚡ New yt-dlp release available (v{latest_v}). Click 'Check & Update' to upgrade!",
                        text_color="#F59E0B"
                    ))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _open_pro_dialog(self):
        ProDialog(self, on_activated=self._update_license_display)

    def _on_deactivate_clicked(self):
        success, msg = deactivate_license()
        self._update_license_display()

    def _update_license_display(self):
        info = get_license_info()
        if info["is_pro"]:
            tier_badge = info.get("tier_label", "👑 PRO LIFETIME")
            self.lic_badge.configure(
                text=tier_badge,
                fg_color=("#D97706", "#F59E0B"),
                text_color="#0F172A"
            )
            key_str = f" • Key: {info['masked_key']}" if info['masked_key'] else ""
            plan_str = f"Plan: {info['plan_name']}"
            if info.get("days_left") != "Lifetime":
                exp_str = f" • Valid until: {info.get('expires_at')} ({info.get('days_left')} days left)"
            else:
                exp_str = " • Lifetime Access (Never Expires)"
            self.lic_desc.configure(
                text=f"✔ Active Pro License ({plan_str}){key_str}{exp_str}. All 4K UHD, channel scraping, and batch features unlocked."
            )
            self.lic_upgrade_btn.pack_forget()
            self.lic_enter_key_btn.pack_forget()
            if not self.lic_deactivate_btn.winfo_ismapped():
                self.lic_deactivate_btn.pack(side="left")
        else:
            self.lic_badge.configure(
                text="FREE EDITION",
                fg_color=("#64748B", "#475569"),
                text_color="white"
            )
            self.lic_desc.configure(
                text="You are using the Free Edition (limited to 720p HD and 5 batch items). Upgrade to Pro for 1080p Full HD, 4K UHD, and channel scraping."
            )
            self.lic_deactivate_btn.pack_forget()
            if not self.lic_upgrade_btn.winfo_ismapped():
                self.lic_upgrade_btn.pack(side="left", padx=(0, 8))
            if not self.lic_enter_key_btn.winfo_ismapped():
                self.lic_enter_key_btn.pack(side="left")


