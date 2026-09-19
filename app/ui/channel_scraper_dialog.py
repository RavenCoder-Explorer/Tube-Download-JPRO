import io
import threading
import requests
from typing import List, Dict, Any, Callable, Optional
from PIL import Image
import customtkinter as ctk

from app.downloader import scrape_channel_clips, get_platform_label
from app.license_manager import is_pro_active
from app.ui.pro_dialog import ProDialog
from app.ui.theme import (
    COLOR_WINDOW_BG, COLOR_CARD_BG, COLOR_CARD_BORDER, COLOR_INPUT_BG,
    COLOR_INPUT_BORDER, NEON_CYAN, NEON_CYAN_MID, NEON_CYAN_DEEP,
    NEON_EMERALD, CROWN_GOLD, style_neon_cyan_button,
    style_neon_emerald_button, style_glass_button, style_card, style_input_entry
)


class ChannelScraperDialog(ctk.CTkToplevel):
    """
    Interactive modal popup for scraping and selecting clips from YouTube Channels,
    YouTube Shorts, TikTok profiles, or Playlists into the batch queue.
    """

    def __init__(self, master, on_add_links: Callable[[List[str]], None], **kwargs):
        super().__init__(master, **kwargs)
        self.on_add_links = on_add_links
        self.scraped_items: List[Dict[str, Any]] = []
        self.item_cards: List[Dict[str, Any]] = []
        self.is_scraping = False

        self.title("Channel & Playlist Visual Scraper - Tube Download JPRO")
        self.geometry("860x700")
        self.minsize(740, 560)
        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        self.configure(fg_color=COLOR_WINDOW_BG)

        # 1. Header Frame
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 10))

        title = ctk.CTkLabel(
            header,
            text="Channel & Playlist Visual Scraper",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(anchor="w")

        sub = ctk.CTkLabel(
            header,
            text="Scrape up to 100 Shorts or videos from a YouTube channel or playlist, visually inspect clips, and queue selected items.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8")
        )
        sub.pack(anchor="w")

        # 2. Input Box Card
        input_card = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        input_card.pack(fill="x", padx=24, pady=(5, 10))

        url_row = ctk.CTkFrame(input_card, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=(12, 8))

        self.url_entry = ctk.CTkEntry(
            url_row,
            placeholder_text="Enter Channel URL (e.g. https://www.youtube.com/@MrBeast/shorts)...",
            height=40,
            font=ctk.CTkFont(size=13),
            corner_radius=8
        )
        style_input_entry(self.url_entry)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self._start_scrape())

        paste_btn = ctk.CTkButton(
            url_row,
            text="📋 Paste",
            width=80,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_paste
        )
        style_glass_button(paste_btn)
        paste_btn.pack(side="left", padx=(0, 10))

        self.scrape_btn = ctk.CTkButton(
            url_row,
            text="🔍 Scrape Channel",
            width=140,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_scrape
        )
        style_neon_cyan_button(self.scrape_btn)
        self.scrape_btn.pack(side="left")

        # Options Row: Mode & Limit
        opt_row = ctk.CTkFrame(input_card, fg_color="transparent")
        opt_row.pack(fill="x", padx=16, pady=(0, 12))

        lim_lbl = ctk.CTkLabel(opt_row, text="Max Items:", font=ctk.CTkFont(size=12, weight="bold"))
        lim_lbl.pack(side="left", padx=(0, 6))

        self.limit_menu = ctk.CTkOptionMenu(
            opt_row,
            values=["20", "40", "60", "100"],
            width=80,
            height=28,
            fg_color=("#0284C7", "#0284C7"),
            button_color=("#0369A1", "#0369A1"),
            button_hover_color=("#38BDF8", "#38BDF8")
        )
        self.limit_menu.set("40")
        self.limit_menu.pack(side="left", padx=(0, 20))

        type_lbl = ctk.CTkLabel(opt_row, text="Scrape Target:", font=ctk.CTkFont(size=12, weight="bold"))
        type_lbl.pack(side="left", padx=(0, 6))

        self.type_menu = ctk.CTkOptionMenu(
            opt_row,
            values=["Shorts Only", "Standard Videos", "All / Playlists"],
            width=140,
            height=28,
            fg_color=("#0284C7", "#0284C7"),
            button_color=("#0369A1", "#0369A1"),
            button_hover_color=("#38BDF8", "#38BDF8")
        )
        self.type_menu.set("Shorts Only")
        self.type_menu.pack(side="left", padx=(0, 15))

        hint_lbl = ctk.CTkLabel(
            opt_row,
            text="(Fast multi-threaded scraping)",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color=("gray40", "#94A3B8")
        )
        hint_lbl.pack(side="left")

        # Status row
        self.status_lbl = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8"),
            anchor="w"
        )
        self.status_lbl.pack(fill="x", padx=28, pady=(0, 6))

        # 3. Selection & Batch Action Toolbar
        self.action_bar = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        self.action_bar.pack(fill="x", padx=24, pady=(0, 10))

        ab_inner = ctk.CTkFrame(self.action_bar, fg_color="transparent")
        ab_inner.pack(fill="x", padx=16, pady=8)

        self.select_all_var = ctk.BooleanVar(value=True)
        self.select_all_cb = ctk.CTkCheckBox(
            ab_inner,
            text="Select All",
            variable=self.select_all_var,
            command=self._on_toggle_select_all,
            font=ctk.CTkFont(size=12, weight="bold"),
            checkbox_width=18,
            checkbox_height=18
        )
        self.select_all_cb.pack(side="left", padx=(0, 15))

        self.count_badge = ctk.CTkLabel(
            ab_inner,
            text="0 clips found",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8")
        )
        self.count_badge.pack(side="left")

        self.add_btn = ctk.CTkButton(
            ab_inner,
            text="➕  Add Selected (0) to Queue",
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled",
            command=self._on_confirm_add
        )
        style_neon_emerald_button(self.add_btn)
        self.add_btn.pack(side="right")

        # 4. Scrollable Container for Scraped Cards
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.empty_lbl = ctk.CTkLabel(
            self.scroll,
            text="No clips scraped yet.\nEnter a channel link above to begin.",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "#64748B")
        )
        self.empty_lbl.pack(pady=60)

    def _on_paste(self):
        try:
            txt = self.clipboard_get().strip()
            if txt:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, txt)
        except Exception:
            pass

    def _ensure_shorts_suffix(self):
        url = self.url_entry.get().strip()
        if url and "/shorts" not in url:
            url = url.rstrip("/") + "/shorts"
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, url)

    def _start_scrape(self):
        url = self.url_entry.get().strip()
        if not url:
            self.status_lbl.configure(text="⚠ Please enter a valid channel or playlist URL.", text_color="#EF4444")
            return

        limit = int(self.limit_menu.get())
        self.is_scraping = True
        self.scrape_btn.configure(state="disabled", text="⏳ Scraping...")
        self.status_lbl.configure(
            text=f"⏳ Contacting platform and scraping up to {limit} clips (Fast Flat Extraction)...",
            text_color=("#1f6aa5", "#38BDF8")
        )
        self.add_btn.configure(state="disabled")

        # Clear existing items
        for child in self.scroll.winfo_children():
            child.destroy()
        self.item_cards.clear()
        self.scraped_items.clear()

        loading = ctk.CTkLabel(
            self.scroll,
            text="⏳ Scraping channel items, please wait...",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray40", "#94A3B8")
        )
        loading.pack(pady=60)

        def worker():
            try:
                items = scrape_channel_clips(url, max_items=limit)
                self.after(0, lambda: self._on_scrape_success(items))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._on_scrape_error(err_msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_scrape_success(self, items: List[Dict[str, Any]]):
        self.is_scraping = False
        self.scrape_btn.configure(state="normal", text="🔍 Scrape Channel")

        for child in self.scroll.winfo_children():
            child.destroy()

        if not items:
            self.status_lbl.configure(
                text="❌ No video clips found. Try adding '/shorts' or check if channel has public uploads.",
                text_color="#EF4444"
            )
            empty = ctk.CTkLabel(
                self.scroll,
                text="No video clips found for this channel URL.\nMake sure the channel exists and has public videos.",
                font=ctk.CTkFont(size=13),
                text_color=("gray40", "#64748B")
            )
            empty.pack(pady=60)
            return

        self.scraped_items = items
        self.status_lbl.configure(
            text=f"✔ Successfully scraped {len(items)} clips! Check items to add to queue.",
            text_color="#10B981"
        )
        self.count_badge.configure(text=f"{len(items)} clips found")

        # Build cards
        for i, item in enumerate(items):
            card = self._create_item_card(i, item)
            card.pack(fill="x", padx=4, pady=4)

        self._update_selected_count()

    def _on_scrape_error(self, err_msg: str):
        self.is_scraping = False
        self.scrape_btn.configure(state="normal", text="🔍 Scrape Channel")
        for child in self.scroll.winfo_children():
            child.destroy()
        self.status_lbl.configure(text=f"❌ Error scraping channel: {err_msg[:80]}", text_color="#EF4444")

    def _create_item_card(self, index: int, item: Dict[str, Any]) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            self.scroll,
            corner_radius=10,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)

        # Checkbox
        var = ctk.BooleanVar(value=True)
        cb = ctk.CTkCheckBox(
            inner,
            text="",
            variable=var,
            width=20,
            height=20,
            command=self._update_selected_count
        )
        cb.pack(side="left", padx=(0, 10))

        # Thumbnail (Placeholder initially, fetched in background)
        thumb_lbl = ctk.CTkLabel(
            inner,
            text="🎬",
            width=96,
            height=54,
            corner_radius=6,
            fg_color=("gray80", "#0F172A"),
            font=ctk.CTkFont(size=16)
        )
        thumb_lbl.pack(side="left", padx=(0, 12))

        if item.get("thumbnail_url"):
            self._load_thumbnail_async(thumb_lbl, item["thumbnail_url"])

        # Title and details
        details = ctk.CTkFrame(inner, fg_color="transparent")
        details.pack(side="left", fill="both", expand=True)

        t_lbl = ctk.CTkLabel(
            details,
            text=f"#{index + 1}  {item['title']}",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            wraplength=520,
            justify="left"
        )
        t_lbl.pack(fill="x", pady=(0, 4))

        meta_row = ctk.CTkFrame(details, fg_color="transparent")
        meta_row.pack(fill="x")

        plat = item.get("platform", "youtube")
        plat_badge = ctk.CTkLabel(
            meta_row,
            text=get_platform_label(plat),
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=("#EF4444" if plat in ["youtube", "shorts"] else "#06B6D4"),
            text_color="white",
            corner_radius=4,
            padx=6,
            pady=1
        )
        plat_badge.pack(side="left", padx=(0, 6))

        if item.get("duration_str"):
            dur_badge = ctk.CTkLabel(
                meta_row,
                text=f"⏱ {item['duration_str']}",
                font=ctk.CTkFont(size=10),
                fg_color=("gray80", "#334155"),
                corner_radius=4,
                padx=6,
                pady=1
            )
            dur_badge.pack(side="left", padx=(0, 6))

        if item.get("view_count_str"):
            v_badge = ctk.CTkLabel(
                meta_row,
                text=f"👁 {item['view_count_str']}",
                font=ctk.CTkFont(size=10),
                fg_color=("gray80", "#334155"),
                corner_radius=4,
                padx=6,
                pady=1
            )
            v_badge.pack(side="left", padx=(0, 6))

        if item.get("uploader"):
            up_lbl = ctk.CTkLabel(
                meta_row,
                text=f"By {item['uploader']}",
                font=ctk.CTkFont(size=10),
                text_color=("gray40", "#94A3B8")
            )
            up_lbl.pack(side="left")

        self.item_cards.append({
            "item": item,
            "var": var,
            "card": card
        })
        return card

    def _load_thumbnail_async(self, label: ctk.CTkLabel, thumb_url: str):
        def worker():
            try:
                resp = requests.get(thumb_url, timeout=6)
                if resp.status_code == 200:
                    pil_img = Image.open(io.BytesIO(resp.content))
                    pil_img.thumbnail((96, 54))
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                    def _apply():
                        try:
                            label._label.configure(image="")
                        except Exception:
                            pass
                        label._ctk_img_ref = ctk_img
                        label.configure(image=ctk_img, text="")
                    self.after(0, _apply)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _on_toggle_select_all(self):
        state = self.select_all_var.get()
        for c in self.item_cards:
            c["var"].set(state)
        self._update_selected_count()

    def _update_selected_count(self):
        sel_count = sum(1 for c in self.item_cards if c["var"].get())
        total = len(self.item_cards)
        self.count_badge.configure(text=f"Selected: {sel_count} / {total} clips")

        if sel_count > 0:
            self.add_btn.configure(
                state="normal",
                text=f"➕  Add Selected ({sel_count}) to Queue"
            )
        else:
            self.add_btn.configure(
                state="disabled",
                text="➕  Add Selected (0) to Queue"
            )

    def _on_confirm_add(self):
        selected_items = [
            (c["item"]["url"], c["item"].get("title", ""))
            for c in self.item_cards if c["var"].get()
        ]
        if not selected_items:
            return

        # Pro Feature Gate: Max 5 clips from channel scraper in Free Edition
        if len(selected_items) > 5 and not is_pro_active():
            ProDialog(self)
            self.status_lbl.configure(
                text="👑 Free Edition allows adding up to 5 clips at once. Upgrade to Pro for unlimited channel ingestion!",
                text_color="#F59E0B"
            )
            return

        if self.on_add_links:
            try:
                self.on_add_links(selected_items)
            except Exception as e:
                print(f"Error adding links to queue: {e}")
                self.status_lbl.configure(text=f"❌ Error adding to queue: {e}", text_color="#EF4444")
                return

        self.destroy()
