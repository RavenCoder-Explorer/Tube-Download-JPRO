import io
import os
import threading
from typing import Optional, Callable
import requests
from PIL import Image
import customtkinter as ctk

from app.config import config
from app.downloader import fetch_video_metadata, download_manager, VideoInfo, detect_platform, get_platform_label, NAMING_TEMPLATES
from app.ffmpeg_helper import is_ffmpeg_available
from app.license_manager import is_pro_active, register_license_callback
from app.ui.pro_dialog import ProDialog
from app.ui.theme import (
    COLOR_WINDOW_BG, COLOR_CARD_BG, COLOR_CARD_BORDER, COLOR_INPUT_BG, COLOR_INPUT_BORDER,
    NEON_CYAN, NEON_CYAN_MID, NEON_CYAN_DEEP, NEON_EMERALD, CROWN_GOLD,
    style_neon_cyan_button, style_neon_emerald_button, style_glass_button,
    style_danger_glass_button, style_card, style_input_entry
)


class DownloadView(ctk.CTkFrame):
    """Professional single video downloader panel for Tube Download JPRO."""

    def __init__(self, master, on_download_started: Optional[Callable] = None, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=COLOR_WINDOW_BG, **kwargs)
        self.on_download_started = on_download_started
        self.current_video_info: Optional[VideoInfo] = None
        self.thumbnail_image: Optional[ctk.CTkImage] = None
        self.raw_thumbnail_bytes: Optional[bytes] = None

        self._build_ui()
        register_license_callback(lambda is_pro: self._refresh_quality_options())

    def _build_ui(self):
        # Header title
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(16, 8))

        # Top row: Title on left, Badges on right
        top_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        top_row.pack(fill="x")

        title_label = ctk.CTkLabel(
            top_row,
            text="Media Downloader Pro",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(side="left")

        # Badges
        badges_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        badges_frame.pack(side="right")

        yt_badge = ctk.CTkLabel(
            badges_frame,
            text="YouTube",
            fg_color="#EF4444",
            text_color="white",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=7,
            pady=2
        )
        yt_badge.pack(side="left", padx=2)

        tt_badge = ctk.CTkLabel(
            badges_frame,
            text="TikTok",
            fg_color="#06B6D4",
            text_color="#0F172A",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=7,
            pady=2
        )
        tt_badge.pack(side="left", padx=2)

        ig_badge = ctk.CTkLabel(
            badges_frame,
            text="Instagram",
            fg_color="#E1306C",
            text_color="white",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=7,
            pady=2
        )
        ig_badge.pack(side="left", padx=2)

        pin_badge = ctk.CTkLabel(
            badges_frame,
            text="Pinterest",
            fg_color="#E60023",
            text_color="white",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=7,
            pady=2
        )
        pin_badge.pack(side="left", padx=2)

        # Subtitle row underneath spanning full width
        sub_label = ctk.CTkLabel(
            header_frame,
            text="Download individual YouTube videos, Shorts, TikToks, Instagram Reels, and Pinterest in full fidelity",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8"),
            anchor="w"
        )
        sub_label.pack(fill="x", pady=(3, 0))

        # URL Input Card (Obsidian glass styling)
        url_container = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        url_container.pack(fill="x", padx=30, pady=(5, 8))

        url_inner = ctk.CTkFrame(url_container, fg_color="transparent")
        url_inner.pack(fill="x", padx=16, pady=12)

        self.url_entry = ctk.CTkEntry(
            url_inner,
            placeholder_text="Paste YouTube, TikTok, Instagram Reel, or Pinterest link here...",
            height=44,
            font=ctk.CTkFont(size=13),
            corner_radius=8
        )
        style_input_entry(self.url_entry)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self.on_fetch_clicked())

        self.paste_btn = ctk.CTkButton(
            url_inner,
            text="📋 Paste",
            width=90,
            height=44,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.on_paste_clicked
        )
        style_glass_button(self.paste_btn)
        self.paste_btn.pack(side="left", padx=(0, 8))

        self.fetch_btn = ctk.CTkButton(
            url_inner,
            text="🔍 Analyze",
            width=100,
            height=44,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.on_fetch_clicked
        )
        style_neon_cyan_button(self.fetch_btn)
        self.fetch_btn.pack(side="left")

        self.clear_url_btn = ctk.CTkButton(
            url_inner,
            text="✕ Clear",
            width=80,
            height=44,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.on_clear_video
        )
        style_glass_button(self.clear_url_btn)
        self.clear_url_btn.pack(side="left", padx=(8, 0))

        # Feedback/Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8")
        )
        self.status_label.pack(fill="x", padx=35, pady=(0, 4))

        # Action Button Frame (Docked to bottom edge so it is never pushed off-screen)
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(side="bottom", fill="x", padx=30, pady=(8, 14))

        self.download_button = ctk.CTkButton(
            action_frame,
            text="⬇  Start Download",
            height=46,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.on_download_clicked
        )
        style_neon_emerald_button(self.download_button)
        self.download_button.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.reset_button = ctk.CTkButton(
            action_frame,
            text="✕ Remove Video",
            height=46,
            width=150,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.on_clear_video
        )
        style_danger_glass_button(self.reset_button)
        self.reset_button.pack(side="right")

        # Main Scrollable Content Area for Preview and Options (Fills remaining space)
        self.content_scroll = ctk.CTkScrollableFrame(self, fg_color=COLOR_WINDOW_BG)
        self.content_scroll.pack(fill="both", expand=True, padx=25, pady=(0, 6))

        # Preview Card (Hidden initially until video is loaded)
        self.preview_card = ctk.CTkFrame(
            self.content_scroll,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )

        # Thumbnail container with overlay badges
        self.thumb_container = ctk.CTkFrame(
            self.preview_card,
            width=220,
            height=135,
            corner_radius=8,
            fg_color=("gray80", "#0F172A")
        )
        self.thumb_container.pack_propagate(False)
        self.thumb_container.pack(side="left", padx=16, pady=16)

        self.thumb_label = ctk.CTkLabel(
            self.thumb_container,
            text="No Preview",
            width=220,
            height=135,
            corner_radius=8,
            fg_color=("gray80", "#0F172A")
        )
        self.thumb_label.place(relx=0.5, rely=0.5, anchor="center")

        # Top-left chip (Quality / Resolution badge)
        self.thumb_badge_res = ctk.CTkLabel(
            self.thumb_container,
            text="HD",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=("#2563EB", "#1D4ED8"),
            text_color="white",
            corner_radius=4,
            padx=6,
            pady=2
        )

        # Bottom-right chip (Duration badge)
        self.thumb_badge_time = ctk.CTkLabel(
            self.thumb_container,
            text="⏱ 00:00",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=("#111827", "#000000"),
            text_color="white",
            corner_radius=4,
            padx=6,
            pady=2
        )

        # Action buttons top-right (Save Thumbnail & Remove Video)
        card_actions = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        card_actions.pack(side="right", anchor="ne", padx=16, pady=16)

        self.save_thumb_btn = ctk.CTkButton(
            card_actions,
            text="🖼 Save Thumbnail",
            width=135,
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.on_save_thumbnail_clicked
        )
        style_neon_cyan_button(self.save_thumb_btn)
        self.save_thumb_btn.pack(side="left", padx=(0, 8))

        self.remove_preview_btn = ctk.CTkButton(
            card_actions,
            text="✕ Remove Video",
            width=120,
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.on_clear_video
        )
        style_danger_glass_button(self.remove_preview_btn)
        self.remove_preview_btn.pack(side="left")

        # Video info middle
        info_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=16)

        self.video_title_label = ctk.CTkLabel(
            info_frame,
            text="Video Title Placeholder",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
            wraplength=480,
            justify="left"
        )
        self.video_title_label.pack(fill="x", pady=(0, 4))

        self.uploader_label = ctk.CTkLabel(
            info_frame,
            text="Channel / Creator",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "#94A3B8"),
            anchor="w"
        )
        self.uploader_label.pack(fill="x", pady=(0, 8))

        stats_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        stats_row.pack(fill="x")

        self.duration_badge = ctk.CTkLabel(
            stats_row,
            text="⏱ 00:00",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("gray80", "#334155"),
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.duration_badge.pack(side="left", padx=(0, 8))

        self.views_badge = ctk.CTkLabel(
            stats_row,
            text="👁 0 views",
            font=ctk.CTkFont(size=11),
            fg_color=("gray80", "#334155"),
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.views_badge.pack(side="left", padx=(0, 8))

        self.platform_badge = ctk.CTkLabel(
            stats_row,
            text="Platform",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("gray80", "#334155"),
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.platform_badge.pack(side="left")

        # Download Configuration Panel (Options)
        self.options_card = ctk.CTkFrame(
            self.content_scroll,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )

        opt_title = ctk.CTkLabel(
            self.options_card,
            text="Download Configuration",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        opt_title.pack(anchor="w", padx=20, pady=(15, 8))

        # Mode Selection: Video vs Audio
        mode_row = ctk.CTkFrame(self.options_card, fg_color="transparent")
        mode_row.pack(fill="x", padx=20, pady=5)

        mode_lbl = ctk.CTkLabel(mode_row, text="Format Type:", width=120, anchor="w", font=ctk.CTkFont(size=13))
        mode_lbl.pack(side="left")

        self.mode_segmented = ctk.CTkSegmentedButton(
            mode_row,
            values=["🎬 Video (MP4)", "🎵 Audio (MP3)", "🖼 Image (HD)"],
            command=self._on_mode_changed,
            height=32,
            selected_color=NEON_CYAN_DEEP,
            selected_hover_color=NEON_CYAN_MID,
            unselected_color=("#E2E8F0", "#1E293B")
        )
        self.mode_segmented.set("🎬 Video (MP4)")
        self.mode_segmented.pack(side="left", fill="x", expand=True)

        # Resolution Row (for Video)
        self.res_row = ctk.CTkFrame(self.options_card, fg_color="transparent")
        self.res_row.pack(fill="x", padx=20, pady=6)

        self.res_label = ctk.CTkLabel(self.res_row, text="Resolution:", width=120, anchor="w", font=ctk.CTkFont(size=13))
        self.res_label.pack(side="left")

        self.res_menu = ctk.CTkOptionMenu(
            self.res_row,
            values=["Best Quality (Max 720p HD)", "720p (HD)", "480p", "360p"],
            width=270,
            height=32,
            command=self._on_resolution_selected
        )
        self.res_menu.pack(side="left")
        self._populate_resolution_menu()

        # Audio Quality Row (for Audio Mode)
        self.audio_row = ctk.CTkFrame(self.options_card, fg_color="transparent")

        self.audio_format_lbl = ctk.CTkLabel(self.audio_row, text="Audio Format:", width=120, anchor="w", font=ctk.CTkFont(size=13))
        self.audio_format_lbl.pack(side="left")

        self.audio_format_menu = ctk.CTkOptionMenu(
            self.audio_row,
            values=["mp3", "m4a", "wav"],
            width=100,
            height=32
        )
        self.audio_format_menu.set("mp3")
        self.audio_format_menu.pack(side="left", padx=(0, 15))

        self.audio_bitrate_lbl = ctk.CTkLabel(self.audio_row, text="Bitrate:", anchor="w", font=ctk.CTkFont(size=13))
        self.audio_bitrate_lbl.pack(side="left", padx=(0, 8))

        self.audio_bitrate_menu = ctk.CTkOptionMenu(
            self.audio_row,
            values=["320k (High Quality)", "256k", "192k", "128k"],
            width=230,
            height=32,
            command=self._on_audio_bitrate_selected
        )
        self.audio_bitrate_menu.pack(side="left")
        self._populate_audio_bitrate_menu()

        # Image Configuration Row (for Image Mode)
        self.image_row = ctk.CTkFrame(self.options_card, fg_color="transparent")

        self.image_format_lbl = ctk.CTkLabel(self.image_row, text="Image Format:", width=120, anchor="w", font=ctk.CTkFont(size=13))
        self.image_format_lbl.pack(side="left")

        self.image_format_menu = ctk.CTkOptionMenu(
            self.image_row,
            values=["Original (Best)", "JPG (Universal)", "PNG (Lossless)", "WebP"],
            width=155,
            height=32
        )
        cur_img_fmt = config.get("image_format", "Original (Best)")
        if cur_img_fmt not in ["Original (Best)", "JPG (Universal)", "PNG (Lossless)", "WebP"]:
            cur_img_fmt = "Original (Best)"
        self.image_format_menu.set(cur_img_fmt)
        self.image_format_menu.pack(side="left", padx=(0, 15))

        self.image_quality_lbl = ctk.CTkLabel(self.image_row, text="Quality:", anchor="w", font=ctk.CTkFont(size=13))
        self.image_quality_lbl.pack(side="left", padx=(0, 8))

        self.image_quality_menu = ctk.CTkOptionMenu(
            self.image_row,
            values=["Original (Master HD)", "High Quality (1080p)", "Standard (736p)"],
            width=210,
            height=32
        )
        self.image_quality_menu.set("Original (Master HD)")
        self.image_quality_menu.pack(side="left")

        # File Naming Format Row
        self.naming_row = ctk.CTkFrame(self.options_card, fg_color="transparent")
        self.naming_row.pack(fill="x", padx=20, pady=6)

        naming_lbl = ctk.CTkLabel(self.naming_row, text="File Naming:", width=120, anchor="w", font=ctk.CTkFont(size=13))
        naming_lbl.pack(side="left")

        self.naming_menu = ctk.CTkOptionMenu(
            self.naming_row,
            values=list(NAMING_TEMPLATES.keys()),
            command=lambda val: config.set("naming_template", val),
            width=200,
            height=32
        )
        cur_naming = config.get("naming_template", "Title + ID (Default)")
        if cur_naming not in NAMING_TEMPLATES:
            cur_naming = "Title + ID (Default)"
        self.naming_menu.set(cur_naming)
        self.naming_menu.pack(side="left", padx=(0, 14))

        order_lbl = ctk.CTkLabel(self.naming_row, text="Order #:", font=ctk.CTkFont(size=12, weight="bold"))
        order_lbl.pack(side="left", padx=(0, 6))

        self.order_num_entry = ctk.CTkEntry(
            self.naming_row,
            width=50,
            height=32,
            justify="center",
            font=ctk.CTkFont(size=12)
        )
        self.order_num_entry.insert(0, "1")
        self.order_num_entry.pack(side="left")

        # Subtitles Row
        self.subs_row = ctk.CTkFrame(self.options_card, fg_color="transparent")
        self.subs_row.pack(fill="x", padx=20, pady=6)

        subs_lbl = ctk.CTkLabel(self.subs_row, text="Subtitles / CC:", width=120, anchor="w", font=ctk.CTkFont(size=13))
        subs_lbl.pack(side="left")

        self.subtitles_menu = ctk.CTkOptionMenu(
            self.subs_row,
            values=["None", "Download .SRT", "Burn into Video"],
            width=200,
            height=32
        )
        self.subtitles_menu.set(config.get("subtitles_mode", "None"))
        self.subtitles_menu.pack(side="left")

        # Timestamp Trimmer / Range Row
        self.trim_container = ctk.CTkFrame(self.options_card, fg_color="transparent")
        self.trim_container.pack(fill="x", padx=20, pady=6)

        self.trim_var = ctk.BooleanVar(value=False)
        self.trim_cb = ctk.CTkCheckBox(
            self.trim_container,
            text="✂ Trim Video Range",
            variable=self.trim_var,
            command=self._on_trim_toggled,
            font=ctk.CTkFont(size=13),
            checkbox_width=20,
            checkbox_height=20
        )
        self.trim_cb.pack(side="left", padx=(0, 15))

        self.trim_inputs_frame = ctk.CTkFrame(self.trim_container, fg_color="transparent")

        t_from_lbl = ctk.CTkLabel(self.trim_inputs_frame, text="Start:", font=ctk.CTkFont(size=12))
        t_from_lbl.pack(side="left", padx=(0, 4))

        self.trim_start_entry = ctk.CTkEntry(
            self.trim_inputs_frame,
            width=65,
            height=30,
            font=ctk.CTkFont(size=12),
            placeholder_text="00:00"
        )
        self.trim_start_entry.insert(0, "00:00")
        self.trim_start_entry.pack(side="left", padx=(0, 10))

        t_to_lbl = ctk.CTkLabel(self.trim_inputs_frame, text="End:", font=ctk.CTkFont(size=12))
        t_to_lbl.pack(side="left", padx=(0, 4))

        self.trim_end_entry = ctk.CTkEntry(
            self.trim_inputs_frame,
            width=65,
            height=30,
            font=ctk.CTkFont(size=12),
            placeholder_text="01:00"
        )
        self.trim_end_entry.pack(side="left", padx=(0, 10))

        trim_hint = ctk.CTkLabel(
            self.trim_inputs_frame,
            text="(MM:SS)",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color=("gray40", "#94A3B8")
        )
        trim_hint.pack(side="left")

        # TikTok & Reels specific note
        self.watermark_note = ctk.CTkLabel(
            self.options_card,
            text="✨ TikTok & Reels videos will be downloaded without watermark automatically.",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color=("#00a2b8", "#06B6D4")
        )
        self.watermark_note.pack(anchor="w", padx=20, pady=(4, 6))

        # Save Directory Row
        save_row = ctk.CTkFrame(self.options_card, fg_color="transparent")
        save_row.pack(fill="x", padx=20, pady=(6, 15))

        save_lbl = ctk.CTkLabel(save_row, text="Save Location:", width=120, anchor="w", font=ctk.CTkFont(size=13))
        save_lbl.pack(side="left")

        self.save_path_label = ctk.CTkLabel(
            save_row,
            text=config.download_dir,
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "#94A3B8"),
            anchor="w"
        )
        self.save_path_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.browse_btn = ctk.CTkButton(
            save_row,
            text="Browse...",
            width=90,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_browse_clicked
        )
        style_glass_button(self.browse_btn)
        self.browse_btn.pack(side="right")

        # Default state
        self.preview_card.pack(fill="x", pady=(0, 15))
        self.options_card.pack(fill="x", pady=(0, 15))
        self._set_ui_loaded(False)

    def _safe_reset_thumbnail(self, text="No Preview"):
        """Safely disassociates any previous Tk PhotoImage from the underlying label to prevent TclError dangling pointer crashes."""
        self.thumbnail_image = None
        self.raw_thumbnail_bytes = None
        if hasattr(self, "thumb_badge_res"):
            self.thumb_badge_res.place_forget()
        if hasattr(self, "thumb_badge_time"):
            self.thumb_badge_time.place_forget()
        try:
            self.thumb_label._label.configure(image="")
        except Exception:
            pass
        try:
            self.thumb_label.configure(image=None, text=text)
        except Exception:
            try:
                self.thumb_label._label.configure(image="", text=text)
            except Exception:
                pass

    def _set_ui_loaded(self, loaded: bool):
        if not loaded:
            self.preview_card.pack_forget()
            self.options_card.pack_forget()
            self.download_button.configure(state="disabled")
            if hasattr(self, "reset_button"):
                self.reset_button.configure(state="disabled")
        else:
            self.preview_card.pack(fill="x", pady=(0, 15))
            self.options_card.pack(fill="x", pady=(0, 15))
            self.download_button.configure(state="normal")
            if hasattr(self, "reset_button"):
                self.reset_button.configure(state="normal")
            try:
                self.content_scroll.update_idletasks()
                self.content_scroll._parent_canvas.yview_moveto(0.0)
            except Exception:
                pass

    def _refresh_quality_options(self):
        self._populate_resolution_menu()
        self._populate_audio_bitrate_menu()

    def _populate_resolution_menu(self):
        if not hasattr(self, "res_menu"):
            return
        pro = is_pro_active()
        if not self.current_video_info or not self.current_video_info.available_resolutions:
            base_list = ["Best Quality", "1080p (Full HD)", "720p (HD)", "480p", "360p"]
        else:
            base_list = self.current_video_info.available_resolutions

        formatted_list = []
        default_val = None

        for r in base_list:
            if r == "Best Quality":
                item = "Best Quality (Up to 4K/8K UHD)" if pro else "Best Quality (Max 720p HD)"
                formatted_list.append(item)
                if pro and default_val is None:
                    default_val = item
            elif any(q in r for q in ["2160", "1440", "1080", "4K", "2K", "4320", "8K", "Full HD"]):
                item = r if pro else f"👑 {r} — Pro Only"
                formatted_list.append(item)
            else:
                formatted_list.append(r)
                if not pro and default_val is None and ("720" in r or "HD" in r):
                    default_val = r

        if default_val is None and formatted_list:
            default_val = formatted_list[0]

        cur_selected = self.res_menu.get()
        self.res_menu.configure(values=formatted_list)
        if cur_selected in formatted_list and (pro or "👑" not in cur_selected):
            self.res_menu.set(cur_selected)
        elif default_val:
            self.res_menu.set(default_val)

    def _on_resolution_selected(self, val: str):
        if "👑" in val or "Pro Only" in val:
            ProDialog(self.winfo_toplevel())
            self.status_label.configure(
                text="👑 1080p Full HD, 2K & 4K require Pro Edition. Upgrade to unlock!",
                text_color="#F59E0B"
            )
            # Revert to highest free resolution (720p HD or Best Quality Free)
            vals = self.res_menu.cget("values")
            for opt in vals:
                if "720p" in opt or "Max 720p" in opt:
                    self.res_menu.set(opt)
                    break

    def _populate_audio_bitrate_menu(self):
        if not hasattr(self, "audio_bitrate_menu"):
            return
        pro = is_pro_active()
        if pro:
            bitrate_vals = ["320k (High Quality)", "256k", "192k", "128k"]
            default_bitrate = "320k (High Quality)"
        else:
            bitrate_vals = ["👑 320k (High Quality) — Pro Only", "256k (High)", "192k (Standard)", "128k"]
            default_bitrate = "192k (Standard)"

        self.audio_bitrate_menu.configure(values=bitrate_vals)
        cur_val = self.audio_bitrate_menu.get()
        if cur_val in bitrate_vals and (pro or "👑" not in cur_val):
            self.audio_bitrate_menu.set(cur_val)
        else:
            self.audio_bitrate_menu.set(default_bitrate)

    def _on_audio_bitrate_selected(self, val: str):
        if "👑" in val or "Pro Only" in val:
            ProDialog(self.winfo_toplevel())
            self.status_label.configure(
                text="👑 320kbps High Fidelity audio requires Pro Edition. Upgrade to unlock!",
                text_color="#F59E0B"
            )
            self.audio_bitrate_menu.set("192k (Standard)")

    def on_clear_video(self):
        self.current_video_info = None
        self._safe_reset_thumbnail("No Preview")
        self.url_entry.delete(0, "end")
        self.status_label.configure(text="")
        self.trim_var.set(False)
        self.trim_inputs_frame.pack_forget()
        self._set_ui_loaded(False)
        try:
            self.content_scroll._parent_canvas.yview_moveto(0.0)
        except Exception:
            pass

    def _on_mode_changed(self, value):
        if "Audio" in value:
            self.res_row.pack_forget()
            self.image_row.pack_forget()
            self.audio_row.pack(fill="x", padx=20, pady=6, after=self.mode_segmented.master)
            if hasattr(self, "subs_row"):
                self.subs_row.pack_forget()
            if hasattr(self, "trim_container"):
                self.trim_container.pack(fill="x", padx=20, pady=6, after=self.naming_row)
        elif "Image" in value:
            self.res_row.pack_forget()
            self.audio_row.pack_forget()
            self.image_row.pack(fill="x", padx=20, pady=6, after=self.mode_segmented.master)
            if hasattr(self, "subs_row"):
                self.subs_row.pack_forget()
            if hasattr(self, "trim_container"):
                self.trim_container.pack_forget()
        else:
            self.audio_row.pack_forget()
            self.image_row.pack_forget()
            self.res_row.pack(fill="x", padx=20, pady=6, after=self.mode_segmented.master)
            if hasattr(self, "subs_row"):
                self.subs_row.pack(fill="x", padx=20, pady=6, after=self.naming_row)
            if hasattr(self, "trim_container"):
                self.trim_container.pack(fill="x", padx=20, pady=6, after=self.subs_row)

    def _on_browse_clicked(self):
        folder = ctk.filedialog.askdirectory(initialdir=config.download_dir)
        if folder:
            config.download_dir = folder
            self.save_path_label.configure(text=folder)

    def on_paste_clicked(self):
        try:
            clipboard = self.clipboard_get().strip()
            if clipboard:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, clipboard)
                self.on_fetch_clicked()
        except Exception:
            self.status_label.configure(text="Clipboard is empty or unavailable.", text_color="orange")

    def on_fetch_clicked(self):
        url = self.url_entry.get().strip()
        if not url:
            self.status_label.configure(text="Please enter a valid video link.", text_color="orange")
            return

        self.status_label.configure(text="⏳ Analyzing video metadata, please wait...", text_color=("gray40", "#94A3B8"))
        self.fetch_btn.configure(state="disabled", text="⏳...")
        self.url_entry.configure(state="disabled")

        def _worker():
            try:
                info = fetch_video_metadata(url)
                img_data = None
                if info.thumbnail_url:
                    try:
                        resp = requests.get(info.thumbnail_url, timeout=10)
                        if resp.status_code == 200:
                            img_data = resp.content
                    except Exception as img_err:
                        print(f"Failed to fetch thumbnail: {img_err}")

                self.after(0, lambda: self._on_fetch_success(info, img_data))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._on_fetch_error(err_msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_fetch_success(self, info: VideoInfo, img_data: Optional[bytes]):
        try:
            self.current_video_info = info
            self.fetch_btn.configure(state="normal", text="🔍 Analyze")
            ready_msg = "✔ Video ready for download!" if is_pro_active() else "✔ Video ready for download! (Free Edition capped at 720p HD)"
            self.status_label.configure(text=ready_msg, text_color="#10B981")

            self.video_title_label.configure(text=info.title)
            self.uploader_label.configure(text=f"By {info.uploader}")
            self.duration_badge.configure(text=f"⏱ {info.duration_str}")
            self.views_badge.configure(text=f"👁 {info.view_count_str}")

            # Platform badge styling
            plat_colors = {
                "shorts": ("#EF4444", "white"),
                "youtube": ("#DC2626", "white"),
                "tiktok": ("#06B6D4", "#0F172A"),
                "instagram": ("#E1306C", "white"),
                "pinterest": ("#E60023", "white"),
                "other": ("#6B7280", "white")
            }
            bg_col, txt_col = plat_colors.get(info.platform, ("#6B7280", "white"))
            self.platform_badge.configure(
                text=get_platform_label(info.platform),
                fg_color=bg_col,
                text_color=txt_col
            )

            if info.platform in ["tiktok", "instagram"]:
                self.watermark_note.pack(anchor="w", padx=20, pady=(4, 6))
            else:
                self.watermark_note.pack_forget()

            if info.available_resolutions:
                self._populate_resolution_menu()

            self.raw_thumbnail_bytes = img_data

            # Quality / Resolution badge text and color
            res_text = "HD"
            res_color = ("#2563EB", "#1D4ED8")
            if info.available_resolutions:
                top_res = info.available_resolutions[0]
                if "Image" in top_res or (info.raw_info and info.raw_info.get("is_image")):
                    res_text = "IMAGE HD"
                    res_color = ("#E60023", "#DC2626")
                elif "Watermark" in top_res or "NO WM" in top_res:
                    res_text = "HD NO WM"
                    res_color = ("#059669", "#10B981")
                elif "4K" in top_res or "2160" in top_res:
                    res_text = "4K UHD"
                    res_color = ("#7C3AED", "#6D28D9")
                elif "1080" in top_res or "Full HD" in top_res:
                    res_text = "1080p FHD"
                    res_color = ("#2563EB", "#1D4ED8")
                elif "720" in top_res:
                    res_text = "720p HD"
                    res_color = ("#0284C7", "#0369A1")
                else:
                    res_text = "HQ"
                    res_color = ("#475569", "#334155")

            self.thumb_badge_res.configure(text=res_text, fg_color=res_color)
            self.thumb_badge_res.place(relx=0.06, rely=0.08, anchor="nw")

            # Duration badge
            if info.duration_str and info.duration_str != "Live":
                self.thumb_badge_time.configure(text=f"⏱ {info.duration_str}")
                self.thumb_badge_time.place(relx=0.94, rely=0.92, anchor="se")
            else:
                self.thumb_badge_time.place_forget()

            if img_data:
                try:
                    pil_img = Image.open(io.BytesIO(img_data))
                    pil_img.thumbnail((220, 135))
                    self.thumbnail_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                    try:
                        self.thumb_label._label.configure(image="")
                    except Exception:
                        pass
                    self.thumb_label.configure(image=self.thumbnail_image, text="")
                except Exception as img_err:
                    print(f"Failed to display thumbnail: {img_err}")
                    self._safe_reset_thumbnail("Thumbnail\nNot Available")
            else:
                self._safe_reset_thumbnail("No Thumbnail")

            # Auto-switch to Image mode if analyzing a photo pin
            is_image_pin = bool(info.raw_info and info.raw_info.get("is_image"))
            if is_image_pin:
                self.mode_segmented.set("🖼 Image (HD)")
                self._on_mode_changed("🖼 Image (HD)")
            else:
                if self.mode_segmented.get() == "🖼 Image (HD)":
                    self.mode_segmented.set("🎬 Video (MP4)")
                    self._on_mode_changed("🎬 Video (MP4)")

            # Set default trimmer end time to video duration
            if info.duration_str and info.duration_str != "Live":
                self.trim_end_entry.delete(0, "end")
                self.trim_end_entry.insert(0, info.duration_str)

            self._set_ui_loaded(True)
        except Exception as e:
            print(f"Error displaying video info: {e}")
            self.fetch_btn.configure(state="normal", text="🔍 Analyze")
            self.url_entry.configure(state="normal")
            self.status_label.configure(text=f"❌ Error displaying video: {e}", text_color="#EF4444")
            self._set_ui_loaded(False)

    def _on_trim_toggled(self):
        if self.trim_var.get():
            self.trim_inputs_frame.pack(side="left")
        else:
            self.trim_inputs_frame.pack_forget()

    def _on_fetch_error(self, err_msg: str):
        self.fetch_btn.configure(state="normal", text="🔍 Analyze")
        self.url_entry.configure(state="normal")
        short_err = err_msg.split("\n")[-1] if "\n" in err_msg else err_msg
        if len(short_err) > 80:
            short_err = short_err[:77] + "..."
        self.status_label.configure(text=f"❌ Error: {short_err}", text_color="#EF4444")
        self._set_ui_loaded(False)

    def on_download_clicked(self):
        if not self.current_video_info:
            return

        mode_val = self.mode_segmented.get()
        if "Audio" in mode_val:
            mode = "audio"
        elif "Image" in mode_val:
            mode = "image"
        else:
            mode = "video"

        resolution = self.res_menu.get()
        audio_fmt = self.audio_format_menu.get()
        bitrate_str = self.audio_bitrate_menu.get().split()[0]

        raw_img_fmt = self.image_format_menu.get().split()[0].lower()
        img_fmt = "jpg" if "jpg" in raw_img_fmt else ("png" if "png" in raw_img_fmt else ("webp" if "webp" in raw_img_fmt else "original"))

        # Pro Feature Gate: 4K/2K UHD Video and 320k Audio
        is_4k = (mode == "video") and (any(q in resolution for q in ["4K", "2160", "1440"]) or "👑" in resolution or "Pro Only" in resolution)
        is_320k = (mode == "audio") and ("320" in bitrate_str or "👑" in self.audio_bitrate_menu.get())
        if (is_4k or is_320k) and not is_pro_active():
            ProDialog(self.winfo_toplevel())
            feat_name = "4K / 2K Ultra HD video" if is_4k else "320kbps High Fidelity audio"
            self.status_label.configure(
                text=f"👑 {feat_name} is a Pro Edition feature. Upgrade to unlock!",
                text_color="#F59E0B"
            )
            return

        # Clean resolution for engine
        clean_res = resolution.replace("👑", "").replace("— Pro Only", "").strip()
        if "Max 1080p" in clean_res:
            clean_res = "1080p (Full HD)"
        elif "Up to 4K" in clean_res:
            clean_res = "Best Quality"

        order_num = 1
        try:
            order_num = int(self.order_num_entry.get().strip())
        except Exception:
            order_num = 1

        time_range = None
        if self.trim_var.get() and mode != "image":
            s_val = self.trim_start_entry.get().strip()
            e_val = self.trim_end_entry.get().strip()
            if s_val or e_val:
                time_range = (s_val or "00:00", e_val or "")

        subtitles_choice = self.subtitles_menu.get() if mode != "image" else "None"

        task = download_manager.add_task(
            url=self.current_video_info.url,
            title=self.current_video_info.title,
            thumbnail_url=self.current_video_info.thumbnail_url,
            platform=self.current_video_info.platform,
            mode=mode,
            resolution=clean_res,
            audio_format=audio_fmt,
            audio_bitrate=bitrate_str,
            image_format=img_fmt,
            save_dir=config.download_dir,
            naming_template=self.naming_menu.get(),
            order_num=order_num,
            time_range=time_range,
            subtitles_mode=subtitles_choice,
            extra_info=self.current_video_info.raw_info
        )

        self.status_label.configure(
            text="🚀 Download started! Added to Queue.",
            text_color="#10B981"
        )

        if self.on_download_started:
            self.on_download_started(task)

    def on_save_thumbnail_clicked(self):
        """Allows 1-click saving of the high-res thumbnail to disk."""
        if not self.raw_thumbnail_bytes or not self.current_video_info:
            self.status_label.configure(text="⚠ No thumbnail image available to save.", text_color="orange")
            return

        import re
        safe_title = re.sub(r'[\\/*?:"<>|]', "", self.current_video_info.title).strip()
        if not safe_title:
            safe_title = "thumbnail"
        default_name = f"{safe_title[:40]}_thumb.jpg"

        file_path = ctk.filedialog.asksaveasfilename(
            initialdir=config.download_dir,
            initialfile=default_name,
            defaultextension=".jpg",
            filetypes=[("JPEG Image", "*.jpg"), ("PNG Image", "*.png"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        try:
            img = Image.open(io.BytesIO(self.raw_thumbnail_bytes))
            if file_path.lower().endswith(".png"):
                img.save(file_path, format="PNG")
            else:
                img = img.convert("RGB")
                img.save(file_path, format="JPEG", quality=95)

            self.status_label.configure(
                text=f"✔ Thumbnail saved: {os.path.basename(file_path)}",
                text_color="#10B981"
            )
        except Exception as e:
            self.status_label.configure(
                text=f"❌ Failed to save thumbnail: {e}",
                text_color="#EF4444"
            )

