from typing import Optional
import customtkinter as ctk

from app.config import config
from app.ffmpeg_helper import is_ffmpeg_available
from app.downloader import download_manager, DownloadTask, extract_supported_urls, detect_platform, get_platform_label
from app.license_manager import is_pro_active, register_license_callback, get_license_info
from app.ui.theme import (
    COLOR_WINDOW_BG, COLOR_SIDEBAR_BG, COLOR_CARD_BG, COLOR_CARD_BORDER,
    NEON_CYAN, NEON_CYAN_MID, NEON_CYAN_DEEP, NEON_EMERALD, CROWN_GOLD,
    get_app_icon_image, style_crown_gold_button, style_neon_cyan_button,
    style_neon_emerald_button, style_glass_button
)
from app.ui.download_view import DownloadView
from app.ui.batch_view import BatchView
from app.ui.history_view import HistoryView
from app.ui.settings_view import SettingsView
from app.ui.pro_dialog import ProDialog


class MainWindow(ctk.CTk):
    """Professional main window for Tube Download JPRO with multi-tab workflow."""

    def __init__(self):
        super().__init__()

        # Appearance configuration
        saved_theme = config.get("theme", "Dark")
        ctk.set_appearance_mode(saved_theme)
        ctk.set_default_color_theme("blue")

        self.title("Tube Download JPRO — Shorts, Reels & Video Downloader")
        self.geometry("1080x740")
        self.minsize(920, 640)
        self.configure(fg_color=COLOR_WINDOW_BG)

        # Set application icon
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "app_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Configure grid layout (1 row, 2 columns: sidebar and main)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_views()

        # Smart Clipboard Watcher initialization
        self.last_clipboard = ""
        self.detected_url = ""
        self.after(2000, self._clipboard_loop)

        # Listen for task updates to update queue badges and indicators
        download_manager.register_callback(self._on_task_update)
        register_license_callback(self._update_license_ui)

        # Start on Downloader view
        self.select_tab("downloader")
        self._update_license_ui()

    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=COLOR_SIDEBAR_BG)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        # App Logo & Branding Header
        brand_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand_frame.pack(fill="x", padx=16, pady=(20, 16))

        # Brand row with 3D Crowned Icon thumbnail
        brand_row = ctk.CTkFrame(brand_frame, fg_color="transparent")
        brand_row.pack(fill="x")

        self.brand_icon_img = get_app_icon_image((42, 42))
        if self.brand_icon_img:
            self.brand_icon_lbl = ctk.CTkLabel(brand_row, image=self.brand_icon_img, text="")
            self.brand_icon_lbl.pack(side="left", padx=(0, 10))

        brand_text_box = ctk.CTkFrame(brand_row, fg_color="transparent")
        brand_text_box.pack(side="left", fill="x", expand=True)

        logo_title = ctk.CTkLabel(
            brand_text_box,
            text="TUBE DOWNLOAD",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        logo_title.pack(anchor="w")

        logo_sub = ctk.CTkLabel(
            brand_text_box,
            text="JPRO CREATOR SUITE",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=NEON_CYAN_MID,
            anchor="w"
        )
        logo_sub.pack(anchor="w")

        sub_brand = ctk.CTkFrame(brand_frame, fg_color="transparent")
        sub_brand.pack(fill="x", pady=(8, 0))

        self.pro_badge = ctk.CTkLabel(
            sub_brand,
            text="FREE EDITION",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=("#64748B", "#475569"),
            text_color="white",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.pro_badge.pack(side="left")

        self.upgrade_btn = ctk.CTkButton(
            sub_brand,
            text="⭐ Upgrade",
            width=80,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self.open_pro_dialog
        )
        style_crown_gold_button(self.upgrade_btn)
        self.upgrade_btn.pack(side="left", padx=(6, 0))

        # Navigation Buttons
        self.btn_download = ctk.CTkButton(
            self.sidebar_frame,
            text="  📥  Single Downloader",
            height=42,
            corner_radius=10,
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.select_tab("downloader")
        )
        self.btn_download.pack(fill="x", padx=12, pady=3)

        self.btn_batch = ctk.CTkButton(
            self.sidebar_frame,
            text="  ⚡  Batch Shorts & Reels",
            height=42,
            corner_radius=10,
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.select_tab("batch")
        )
        self.btn_batch.pack(fill="x", padx=12, pady=3)

        self.btn_history = ctk.CTkButton(
            self.sidebar_frame,
            text="  📋  Queue & History",
            height=42,
            corner_radius=10,
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.select_tab("history")
        )
        self.btn_history.pack(fill="x", padx=12, pady=3)

        self.btn_settings = ctk.CTkButton(
            self.sidebar_frame,
            text="  ⚙  Settings",
            height=42,
            corner_radius=10,
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.select_tab("settings")
        )
        self.btn_settings.pack(fill="x", padx=12, pady=3)

        # Live Workstation Telemetry Card
        self.telemetry_card = ctk.CTkFrame(
            self.sidebar_frame,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        self.telemetry_card.pack(fill="x", padx=12, pady=(16, 8))

        telem_title = ctk.CTkLabel(
            self.telemetry_card,
            text="SYSTEM TELEMETRY",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray40", "#64748B"),
            anchor="w"
        )
        telem_title.pack(anchor="w", padx=12, pady=(8, 3))

        # Core Engine Status
        self.engine_status_label = ctk.CTkLabel(
            self.telemetry_card,
            text="● Core Engine: Ready",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#10B981",
            anchor="w"
        )
        self.engine_status_label.pack(anchor="w", padx=12, pady=(0, 2))

        # Live Speed Indicator
        self.speed_status_label = ctk.CTkLabel(
            self.telemetry_card,
            text="⚡ Speed: Idle",
            font=ctk.CTkFont(size=11),
            text_color=("gray30", "#94A3B8"),
            anchor="w"
        )
        self.speed_status_label.pack(anchor="w", padx=12, pady=(0, 2))

        # Total Completed Counter
        self.completed_count_label = ctk.CTkLabel(
            self.telemetry_card,
            text="✔ Completed: 0 videos",
            font=ctk.CTkFont(size=11),
            text_color=("gray30", "#94A3B8"),
            anchor="w"
        )
        self.completed_count_label.pack(anchor="w", padx=12, pady=(0, 2))

        # License Tier Indicator in Telemetry
        self.license_status_label = ctk.CTkLabel(
            self.telemetry_card,
            text="● License: Free Edition",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray40", "#64748B"),
            anchor="w"
        )
        self.license_status_label.pack(anchor="w", padx=12, pady=(0, 8))

        # Bottom System Info in Sidebar
        bottom_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=18, pady=20)

        # Supported platforms row
        plat_lbl = ctk.CTkLabel(
            bottom_frame,
            text="YouTube • TikTok • Reels",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray40", "#64748B"),
            anchor="w"
        )
        plat_lbl.pack(anchor="w", pady=(0, 6))

        # FFmpeg status dot
        has_ffmpeg = is_ffmpeg_available()
        dot_color = "#10B981" if has_ffmpeg else "#F59E0B"
        ffmpeg_text = "FFmpeg Engine Ready" if has_ffmpeg else "FFmpeg Missing"

        self.ffmpeg_indicator = ctk.CTkLabel(
            bottom_frame,
            text=f"● {ffmpeg_text}",
            font=ctk.CTkFont(size=11),
            text_color=dot_color,
            anchor="w"
        )
        self.ffmpeg_indicator.pack(anchor="w", pady=(0, 3))

        version_label = ctk.CTkLabel(
            bottom_frame,
            text="v1.3.0 Pro • Windows x64",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "#64748B"),
            anchor="w"
        )
        version_label.pack(anchor="w")

    def _build_views(self):
        # Container for main views
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_WINDOW_BG)
        self.main_container.grid(row=0, column=1, sticky="nsew")

        # Top Smart Clipboard Banner (hidden initially)
        self.clipboard_banner = ctk.CTkFrame(
            self.main_container,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=("#38BDF8", "#0284C7")
        )

        b_inner = ctk.CTkFrame(self.clipboard_banner, fg_color="transparent")
        b_inner.pack(fill="x", padx=14, pady=8)

        b_left = ctk.CTkFrame(b_inner, fg_color="transparent")
        b_left.pack(side="left", fill="x", expand=True)

        self.clip_title = ctk.CTkLabel(
            b_left,
            text="📋 Video Link Detected on Clipboard:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#0284C7", "#38BDF8")
        )
        self.clip_title.pack(anchor="w")

        self.clip_url_label = ctk.CTkLabel(
            b_left,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray30", "#94A3B8"),
            anchor="w"
        )
        self.clip_url_label.pack(anchor="w")

        b_right = ctk.CTkFrame(b_inner, fg_color="transparent")
        b_right.pack(side="right")

        single_btn = ctk.CTkButton(
            b_right,
            text="📥 Single Download",
            height=30,
            width=135,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_clip_single
        )
        style_neon_cyan_button(single_btn)
        single_btn.pack(side="left", padx=(0, 6))

        batch_btn = ctk.CTkButton(
            b_right,
            text="➕ Add to Batch",
            height=30,
            width=115,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_clip_batch
        )
        style_neon_emerald_button(batch_btn)
        batch_btn.pack(side="left", padx=(0, 6))

        dismiss_btn = ctk.CTkButton(
            b_right,
            text="✕",
            height=30,
            width=30,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.clipboard_banner.pack_forget()
        )
        style_glass_button(dismiss_btn)
        dismiss_btn.pack(side="left")

        # Swappable views container
        self.view_container = ctk.CTkFrame(self.main_container, corner_radius=0, fg_color=COLOR_WINDOW_BG)
        self.view_container.pack(fill="both", expand=True)

        # Create all views
        self.download_view = DownloadView(
            self.view_container,
            on_download_started=self._on_download_started
        )
        self.batch_view = BatchView(
            self.view_container,
            on_batch_started=self._on_batch_started
        )
        self.history_view = HistoryView(self.view_container)
        self.settings_view = SettingsView(
            self.view_container,
            on_theme_change=self._on_theme_changed
        )

    def select_tab(self, tab_name: str):
        unselected_fg = "transparent"
        selected_fg = ("#DBEAFE", "#0C2340")
        unselected_text = ("gray30", "#94A3B8")
        selected_text = ("#1D4ED8", "#38BDF8")

        tabs = [
            ("downloader", self.btn_download, self.download_view),
            ("batch", self.btn_batch, self.batch_view),
            ("history", self.btn_history, self.history_view),
            ("settings", self.btn_settings, self.settings_view),
        ]

        for name, btn, view in tabs:
            if name == tab_name:
                btn.configure(
                    fg_color=selected_fg,
                    text_color=selected_text,
                    border_width=1,
                    border_color=("#93C5FD", "#0284C7")
                )
                view.pack(fill="both", expand=True)
            else:
                btn.configure(
                    fg_color=unselected_fg,
                    text_color=unselected_text,
                    border_width=0
                )
                view.pack_forget()

    def _clipboard_loop(self):
        if config.get("clipboard_watcher", True):
            try:
                clip = self.clipboard_get().strip()
                if clip and clip != self.last_clipboard:
                    self.last_clipboard = clip
                    urls = extract_supported_urls(clip)
                    if urls:
                        self.detected_url = urls[0]
                        plat_name = get_platform_label(detect_platform(self.detected_url))
                        self.clip_title.configure(text=f"📋 {plat_name} Link Detected on Clipboard:")
                        disp = self.detected_url if len(self.detected_url) <= 60 else self.detected_url[:57] + "..."
                        self.clip_url_label.configure(text=disp)
                        self.clipboard_banner.pack(fill="x", padx=20, pady=(10, 0), before=self.view_container)
            except Exception:
                pass
        self.after(1500, self._clipboard_loop)

    def _on_clip_single(self):
        self.clipboard_banner.pack_forget()
        self.select_tab("downloader")
        if self.detected_url:
            self.download_view.url_entry.delete(0, "end")
            self.download_view.url_entry.insert(0, self.detected_url)
            self.download_view.on_fetch_clicked()

    def _on_clip_batch(self):
        self.clipboard_banner.pack_forget()
        self.select_tab("batch")
        if self.detected_url:
            self.batch_view.textbox.insert("end", "\n" + self.detected_url)
            self.batch_view._on_parse_links()

    def _on_download_started(self, task: DownloadTask):
        self._update_sidebar_queue_count()

    def _on_batch_started(self):
        self._update_sidebar_queue_count()

    def _on_theme_changed(self, theme: str):
        pass

    def _on_task_update(self, task: DownloadTask):
        self.after(0, self._update_sidebar_queue_count)

    def _update_sidebar_queue_count(self):
        all_tasks = list(download_manager.tasks.values())
        active_tasks = [t for t in all_tasks if t.status in ["queued", "downloading", "merging"]]
        active_downloading = [t for t in all_tasks if t.status in ["downloading", "merging"]]
        completed_count = sum(1 for t in all_tasks if t.status == "completed")

        if len(active_tasks) > 0:
            self.btn_history.configure(text=f"  📋  Queue & History ({len(active_tasks)})")
        else:
            self.btn_history.configure(text="  📋  Queue & History")

        # Telemetry updates
        if active_downloading:
            first_active = active_downloading[0]
            spd = first_active.speed_str if first_active.speed_str and first_active.speed_str != "-- MB/s" else "Active"
            self.engine_status_label.configure(text="● Core Engine: Active", text_color=("#2563EB", "#38BDF8"))
            self.speed_status_label.configure(text=f"⚡ Speed: {spd}", text_color=("#0284C7", "#38BDF8"))
        else:
            self.engine_status_label.configure(text="● Core Engine: Ready", text_color="#10B981")
            self.speed_status_label.configure(text="⚡ Speed: Idle", text_color=("gray40", "#64748B"))

        self.completed_count_label.configure(
            text=f"✔ Completed: {completed_count} video{'s' if completed_count != 1 else ''}"
        )

        has_ffmpeg = is_ffmpeg_available()
        dot_color = "#10B981" if has_ffmpeg else "#F59E0B"
        ffmpeg_text = "FFmpeg Engine Ready" if has_ffmpeg else "FFmpeg Missing"
        self.ffmpeg_indicator.configure(text=f"● {ffmpeg_text}", text_color=dot_color)

    def open_pro_dialog(self):
        ProDialog(self, on_activated=self._update_license_ui)

    def _update_license_ui(self, is_pro: Optional[bool] = None):
        if is_pro is None:
            is_pro = is_pro_active()

        if is_pro:
            info = get_license_info()
            tier_text = info.get("tier_label", "👑 PRO LIFETIME")
            self.pro_badge.configure(
                text=tier_text,
                fg_color=("#D97706", "#F59E0B"),
                text_color="#0F172A"
            )
            if self.upgrade_btn.winfo_ismapped():
                self.upgrade_btn.pack_forget()
            if hasattr(self, "license_status_label"):
                plan_name = info.get("plan_name", "Pro Edition")
                self.license_status_label.configure(text=f"● License: {plan_name}", text_color=("#D97706", "#F59E0B"))
        else:
            self.pro_badge.configure(
                text="FREE EDITION",
                fg_color=("#64748B", "#475569"),
                text_color="white"
            )
            if not self.upgrade_btn.winfo_ismapped():
                self.upgrade_btn.pack(side="left", padx=(6, 0))
            if hasattr(self, "license_status_label"):
                self.license_status_label.configure(text="● License: Free Edition", text_color=("gray40", "#64748B"))

