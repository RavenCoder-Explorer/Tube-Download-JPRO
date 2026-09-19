import os
import threading
from typing import List, Dict, Any, Optional, Callable
import customtkinter as ctk

from app.config import config
from app.downloader import (
    download_manager,
    DownloadTask,
    extract_supported_urls,
    expand_channel_shorts,
    detect_platform,
    get_platform_label,
    NAMING_TEMPLATES,
    execute_system_power_action
)
from app.ui.channel_scraper_dialog import ChannelScraperDialog
from app.license_manager import is_pro_active, register_license_callback
from app.ui.pro_dialog import ProDialog
from app.ui.theme import (
    COLOR_WINDOW_BG, COLOR_CARD_BG, COLOR_CARD_BORDER, COLOR_INPUT_BG, COLOR_INPUT_BORDER,
    NEON_CYAN, NEON_CYAN_MID, NEON_CYAN_DEEP, NEON_EMERALD, CROWN_GOLD,
    style_neon_cyan_button, style_neon_emerald_button, style_glass_button,
    style_danger_glass_button, style_card, style_input_entry
)


class BatchItemRow(ctk.CTkFrame):
    """A row representing an item in the batch download queue."""

    def __init__(self, master, index: int, url: str, title: Optional[str] = None, on_remove=None, **kwargs):
        super().__init__(
            master,
            corner_radius=10,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            **kwargs
        )
        self.index = index
        self.url = url
        self.title = title
        self.on_remove = on_remove
        self.task: Optional[DownloadTask] = None
        self.platform = detect_platform(url)

        self._build_ui()

    def set_index(self, index: int):
        self.index = index
        self.idx_lbl.configure(text=f"#{self.index:03d}")

    def _build_ui(self):
        self.pack_configure(fill="x", padx=6, pady=4)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)
        inner.grid_columnconfigure(2, weight=1)

        # Index label (001, 002, etc.)
        self.idx_lbl = ctk.CTkLabel(
            inner,
            text=f"#{self.index:03d}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#2563EB", "#60A5FA"),
            width=38
        )
        self.idx_lbl.grid(row=0, column=0, sticky="w")

        # Platform badge
        plat_colors = {
            "shorts": ("#EF4444", "white"),
            "youtube": ("#DC2626", "white"),
            "tiktok": ("#06B6D4", "#0F172A"),
            "instagram": ("#E1306C", "white"),
            "pinterest": ("#E60023", "white"),
            "other": ("#6B7280", "white")
        }
        bg_col, txt_col = plat_colors.get(self.platform, ("#6B7280", "white"))

        plat_badge = ctk.CTkLabel(
            inner,
            text=get_platform_label(self.platform).upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=bg_col,
            text_color=txt_col,
            corner_radius=4,
            padx=6,
            pady=2
        )
        plat_badge.grid(row=0, column=1, sticky="w", padx=(4, 10))

        # URL / Title text
        display_text = self.title if self.title else self.url
        if len(display_text) > 55:
            display_text = display_text[:52] + "..."

        self.text_label = ctk.CTkLabel(
            inner,
            text=display_text,
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.text_label.grid(row=0, column=2, sticky="ew", padx=(0, 10))

        # Mini Progress Bar
        self.pbar = ctk.CTkProgressBar(inner, width=120, height=8, corner_radius=4, progress_color=NEON_CYAN)
        self.pbar.set(0)
        self.pbar.grid(row=0, column=3, sticky="e", padx=(0, 10))

        # Status badge
        self.status_badge = ctk.CTkLabel(
            inner,
            text="Waiting",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#E2E8F0", "#1E293B"),
            text_color=("gray20", "gray80"),
            corner_radius=4,
            padx=8,
            pady=2,
            width=85
        )
        self.status_badge.grid(row=0, column=4, sticky="e", padx=(0, 8))

        # Right actions container
        self.btn_container = ctk.CTkFrame(inner, fg_color="transparent")
        self.btn_container.grid(row=0, column=5, sticky="e")

        self.play_btn = ctk.CTkButton(
            self.btn_container,
            text="▶ Play",
            width=65,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._play_file
        )
        style_neon_emerald_button(self.play_btn)

        self.folder_btn = ctk.CTkButton(
            self.btn_container,
            text="📁",
            width=28,
            height=26,
            font=ctk.CTkFont(size=11),
            command=self._open_folder
        )
        style_glass_button(self.folder_btn)

        self.del_btn = ctk.CTkButton(
            self.btn_container,
            text="✕",
            width=26,
            height=26,
            font=ctk.CTkFont(size=12),
            command=self._handle_remove
        )
        style_danger_glass_button(self.del_btn)
        self.del_btn.pack(side="left")

    def _play_file(self):
        if self.task and self.task.target_filepath and os.path.exists(self.task.target_filepath):
            try:
                os.startfile(self.task.target_filepath)
                return
            except Exception as e:
                print(f"Failed to play file: {e}")
        save_d = self.task.save_dir if self.task else config.download_dir
        if os.path.exists(save_d):
            os.startfile(save_d)

    def _open_folder(self):
        if self.task and self.task.target_filepath and os.path.exists(self.task.target_filepath):
            import subprocess
            subprocess.run(["explorer", "/select,", os.path.normpath(self.task.target_filepath)])
        else:
            save_d = self.task.save_dir if self.task else config.download_dir
            if os.path.exists(save_d):
                os.startfile(save_d)

    def _handle_remove(self):
        if self.on_remove:
            self.on_remove(self)

    def attach_task(self, task: DownloadTask):
        self.task = task
        self.update_progress(task)

    def update_progress(self, task: DownloadTask):
        pct = task.progress / 100.0
        self.pbar.set(min(1.0, max(0.0, pct)))

        if task.title and task.title != "Loading metadata...":
            dt = task.title
            if len(dt) > 55:
                dt = dt[:52] + "..."
            self.text_label.configure(text=dt)

        if task.status == "queued":
            self.status_badge.configure(text="Queued", fg_color=("#3B82F6", "#1D4ED8"), text_color="white")
            self.pbar.grid()
        elif task.status == "downloading":
            self.pbar.grid()
            self.status_badge.configure(text=f"{task.progress:.0f}%", fg_color="#2563EB", text_color="white")
        elif task.status == "merging":
            self.pbar.grid()
            self.status_badge.configure(text="Merging...", fg_color="#D97706", text_color="white")
        elif task.status == "completed":
            self.status_badge.configure(text="✔ Done", fg_color="#10B981", text_color="white")
            self.pbar.grid_remove()
            if not self.play_btn.winfo_ismapped():
                self.del_btn.pack_forget()
                self.play_btn.pack(side="left", padx=(0, 4))
                self.folder_btn.pack(side="left", padx=(0, 4))
                self.del_btn.pack(side="left")
        elif task.status == "cancelled":
            self.pbar.grid_remove()
            self.status_badge.configure(text="Cancelled", fg_color="#64748B", text_color="white")
        elif task.status == "error":
            self.pbar.grid_remove()
            err_short = task.error_message.split("\n")[-1] if "\n" in task.error_message else task.error_message
            if len(err_short) > 40:
                err_short = err_short[:37] + "..."
            self.status_badge.configure(text="Failed", fg_color="#EF4444", text_color="white")
            if err_short:
                self.text_label.configure(text=f"{self.text_label.cget('text')} ({err_short})")


class BatchView(ctk.CTkFrame):
    """Professional workspace for bulk downloading YouTube Shorts, TikToks, and Instagram Reels."""

    def __init__(self, master, on_batch_started: Optional[Callable] = None, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=COLOR_WINDOW_BG, **kwargs)
        self.on_batch_started = on_batch_started
        self.rows: List[BatchItemRow] = []
        self.task_map: Dict[str, BatchItemRow] = {}
        self.is_running = False

        self._build_ui()
        download_manager.register_callback(self._on_task_update)
        register_license_callback(lambda is_pro: self._populate_presets_menu())

    def _build_ui(self):
        # Header Box
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(16, 8))

        # Top row: Title on left, Badges on right
        top_row = ctk.CTkFrame(header, fg_color="transparent")
        top_row.pack(fill="x")

        title = ctk.CTkLabel(
            top_row,
            text="Batch Shorts & Reels Downloader",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(side="left")

        badges = ctk.CTkFrame(top_row, fg_color="transparent")
        badges.pack(side="right")

        b_shorts = ctk.CTkLabel(
            badges,
            text="YouTube",
            fg_color="#EF4444",
            text_color="white",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=7,
            pady=2
        )
        b_shorts.pack(side="left", padx=2)

        b_tiktok = ctk.CTkLabel(
            badges,
            text="TikTok",
            fg_color="#06B6D4",
            text_color="#0F172A",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=7,
            pady=2
        )
        b_tiktok.pack(side="left", padx=2)

        b_reels = ctk.CTkLabel(
            badges,
            text="Instagram",
            fg_color="#E1306C",
            text_color="white",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=7,
            pady=2
        )
        b_reels.pack(side="left", padx=2)

        b_pin = ctk.CTkLabel(
            badges,
            text="Pinterest",
            fg_color="#E60023",
            text_color="white",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=7,
            pady=2
        )
        b_pin.pack(side="left", padx=2)

        # Subtitle row underneath
        subtitle = ctk.CTkLabel(
            header,
            text="Bulk download dozens of YouTube Shorts, TikToks, Instagram Reels, and Pinterest Pins at once",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8"),
            anchor="w"
        )
        subtitle.pack(fill="x", pady=(3, 0))

        # Multi-URL Input Box Card
        input_card = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        input_card.pack(fill="x", padx=30, pady=(5, 10))

        input_header = ctk.CTkFrame(input_card, fg_color="transparent")
        input_header.pack(fill="x", padx=16, pady=(12, 6))

        in_title = ctk.CTkLabel(
            input_header,
            text="Paste Multiple Links or Channel / Shorts URLs",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        in_title.pack(side="left")

        # Text Area for Links
        self.textbox = ctk.CTkTextbox(
            input_card,
            height=85,
            font=ctk.CTkFont(size=12),
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            border_width=1,
            border_color=COLOR_INPUT_BORDER
        )
        self.textbox.pack(fill="x", padx=16, pady=(0, 10))

        # Action Buttons below textbox
        btn_bar = ctk.CTkFrame(input_card, fg_color="transparent")
        btn_bar.pack(fill="x", padx=16, pady=(0, 12))

        paste_btn = ctk.CTkButton(
            btn_bar,
            text="📋 Paste Clipboard",
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_paste_clipboard
        )
        style_glass_button(paste_btn)
        paste_btn.pack(side="left", padx=(0, 8))

        parse_btn = ctk.CTkButton(
            btn_bar,
            text="➕ Parse & Add Links",
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_parse_links
        )
        style_neon_emerald_button(parse_btn)
        parse_btn.pack(side="left", padx=(0, 8))

        scraper_btn = ctk.CTkButton(
            btn_bar,
            text="🔍 Channel Scraper",
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._open_channel_scraper
        )
        style_neon_cyan_button(scraper_btn)
        scraper_btn.pack(side="left", padx=(0, 8))

        import_file_btn = ctk.CTkButton(
            btn_bar,
            text="📁 Import .txt",
            height=34,
            width=95,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_import_file
        )
        style_glass_button(import_file_btn)
        import_file_btn.pack(side="left", padx=(0, 8))

        clear_in_btn = ctk.CTkButton(
            btn_bar,
            text="Clear Input",
            height=34,
            width=85,
            font=ctk.CTkFont(size=12),
            command=lambda: self.textbox.delete("1.0", "end")
        )
        style_glass_button(clear_in_btn)
        clear_in_btn.pack(side="right")

        # Batch Settings Toolbar Card
        settings_card = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray90", "#1E293B"))
        settings_card.pack(fill="x", padx=30, pady=(0, 10))

        # Row 1: Quality Preset, Naming Format, and Start #
        r1 = ctk.CTkFrame(settings_card, fg_color="transparent")
        r1.pack(fill="x", padx=16, pady=(8, 4))

        m_lbl = ctk.CTkLabel(r1, text="Preset:", font=ctk.CTkFont(size=12, weight="bold"))
        m_lbl.pack(side="left", padx=(0, 6))

        self.preset_menu = ctk.CTkOptionMenu(
            r1,
            values=[
                "🎬 Video: Best Quality (Max 720p)",
                "👑 Video: 1080p Full HD (Pro Only)",
                "🎬 Video: 720p HD",
                "🎵 Audio: MP3 192k Standard"
            ],
            width=240,
            height=30,
            command=self._on_preset_selected
        )
        self.preset_menu.pack(side="left", padx=(0, 14))
        self._populate_presets_menu()

        name_lbl = ctk.CTkLabel(r1, text="Naming:", font=ctk.CTkFont(size=12, weight="bold"))
        name_lbl.pack(side="left", padx=(0, 6))

        self.naming_menu = ctk.CTkOptionMenu(
            r1,
            values=list(NAMING_TEMPLATES.keys()),
            command=lambda val: config.set("naming_template", val),
            width=180,
            height=30
        )
        cur_naming = config.get("naming_template", "Title + ID (Default)")
        if cur_naming not in NAMING_TEMPLATES:
            cur_naming = "Title + ID (Default)"
        self.naming_menu.set(cur_naming)
        self.naming_menu.pack(side="left", padx=(0, 14))

        start_lbl = ctk.CTkLabel(r1, text="Start #:", font=ctk.CTkFont(size=12, weight="bold"))
        start_lbl.pack(side="left", padx=(0, 6))

        self.start_num_entry = ctk.CTkEntry(
            r1,
            width=50,
            height=30,
            justify="center",
            font=ctk.CTkFont(size=12)
        )
        self.start_num_entry.insert(0, "1")
        self.start_num_entry.pack(side="left")
        self.start_num_entry.bind("<KeyRelease>", lambda e: self._reindex_rows())

        # Row 2: Speed Limit, Post-Batch Power Action, and Save Destination
        r2 = ctk.CTkFrame(settings_card, fg_color="transparent")
        r2.pack(fill="x", padx=16, pady=(4, 8))

        spd_lbl = ctk.CTkLabel(r2, text="Speed:", font=ctk.CTkFont(size=12, weight="bold"))
        spd_lbl.pack(side="left", padx=(0, 6))

        speed_options = ["Unlimited", "25 MB/s", "15 MB/s", "10 MB/s", "5 MB/s", "2 MB/s"]
        cur_spd = config.get("speed_limit", "Unlimited")
        if cur_spd not in speed_options:
            cur_spd = "Unlimited"

        self.speed_menu = ctk.CTkOptionMenu(
            r2,
            values=speed_options,
            command=lambda val: config.set("speed_limit", val),
            width=110,
            height=28
        )
        self.speed_menu.set(cur_spd)
        self.speed_menu.pack(side="left", padx=(0, 14))

        act_lbl = ctk.CTkLabel(r2, text="On Finish:", font=ctk.CTkFont(size=12, weight="bold"))
        act_lbl.pack(side="left", padx=(0, 6))

        self.post_action_menu = ctk.CTkOptionMenu(
            r2,
            values=["None", "Sleep PC", "Shutdown PC"],
            width=110,
            height=28
        )
        self.post_action_menu.set("None")
        self.post_action_menu.pack(side="left", padx=(0, 14))

        dest_lbl = ctk.CTkLabel(r2, text="Save to:", font=ctk.CTkFont(size=12, weight="bold"))
        dest_lbl.pack(side="left", padx=(0, 6))

        self.dest_label = ctk.CTkLabel(
            r2,
            text=config.download_dir,
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "#94A3B8"),
            anchor="w"
        )
        self.dest_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        change_dir_btn = ctk.CTkButton(
            r2,
            text="Browse...",
            width=80,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_browse_folder
        )
        style_glass_button(change_dir_btn)
        change_dir_btn.pack(side="right")

        # Bottom Batch Control & Overall Progress Bar (Docked to bottom so it is never pushed off-screen)
        bottom_bar = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        bottom_bar.pack(side="bottom", fill="x", padx=30, pady=(10, 15))

        bb_inner = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        bb_inner.pack(fill="x", padx=16, pady=10)

        # Left: Overall progress text and bar
        prog_col = ctk.CTkFrame(bb_inner, fg_color="transparent")
        prog_col.pack(side="left", fill="x", expand=True, padx=(0, 16))

        self.overall_label = ctk.CTkLabel(
            prog_col,
            text="Overall Progress: Ready",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        self.overall_label.pack(fill="x", pady=(0, 4))

        self.overall_pbar = ctk.CTkProgressBar(prog_col, height=10, corner_radius=5, progress_color=NEON_EMERALD)
        self.overall_pbar.set(0)
        self.overall_pbar.pack(fill="x")

        # Right: Big Action Button
        self.start_btn = ctk.CTkButton(
            bb_inner,
            text="🚀  Download All Batch",
            height=44,
            width=210,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_start_batch
        )
        style_neon_emerald_button(self.start_btn)
        self.start_btn.pack(side="right")

        # Batch Queue Table Header & List (Expands to fill all remaining vertical space)
        table_card = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        table_card.pack(fill="both", expand=True, padx=30, pady=(0, 0))

        t_head = ctk.CTkFrame(table_card, fg_color="transparent")
        t_head.pack(fill="x", padx=16, pady=(10, 5))

        self.queue_count_lbl = ctk.CTkLabel(
            t_head,
            text="Batch Queue: 0 items",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.queue_count_lbl.pack(side="left")

        clear_q_btn = ctk.CTkButton(
            t_head,
            text="Clear Queue",
            width=90,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_clear_queue
        )
        style_danger_glass_button(clear_q_btn)
        clear_q_btn.pack(side="right")

        # Filter & Search Toolbar
        filter_bar = ctk.CTkFrame(table_card, fg_color="transparent")
        filter_bar.pack(fill="x", padx=16, pady=(0, 8))

        self.filter_segmented = ctk.CTkSegmentedButton(
            filter_bar,
            values=["All", "YouTube", "TikTok", "Instagram", "Pinterest"],
            command=lambda v: self._apply_filter(),
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            selected_color=NEON_CYAN_DEEP,
            selected_hover_color=NEON_CYAN_MID,
            unselected_color=("#E2E8F0", "#1E293B")
        )
        self.filter_segmented.set("All")
        self.filter_segmented.pack(side="left")

        self.search_entry = ctk.CTkEntry(
            filter_bar,
            placeholder_text="🔍 Filter queue by title or link...",
            width=240,
            height=28,
            font=ctk.CTkFont(size=11)
        )
        style_input_entry(self.search_entry)
        self.search_entry.pack(side="right")
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filter())

        # Scrollable items frame
        self.items_scroll = ctk.CTkScrollableFrame(table_card, fg_color=COLOR_CARD_BG)
        self.items_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.empty_batch_lbl = ctk.CTkLabel(
            self.items_scroll,
            text="No items in batch queue.\nPaste links or channel URLs above and click 'Parse & Add Links'.",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "#64748B")
        )
        self.empty_batch_lbl.pack(pady=40)

    def _populate_presets_menu(self):
        if not hasattr(self, "preset_menu"):
            return
        pro = is_pro_active()
        if pro:
            vals = [
                "🎬 Video: Best Quality (Up to 4K/8K)",
                "🎬 Video: 1080p Full HD",
                "🎬 Video: 720p HD",
                "🎵 Audio: MP3 320k High Quality",
                "🖼 Photos & Images: Original HD"
            ]
            def_val = "🎬 Video: Best Quality (Up to 4K/8K)"
        else:
            vals = [
                "🎬 Video: Best Quality (Max 720p)",
                "👑 Video: 1080p Full HD (Pro Only)",
                "👑 Video: 4K / 2K Ultra HD (Pro Only)",
                "🎬 Video: 720p HD",
                "🎵 Audio: MP3 192k Standard",
                "👑 Audio: MP3 320k (Pro Only)",
                "🖼 Photos & Images: Original HD"
            ]
            def_val = "🎬 Video: Best Quality (Max 720p)"

        self.preset_menu.configure(values=vals)
        cur = self.preset_menu.get()
        if cur in vals and (pro or "👑" not in cur):
            self.preset_menu.set(cur)
        else:
            self.preset_menu.set(def_val)

    def _on_preset_selected(self, val: str):
        if "👑" in val or "Pro Only" in val:
            ProDialog(self.winfo_toplevel())
            if "1080p" in val or "Video" in val or "4K" in val:
                self.overall_label.configure(
                    text="👑 1080p Full HD & 4K require Pro Edition. Upgrade to unlock!",
                    text_color="#F59E0B"
                )
                self.preset_menu.set("🎬 Video: Best Quality (Max 720p)")
            else:
                self.overall_label.configure(
                    text="👑 320kbps High Fidelity audio requires Pro Edition. Upgrade to unlock!",
                    text_color="#F59E0B"
                )
                self.preset_menu.set("🎵 Audio: MP3 192k Standard")

    def _on_paste_clipboard(self):
        try:
            txt = self.clipboard_get().strip()
            if txt:
                self.textbox.insert("end", "\n" + txt)
        except Exception:
            pass

    def _on_import_file(self):
        file_path = ctk.filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    self.textbox.insert("end", "\n" + content)
            except Exception as e:
                print(f"Failed to read file: {e}")

    def _on_browse_folder(self):
        folder = ctk.filedialog.askdirectory(initialdir=config.download_dir)
        if folder:
            config.download_dir = folder
            self.dest_label.configure(text=folder)

    def _on_parse_links(self):
        raw_text = self.textbox.get("1.0", "end").strip()
        if not raw_text:
            self.overall_label.configure(
                text="⚠ Textbox is empty. Please paste your video links first.",
                text_color="#F59E0B"
            )
            return

        urls = extract_supported_urls(raw_text)
        if not urls:
            self.overall_label.configure(
                text="⚠ No supported links found. Ensure links are YouTube, TikTok, Instagram, or Pinterest.",
                text_color="#EF4444"
            )
            return

        # Check if any URL is a channel /shorts link needing expansion
        channel_urls = [u for u in urls if "/shorts" in u and "@" in u]

        def _expand_worker():
            final_urls = []
            for u in urls:
                if "/shorts" in u and "@" in u:
                    expanded = expand_channel_shorts(u, max_items=50)
                    if expanded:
                        final_urls.extend(expanded)
                    else:
                        final_urls.append(u)
                else:
                    final_urls.append(u)

            self.after(0, lambda: self._add_urls_to_queue(final_urls))

        if channel_urls:
            self.overall_label.configure(text="⏳ Scanning channel shorts...", text_color=("#1f6aa5", "#38BDF8"))
            threading.Thread(target=_expand_worker, daemon=True).start()
        else:
            self._add_urls_to_queue(urls)

    def _add_urls_to_queue(self, items: List[Any]):
        existing_urls = {r.url for r in self.rows}
        new_items = []
        for item in items:
            if isinstance(item, (tuple, list)):
                u = item[0]
                t = item[1] if len(item) > 1 else None
            else:
                u = str(item)
                t = None
            if u not in existing_urls:
                new_items.append((u, t))
                existing_urls.add(u)

        if not new_items:
            self.overall_label.configure(
                text="Notice: Selected links are already present in the queue.",
                text_color="#38BDF8"
            )
            return

        # Pro Feature Gate: Max 5 items per batch in Free Edition
        if not is_pro_active():
            allowed = max(0, 5 - len(self.rows))
            if allowed == 0:
                ProDialog(self.winfo_toplevel())
                self.overall_label.configure(
                    text="👑 Free Edition is limited to 5 batch items. Upgrade to Pro for unlimited links!",
                    text_color="#F59E0B"
                )
                return
            elif len(new_items) > allowed:
                ProDialog(self.winfo_toplevel())
                new_items = new_items[:allowed]
                self.overall_label.configure(
                    text="👑 Added first 5 items (Free limit). Upgrade to Pro for unlimited batch downloading!",
                    text_color="#F59E0B"
                )

        if self.empty_batch_lbl.winfo_ismapped():
            self.empty_batch_lbl.pack_forget()

        start_num = 1
        try:
            start_num = int(self.start_num_entry.get().strip())
        except Exception:
            start_num = 1

        for u, t in new_items:
            idx = start_num + len(self.rows)
            row = BatchItemRow(
                self.items_scroll,
                index=idx,
                url=u,
                title=t,
                on_remove=self._remove_row
            )
            self.rows.append(row)

        self._update_counts()
        self.textbox.delete("1.0", "end")
        self.overall_label.configure(
            text=f"✔ Added {len(new_items)} link(s) to batch queue. Ready to download!",
            text_color="#10B981"
        )

    def _reindex_rows(self):
        start_num = 1
        try:
            start_num = int(self.start_num_entry.get().strip())
        except Exception:
            start_num = 1

        for i, r in enumerate(self.rows, start=start_num):
            r.set_index(i)

    def _remove_row(self, row: BatchItemRow):
        if row in self.rows:
            self.rows.remove(row)
            row.destroy()
            self._reindex_rows()
            self._update_counts()

    def _on_clear_queue(self):
        for r in self.rows:
            r.destroy()
        self.rows.clear()
        self.task_map.clear()
        self._update_counts()

    def _apply_filter(self):
        query = self.search_entry.get().strip().lower()
        selected_plat = self.filter_segmented.get()

        visible_count = 0
        for r in self.rows:
            plat_match = (
                selected_plat == "All" or
                (selected_plat == "YouTube" and r.platform in ["youtube", "shorts"]) or
                (selected_plat == "TikTok" and r.platform == "tiktok") or
                (selected_plat == "Instagram" and r.platform == "instagram") or
                (selected_plat == "Pinterest" and r.platform == "pinterest")
            )
            search_target = f"{r.title or ''} {r.url}".lower()
            search_match = not query or query in search_target

            if plat_match and search_match:
                if r.winfo_manager() != "pack":
                    r.pack(fill="x", padx=6, pady=4)
                visible_count += 1
            else:
                if r.winfo_manager() == "pack":
                    r.pack_forget()

        total = len(self.rows)
        if total == 0:
            self.empty_batch_lbl.configure(
                text="No items in batch queue.\nPaste links or channel URLs above and click 'Parse & Add Links'."
            )
            if self.empty_batch_lbl.winfo_manager() != "pack":
                self.empty_batch_lbl.pack(pady=40)
            self.queue_count_lbl.configure(text="Batch Queue: 0 items")
        elif visible_count == 0:
            self.empty_batch_lbl.configure(
                text="No items match your filter.\nTry selecting 'All' or clearing the search."
            )
            if self.empty_batch_lbl.winfo_manager() != "pack":
                self.empty_batch_lbl.pack(pady=40)
            self.queue_count_lbl.configure(text=f"Batch Queue: {total} items (0 shown)")
        else:
            if self.empty_batch_lbl.winfo_manager() == "pack":
                self.empty_batch_lbl.pack_forget()
            if selected_plat != "All" or query:
                self.queue_count_lbl.configure(text=f"Batch Queue: {total} items ({visible_count} shown)")
            else:
                self.queue_count_lbl.configure(text=f"Batch Queue: {total} item{'s' if total != 1 else ''}")

    def _update_counts(self):
        total = len(self.rows)
        self._apply_filter()
        if total == 0:
            self.overall_label.configure(text="Overall Progress: Ready", text_color=("gray40", "#94A3B8"))
            self.overall_pbar.set(0)
        else:
            done_count = sum(1 for r in self.rows if r.task and r.task.status == "completed")
            err_count = sum(1 for r in self.rows if r.task and r.task.status == "error")
            pct = (done_count / total) if total > 0 else 0
            self.overall_pbar.set(pct)
            status_text = f"Completed {done_count} of {total} items ({pct * 100:.0f}%)"
            if err_count > 0:
                status_text += f" • {err_count} failed"
            self.overall_label.configure(text=status_text, text_color=("black", "white"))

    def _on_start_batch(self):
        # 1. Automatically parse links if user pasted into textbox without clicking Parse first
        raw_text = self.textbox.get("1.0", "end").strip()
        if raw_text:
            urls = extract_supported_urls(raw_text)
            if urls:
                self._add_urls_to_queue(urls)
                self.textbox.delete("1.0", "end")

        # 2. Check if batch queue is empty
        if not self.rows:
            self.overall_label.configure(
                text="⚠ Please paste or add at least one video, Shorts, Reels, or Pinterest link first!",
                text_color="#EF4444"
            )
            return

        # Pro Feature Gate: Max 5 items in Free Edition
        if not is_pro_active() and len(self.rows) > 5:
            ProDialog(self.winfo_toplevel())
            self.overall_label.configure(
                text="👑 Batch queues with more than 5 items require Pro Edition. Upgrade to unlock!",
                text_color="#F59E0B"
            )
            return

        preset = self.preset_menu.get()
        if "👑" in preset or "Pro Only" in preset:
            ProDialog(self.winfo_toplevel())
            self.overall_label.configure(
                text="👑 320kbps High Fidelity audio requires Pro Edition. Upgrade to unlock!",
                text_color="#F59E0B"
            )
            return

        if "Audio" in preset:
            mode = "audio"
        elif "Image" in preset or "Photo" in preset:
            mode = "image"
        else:
            mode = "video"

        resolution = "Best Quality"
        if not is_pro_active():
            resolution = "720p (HD)"
        elif "1080p" in preset:
            resolution = "1080p (Full HD)"
        elif "720p" in preset:
            resolution = "720p (HD)"

        audio_bitrate = "320k" if (is_pro_active() and "320k" in preset) else "192k"

        save_dir = config.download_dir

        # 3. Find pending rows that are not currently running or done
        pending_rows = [
            r for r in self.rows
            if not r.task or r.task.status not in ["completed", "downloading", "merging"]
        ]

        # If all items were completed or failed previously, allow retry of failed ones
        if not pending_rows:
            failed_rows = [r for r in self.rows if r.task and r.task.status in ["error", "cancelled"]]
            if failed_rows:
                pending_rows = failed_rows
            else:
                self.overall_label.configure(
                    text="✔ All items in queue have already been downloaded!",
                    text_color="#10B981"
                )
                return

        self.start_btn.configure(state="disabled", text="⏳ Batch Running...")
        self.is_running = True
        self.overall_label.configure(
            text=f"🚀 Starting batch download for {len(pending_rows)} item(s)...",
            text_color=("#1f6aa5", "#38BDF8")
        )

        self._reindex_rows()

        s_limit = self.speed_menu.get()
        img_fmt = config.get("image_format", "original")
        for row in pending_rows:
            task = download_manager.add_task(
                url=row.url,
                title=getattr(row, "title", "") or "",
                platform=row.platform,
                mode=mode,
                resolution=resolution,
                audio_format="mp3",
                audio_bitrate=audio_bitrate,
                image_format=img_fmt,
                save_dir=save_dir,
                naming_template=self.naming_menu.get(),
                order_num=row.index,
                speed_limit=s_limit
            )
            self.task_map[task.task_id] = row
            row.attach_task(task)

        self._update_counts()
        if self.on_batch_started:
            self.on_batch_started()

    def _open_channel_scraper(self):
        ChannelScraperDialog(self, on_add_links=self._on_links_scraped)

    def _on_links_scraped(self, items: List[Any]):
        if not items:
            return
        self._add_urls_to_queue(items)
        self.overall_label.configure(
            text=f"✔ Added {len(items)} clip(s) from Channel Scraper to batch queue.",
            text_color="#10B981"
        )

    def _on_task_update(self, task: DownloadTask):
        self.after(0, lambda: self._handle_task_update(task))

    def _handle_task_update(self, task: DownloadTask):
        row = self.task_map.get(task.task_id)
        if row:
            row.update_progress(task)
            self._update_counts()

        # Check if all completed
        if self.is_running and self.rows:
            all_done = all(
                r.task and r.task.status in ["completed", "error", "cancelled"]
                for r in self.rows
            )
            if all_done:
                self.is_running = False
                self.start_btn.configure(state="normal", text="🚀 Download All Batch")
                post_action = self.post_action_menu.get()
                if post_action in ["Sleep PC", "Shutdown PC"]:
                    self.overall_label.configure(
                        text=f"✔ Batch Complete! System will execute {post_action} in 10 seconds...",
                        text_color="#F59E0B"
                    )
                    self.after(10000, lambda: execute_system_power_action(post_action))
