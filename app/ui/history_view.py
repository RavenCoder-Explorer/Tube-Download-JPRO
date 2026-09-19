import os
import subprocess
from typing import Dict, Any, List
import customtkinter as ctk

from app.config import config
from app.downloader import download_manager, DownloadTask, get_platform_label
from app.ui.theme import (
    COLOR_WINDOW_BG, COLOR_CARD_BG, COLOR_CARD_BORDER, NEON_CYAN, NEON_CYAN_MID, NEON_CYAN_DEEP,
    NEON_EMERALD, style_neon_emerald_button, style_glass_button,
    style_danger_glass_button, style_card
)


class ActiveTaskCard(ctk.CTkFrame):
    """Card representing an active/in-progress download task."""

    def __init__(self, master, task: DownloadTask, on_cancel=None, on_dismiss=None, **kwargs):
        super().__init__(
            master,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            **kwargs
        )
        self.task = task
        self.on_cancel = on_cancel
        self.on_dismiss = on_dismiss

        self._build_ui()
        self.update_task_data(task)

    def _build_ui(self):
        self.pack_configure(fill="x", padx=10, pady=5)

        # Header line: Title + Platform badge + Cancel/Dismiss button
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(10, 4))

        self.title_label = ctk.CTkLabel(
            top_row,
            text=self.task.title,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
            wraplength=480,
            justify="left"
        )
        self.title_label.pack(side="left", fill="x", expand=True)

        # Platform colors
        plat_colors = {
            "shorts": ("#EF4444", "white"),
            "youtube": ("#DC2626", "white"),
            "tiktok": ("#06B6D4", "#0F172A"),
            "instagram": ("#E1306C", "white"),
            "pinterest": ("#E60023", "white"),
            "other": ("#6B7280", "white")
        }
        bg_col, txt_col = plat_colors.get(self.task.platform, ("#6B7280", "white"))

        self.plat_badge = ctk.CTkLabel(
            top_row,
            text=get_platform_label(self.task.platform).upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=bg_col,
            text_color=txt_col,
            corner_radius=4,
            padx=7,
            pady=1
        )
        self.plat_badge.pack(side="left", padx=8)

        self.cancel_btn = ctk.CTkButton(
            top_row,
            text="Cancel",
            width=70,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._handle_cancel
        )
        style_danger_glass_button(self.cancel_btn)
        self.cancel_btn.pack(side="right")

        # Progress bar
        self.pbar = ctk.CTkProgressBar(self, height=8, corner_radius=4, progress_color=NEON_CYAN)
        self.pbar.pack(fill="x", padx=14, pady=6)
        self.pbar.set(0)

        # Footer line: Stats (Percentage, Speed, ETA, Size)
        bottom_row = ctk.CTkFrame(self, fg_color="transparent")
        bottom_row.pack(fill="x", padx=14, pady=(2, 10))

        self.percent_label = ctk.CTkLabel(
            bottom_row,
            text="0%",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#1f6aa5", "#38BDF8")
        )
        self.percent_label.pack(side="left")

        self.stats_label = ctk.CTkLabel(
            bottom_row,
            text="-- MB/s • ETA: --:-- • 0 MB",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "#94A3B8")
        )
        self.stats_label.pack(side="left", padx=12)

        self.status_badge = ctk.CTkLabel(
            bottom_row,
            text="Queued",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("gray75", "#334155"),
            corner_radius=4,
            padx=8,
            pady=1
        )
        self.status_badge.pack(side="right")

    def _handle_cancel(self):
        if self.on_cancel:
            self.on_cancel(self.task.task_id)

    def _handle_dismiss(self):
        if self.on_dismiss:
            self.on_dismiss(self.task.task_id)

    def update_task_data(self, task: DownloadTask):
        self.task = task
        pct = task.progress / 100.0
        self.pbar.set(min(1.0, max(0.0, pct)))
        self.percent_label.configure(text=f"{task.progress:.1f}%")
        self.stats_label.configure(text=f"{task.speed_str} • ETA: {task.eta_str} • {task.size_str}")

        if task.title and task.title != "Loading metadata...":
            self.title_label.configure(text=task.title)

        if task.status == "downloading":
            self.status_badge.configure(text="Downloading", fg_color=("#2563EB", "#1D4ED8"), text_color="white")
            self.cancel_btn.configure(
                state="normal",
                text="Cancel",
                fg_color=("#DC2626", "#B91C1C"),
                hover_color=("#991B1B", "#7F1D1D"),
                text_color="white",
                command=self._handle_cancel
            )
        elif task.status == "merging":
            self.status_badge.configure(text="Merging...", fg_color=("#D97706", "#B45309"), text_color="white")
            self.cancel_btn.configure(
                state="normal",
                text="Cancel",
                fg_color=("#DC2626", "#B91C1C"),
                hover_color=("#991B1B", "#7F1D1D"),
                text_color="white",
                command=self._handle_cancel
            )
        elif task.status == "completed":
            self.status_badge.configure(text="Completed", fg_color=("#059669", "#10B981"), text_color="white")
            self.cancel_btn.configure(
                state="normal",
                text="✕ Dismiss",
                fg_color=("gray75", "#334155"),
                hover_color=("gray65", "#475569"),
                text_color=("black", "white"),
                command=self._handle_dismiss
            )
        elif task.status == "cancelled":
            self.status_badge.configure(text="Cancelled", fg_color=("gray60", "#64748B"), text_color="white")
            self.cancel_btn.configure(
                state="normal",
                text="✕ Dismiss",
                fg_color=("gray75", "#334155"),
                hover_color=("gray65", "#475569"),
                text_color=("black", "white"),
                command=self._handle_dismiss
            )
        elif task.status == "error":
            self.status_badge.configure(text="Error", fg_color=("#DC2626", "#EF4444"), text_color="white")
            self.cancel_btn.configure(
                state="normal",
                text="✕ Dismiss",
                fg_color=("gray75", "#334155"),
                hover_color=("gray65", "#475569"),
                text_color=("black", "white"),
                command=self._handle_dismiss
            )
            if task.error_message:
                err_clean = task.error_message.replace("ERROR:", "").strip()
                err_clean = err_clean.split("\n")[-1] if "\n" in err_clean else err_clean
                self.stats_label.configure(text=f"❌ {err_clean[:75]}", text_color="#EF4444")


class HistoryItemCard(ctk.CTkFrame):
    """Card representing a completed download in history."""

    def __init__(self, master, data: Dict[str, Any], on_delete=None, **kwargs):
        super().__init__(
            master,
            corner_radius=12,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            **kwargs
        )
        self.data = data
        self.on_delete = on_delete

        self._build_ui()

    def _build_ui(self):
        self.pack_configure(fill="x", padx=10, pady=5)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        # Left Info
        info_col = ctk.CTkFrame(inner, fg_color="transparent")
        info_col.pack(side="left", fill="x", expand=True)

        title = self.data.get("title", "Unknown Video")
        title_lbl = ctk.CTkLabel(
            info_col,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
            wraplength=460,
            justify="left"
        )
        title_lbl.pack(fill="x", pady=(0, 4))

        meta_row = ctk.CTkFrame(info_col, fg_color="transparent")
        meta_row.pack(fill="x")

        plat = self.data.get("platform", "youtube")
        plat_colors = {
            "shorts": ("#EF4444", "white"),
            "youtube": ("#DC2626", "white"),
            "tiktok": ("#06B6D4", "#0F172A"),
            "instagram": ("#E1306C", "white"),
            "pinterest": ("#E60023", "white"),
            "other": ("#6B7280", "white")
        }
        bg_col, txt_col = plat_colors.get(plat, ("#6B7280", "white"))

        p_badge = ctk.CTkLabel(
            meta_row,
            text=get_platform_label(plat).upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=bg_col,
            text_color=txt_col,
            corner_radius=4,
            padx=6,
            pady=1
        )
        p_badge.pack(side="left", padx=(0, 6))

        res = self.data.get("resolution", "MP4")
        r_badge = ctk.CTkLabel(
            meta_row,
            text=res,
            font=ctk.CTkFont(size=10),
            fg_color=("#E2E8F0", "#1E293B"),
            corner_radius=4,
            padx=6,
            pady=1
        )
        r_badge.pack(side="left", padx=(0, 8))

        size = self.data.get("filesize", "0 MB")
        date_str = self.data.get("timestamp", "")
        meta_lbl = ctk.CTkLabel(
            meta_row,
            text=f"{size} • {date_str}",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "#94A3B8")
        )
        meta_lbl.pack(side="left")

        # Right Action Buttons
        btn_col = ctk.CTkFrame(inner, fg_color="transparent")
        btn_col.pack(side="right", padx=(10, 0))

        filepath = self.data.get("filepath", "")
        file_exists = os.path.exists(filepath) if filepath else False

        self.play_btn = ctk.CTkButton(
            btn_col,
            text="▶ Play",
            width=65,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            state="normal" if file_exists else "disabled",
            command=self._play_file
        )
        style_neon_emerald_button(self.play_btn)
        self.play_btn.pack(side="left", padx=3)

        self.folder_btn = ctk.CTkButton(
            btn_col,
            text="📁 Folder",
            width=75,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_folder
        )
        style_glass_button(self.folder_btn)
        self.folder_btn.pack(side="left", padx=3)

        self.del_btn = ctk.CTkButton(
            btn_col,
            text="✕",
            width=28,
            height=28,
            font=ctk.CTkFont(size=12),
            command=self._handle_delete
        )
        style_danger_glass_button(self.del_btn)
        self.del_btn.pack(side="left", padx=3)

    def _play_file(self):
        filepath = self.data.get("filepath", "")
        if filepath and os.path.exists(filepath):
            try:
                os.startfile(filepath)
            except Exception as e:
                print(f"Error opening file: {e}")

    def _open_folder(self):
        filepath = self.data.get("filepath", "")
        if filepath and os.path.exists(filepath):
            try:
                subprocess.Popen(f'explorer /select,"{os.path.normpath(filepath)}"')
                return
            except Exception:
                pass
        os.startfile(config.download_dir)

    def _handle_delete(self):
        if self.on_delete:
            self.on_delete(self.data)


class HistoryView(ctk.CTkFrame):
    """View container managing in-flight downloads and completed history."""

    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=COLOR_WINDOW_BG, **kwargs)
        self.active_cards: Dict[str, ActiveTaskCard] = {}
        self._build_ui()
        download_manager.register_callback(self._on_task_update)
        self._refresh_history_list()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(20, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        title = ctk.CTkLabel(
            title_box,
            text="Download Queue & History",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(anchor="w")

        sub = ctk.CTkLabel(
            title_box,
            text="Monitor in-flight transfers and manage completed video files",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94A3B8")
        )
        sub.pack(anchor="w")

        # Top buttons
        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.pack(side="right")

        open_folder_btn = ctk.CTkButton(
            actions,
            text="📂 Open Save Folder",
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: os.startfile(config.download_dir)
        )
        style_glass_button(open_folder_btn)
        open_folder_btn.pack(side="left", padx=(0, 8))

        self.clear_btn = ctk.CTkButton(
            actions,
            text="🗑 Clear Finished / History",
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._clear_all_history
        )
        style_danger_glass_button(self.clear_btn)
        self.clear_btn.pack(side="left")

        # Segmented switch: Active Queue vs History
        switch_frame = ctk.CTkFrame(self, fg_color="transparent")
        switch_frame.pack(fill="x", padx=30, pady=(5, 10))

        self.tab_selector = ctk.CTkSegmentedButton(
            switch_frame,
            values=["Active Transfers", "Completed Archive"],
            command=self._on_tab_switched,
            height=34,
            selected_color=NEON_CYAN_DEEP,
            selected_hover_color=NEON_CYAN_MID,
            unselected_color=("#E2E8F0", "#1E293B")
        )
        self.tab_selector.set("Active Transfers")
        self.tab_selector.pack(fill="x")

        # Scrollable container for Active Downloads
        self.active_scroll = ctk.CTkScrollableFrame(self, fg_color=COLOR_WINDOW_BG)
        self.active_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.empty_active_lbl = ctk.CTkLabel(
            self.active_scroll,
            text="No active downloads currently running.\nPaste a link in Downloader or Batch tab to begin!",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "#64748B"),
            justify="center"
        )
        self.empty_active_lbl.pack(pady=60)

        # Scrollable container for Completed History
        self.history_scroll = ctk.CTkScrollableFrame(self, fg_color=COLOR_WINDOW_BG)

        self.empty_history_lbl = ctk.CTkLabel(
            self.history_scroll,
            text="No completed downloads yet.",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "#64748B")
        )
        self.empty_history_lbl.pack(pady=60)

        self._refresh_history_list()

    def _on_tab_switched(self, tab: str):
        if tab == "Active Transfers":
            self.history_scroll.pack_forget()
            self.active_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        else:
            self.active_scroll.pack_forget()
            self.history_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 15))
            self._refresh_history_list()

    def _on_task_update(self, task: DownloadTask):
        self.after(0, lambda: self._handle_task_update(task))

    def _handle_task_update(self, task: DownloadTask):
        if task.task_id not in self.active_cards:
            if self.empty_active_lbl.winfo_ismapped():
                self.empty_active_lbl.pack_forget()

            card = ActiveTaskCard(
                self.active_scroll,
                task=task,
                on_cancel=lambda tid: download_manager.cancel_task(tid),
                on_dismiss=self._dismiss_active_card
            )
            self.active_cards[task.task_id] = card
        else:
            card = self.active_cards[task.task_id]
            card.update_task_data(task)

        if task.status in ["completed", "cancelled", "error"]:
            if self.tab_selector.get() == "Completed Archive":
                self._refresh_history_list()

    def _dismiss_active_card(self, task_id: str):
        card = self.active_cards.pop(task_id, None)
        if card:
            card.destroy()
        download_manager.remove_task(task_id)
        if not self.active_cards:
            self.empty_active_lbl.pack(pady=60)

    def _refresh_history_list(self):
        for widget in self.history_scroll.winfo_children():
            if widget != self.empty_history_lbl:
                widget.destroy()

        history_items = config.history
        if not history_items:
            self.empty_history_lbl.pack(pady=60)
        else:
            self.empty_history_lbl.pack_forget()
            for item in history_items:
                HistoryItemCard(
                    self.history_scroll,
                    data=item,
                    on_delete=self._delete_history_item
                )

    def _delete_history_item(self, item_id: str):
        config.remove_history_item(item_id)
        self._refresh_history_list()

    def _clear_all_history(self):
        # 1. Clear completed, cancelled, and error cards from Active Transfers
        finished_ids = [
            tid for tid, card in list(self.active_cards.items())
            if card.task.status in ["completed", "cancelled", "error"]
        ]
        for tid in finished_ids:
            card = self.active_cards.pop(tid, None)
            if card:
                card.destroy()

        download_manager.clear_finished_tasks()

        if not self.active_cards:
            self.empty_active_lbl.pack(pady=60)

        # 2. Clear Completed Archive
        config.clear_history()
        self._refresh_history_list()
