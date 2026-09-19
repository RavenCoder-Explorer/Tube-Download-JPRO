import threading
import webbrowser
import customtkinter as ctk

from app.config import config
from app.license_manager import activate_license, is_pro_active, get_license_info, get_formatted_device_id
from app.ui.theme import (
    COLOR_WINDOW_BG, COLOR_CARD_BG, COLOR_CARD_BORDER, NEON_CYAN, NEON_CYAN_MID,
    NEON_CYAN_DEEP, NEON_EMERALD, CROWN_GOLD, get_app_icon_image,
    style_crown_gold_button, style_neon_cyan_button, style_glass_button,
    style_input_entry
)


class ProDialog(ctk.CTkToplevel):
    """Modern modal dialog for purchasing and activating Tube Download JPRO Pro Edition."""

    def __init__(self, master, on_activated=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_activated = on_activated

        self.title("Upgrade to Tube Download JPRO Pro")
        self.geometry("590x800")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # Center dialog over master
        self.after(10, self._center_window)
        self._build_ui()

    def _center_window(self):
        try:
            self.update_idletasks()
            w = self.winfo_width()
            h = self.winfo_height()
            mx = self.master.winfo_x()
            my = self.master.winfo_y()
            mw = self.master.winfo_width()
            mh = self.master.winfo_height()
            x = mx + (mw - w) // 2
            y = my + (mh - h) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    def _build_ui(self):
        self.configure(fg_color=COLOR_WINDOW_BG)

        bg_frame = ctk.CTkFrame(self, fg_color=COLOR_WINDOW_BG, corner_radius=0)
        bg_frame.pack(fill="both", expand=True)

        container = ctk.CTkFrame(bg_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=28, pady=24)

        # Header with 3D Crowned Icon
        header_frame = ctk.CTkFrame(container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 16))

        h_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        h_row.pack(fill="x")

        self.icon_img = get_app_icon_image((54, 54))
        if self.icon_img:
            h_icon = ctk.CTkLabel(h_row, image=self.icon_img, text="")
            h_icon.pack(side="left", padx=(0, 14))

        h_text_col = ctk.CTkFrame(h_row, fg_color="transparent")
        h_text_col.pack(side="left", fill="x", expand=True)

        crown_badge = ctk.CTkLabel(
            h_text_col,
            text="👑 PRO EDITION",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#D97706", "#F59E0B"),
            text_color="#0F172A",
            corner_radius=6,
            padx=10,
            pady=2
        )
        crown_badge.pack(anchor="w", pady=(0, 4))

        title = ctk.CTkLabel(
            h_text_col,
            text="Unlock Full Creator Power",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(anchor="w")

        sub = ctk.CTkLabel(
            header_frame,
            text="Get unlimited batch queues, 4K UHD video, and channel scraping with a single lifetime license.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8"),
            anchor="w",
            wraplength=520,
            justify="left"
        )
        sub.pack(anchor="w", pady=(6, 0))

        # Comparison Card
        comp_card = ctk.CTkFrame(
            container,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        comp_card.pack(fill="x", pady=(0, 16))

        inner_comp = ctk.CTkFrame(comp_card, fg_color="transparent")
        inner_comp.pack(fill="x", padx=16, pady=14)

        features = [
            ("⚡ 1080p, 4K & 8K Ultra HD", "Max 720p (HD)", "✔ Full 1080p / 4K / 8K UHD"),
            ("🚀 Batch Queue Capacity", "5 items max", "✔ Unlimited links"),
            ("🔍 Channel & Playlist Scraper", "5 clips preview", "✔ 100+ clips in 1-click"),
            ("🎵 Studio Audio Bitrate", "Up to 192k", "✔ 320kbps High Fidelity"),
            ("✂️ Video Trimmer & Subtitles", "Basic", "✔ Pro Stream Slicing"),
            ("🔄 Priority Engine Patches", "Standard", "✔ Lifetime Priority Updates")
        ]

        # Table header
        th = ctk.CTkFrame(inner_comp, fg_color="transparent")
        th.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(th, text="Feature", font=ctk.CTkFont(size=11, weight="bold"), anchor="w", width=220).pack(side="left")
        ctk.CTkLabel(th, text="Free", font=ctk.CTkFont(size=11, weight="bold"), text_color=("gray40", "#64748B"), width=110, anchor="w").pack(side="left")
        ctk.CTkLabel(th, text="Pro Lifetime", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#D97706", "#F59E0B"), anchor="w").pack(side="left")

        for feat, free_val, pro_val in features:
            row = ctk.CTkFrame(inner_comp, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=feat, font=ctk.CTkFont(size=11), anchor="w", width=220).pack(side="left")
            ctk.CTkLabel(row, text=free_val, font=ctk.CTkFont(size=11), text_color=("gray40", "#64748B"), width=110, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=pro_val, font=ctk.CTkFont(size=11, weight="bold"), text_color=("#10B981", "#34D399"), anchor="w").pack(side="left")

        # Tiered Plans Grid (Monthly $2, 3-Month $5, 1-Year $15, Lifetime $19)
        store_url = config.get("store_url", "https://lemonsqueezy.com")
        plans_frame = ctk.CTkFrame(container, fg_color="transparent")
        plans_frame.pack(fill="x", pady=(0, 10))

        # Row 1: Monthly ($2) and 3-Month ($5)
        p_row1 = ctk.CTkFrame(plans_frame, fg_color="transparent")
        p_row1.pack(fill="x", pady=(0, 6))

        b_1m = ctk.CTkButton(
            p_row1,
            text="📅 1 Month — $2.00",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: webbrowser.open(store_url)
        )
        style_glass_button(b_1m)
        b_1m.pack(side="left", fill="x", expand=True, padx=(0, 4))

        b_3m = ctk.CTkButton(
            p_row1,
            text="⭐ 3 Months — $5.00 ($1.66/mo)",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: webbrowser.open(store_url)
        )
        style_glass_button(b_3m)
        b_3m.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Row 2: 1-Year ($15) and Lifetime ($19 - Highlighted)
        p_row2 = ctk.CTkFrame(plans_frame, fg_color="transparent")
        p_row2.pack(fill="x")

        b_1y = ctk.CTkButton(
            p_row2,
            text="⚡ 1 Year — $15.00 ($1.25/mo)",
            height=38,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: webbrowser.open(store_url)
        )
        style_neon_cyan_button(b_1y)
        b_1y.pack(side="left", fill="x", expand=True, padx=(0, 4))

        b_life = ctk.CTkButton(
            p_row2,
            text="👑 Lifetime — $19.00 (Best Value)",
            height=38,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: webbrowser.open(store_url)
        )
        style_crown_gold_button(b_life)
        b_life.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Device ID (1-Device Lock Info Box)
        dev_card = ctk.CTkFrame(
            container,
            corner_radius=10,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=("#F59E0B", "#B45309")
        )
        dev_card.pack(fill="x", pady=(0, 12))

        dev_inner = ctk.CTkFrame(dev_card, fg_color="transparent")
        dev_inner.pack(fill="x", padx=12, pady=8)

        dev_top = ctk.CTkFrame(dev_inner, fg_color="transparent")
        dev_top.pack(fill="x")

        dev_id = get_formatted_device_id()
        ctk.CTkLabel(
            dev_top,
            text=f"💻 Your Device ID:  {dev_id}",
            font=ctk.CTkFont(size=11, weight="bold", family="Consolas"),
            text_color=("#D97706", "#F59E0B"),
            anchor="w"
        ).pack(side="left")

        def _copy_id():
            self.clipboard_clear()
            self.clipboard_append(dev_id)
            copy_btn.configure(text="✔ Copied!", fg_color="#10B981")
            self.after(2000, lambda: copy_btn.configure(text="📋 Copy ID"))

        copy_btn = ctk.CTkButton(
            dev_top,
            text="📋 Copy ID",
            width=75,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=_copy_id
        )
        style_glass_button(copy_btn)
        copy_btn.pack(side="right")

        ctk.CTkLabel(
            dev_inner,
            text="🔒 1 key is locked to 1 device. Provide this Device ID for direct 1-computer purchases.",
            font=ctk.CTkFont(size=10),
            text_color=("gray45", "#94A3B8"),
            anchor="w"
        ).pack(anchor="w", pady=(2, 0))

        # Divider or text
        div_frame = ctk.CTkFrame(container, fg_color="transparent")
        div_frame.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(div_frame, text="Already have a license key? Activate below:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(side="left")

        # License Key Entry Box & Activate Button
        act_row = ctk.CTkFrame(container, fg_color="transparent")
        act_row.pack(fill="x", pady=(0, 6))

        self.key_entry = ctk.CTkEntry(
            act_row,
            placeholder_text="Enter key (e.g. JPRO-1M-... or JPRO-LIFE-...)",
            height=40,
            font=ctk.CTkFont(size=12),
            corner_radius=8
        )
        style_input_entry(self.key_entry)
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.key_entry.bind("<Return>", lambda e: self._handle_activate())

        self.act_btn = ctk.CTkButton(
            act_row,
            text="🔑 Activate",
            height=40,
            width=110,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._handle_activate
        )
        style_crown_gold_button(self.act_btn)
        self.act_btn.pack(side="right")

        # Status / Feedback label
        self.status_label = ctk.CTkLabel(
            container,
            text="🔒 1 license key is locked to 1 device. Check your email or message for your key.",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "#64748B"),
            anchor="w"
        )
        self.status_label.pack(fill="x", pady=(2, 0))

    def _handle_activate(self):
        raw_key = self.key_entry.get().strip()
        if not raw_key:
            self.status_label.configure(text="⚠ Please paste or enter your license key.", text_color="#F59E0B")
            return

        self.status_label.configure(text="⏳ Validating license with server...", text_color=("#1f6aa5", "#38BDF8"))
        self.act_btn.configure(state="disabled", text="⏳...")

        def _worker():
            success, message = activate_license(raw_key)
            self.after(0, lambda: self._on_activate_result(success, message))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_activate_result(self, success: bool, message: str):
        self.act_btn.configure(state="normal", text="🔑 Activate")
        if success:
            self.status_label.configure(text=f"{message}", text_color="#10B981")
            self.key_entry.configure(state="disabled")
            if self.on_activated:
                self.on_activated()
            self.after(1500, self.destroy)
        else:
            self.status_label.configure(text=f"❌ {message}", text_color="#EF4444")
