"""
Tube Download JPRO — 3D Glassmorphic Crowned Neon Theme System
Inspired by the 3D Glassmorphic Crowned Neon Icon:
- Obsidian Dark Glass (#0B0F19, #111827, #162032)
- Electric Cyan / Aqua Neon (#00F2FE, #38BDF8, #0284C7)
- Emerald / Mint Neon (#10B981, #00F5A0, #059669)
- Royal 3D Crown Gold (#F59E0B, #FBBF24, #D97706)
"""

import os
from typing import Optional, Tuple
from PIL import Image
import customtkinter as ctk

# --- Core Color Tokens ---
COLOR_WINDOW_BG = ("#F1F5F9", "#0B0F19")
COLOR_SIDEBAR_BG = ("#E2E8F0", "#070A12")
COLOR_CARD_BG = ("#FFFFFF", "#111827")
COLOR_CARD_BORDER = ("#E2E8F0", "#1E293B")
COLOR_CARD_BORDER_GLOW = ("#93C5FD", "#1E3A8A")
COLOR_INPUT_BG = ("#FFFFFF", "#0B1120")
COLOR_INPUT_BORDER = ("#CBD5E1", "#1E293B")

# Neon Accents
NEON_CYAN = "#00F2FE"
NEON_CYAN_MID = "#38BDF8"
NEON_CYAN_DEEP = "#0284C7"
NEON_CYAN_BORDER = "#38BDF8"

NEON_EMERALD = "#10B981"
NEON_EMERALD_BRIGHT = "#00F5A0"
NEON_EMERALD_DEEP = "#059669"
NEON_EMERALD_BORDER = "#34D399"

CROWN_GOLD = "#F59E0B"
CROWN_GOLD_BRIGHT = "#FBBF24"
CROWN_GOLD_DEEP = "#D97706"
CROWN_GOLD_BORDER = "#FDE047"

# Text Colors
TEXT_PRIMARY = ("#0F172A", "#F8FAFC")
TEXT_SECONDARY = ("#64748B", "#94A3B8")
TEXT_MUTED = ("#94A3B8", "#64748B")

# Paths
import sys
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _ROOT_DIR = sys._MEIPASS
else:
    _ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ASSETS_DIR = os.path.join(_ROOT_DIR, "assets")
ICON_PNG_PATH = os.path.join(_ASSETS_DIR, "icon.png")
ICON_ICO_PATH = os.path.join(_ASSETS_DIR, "app_icon.ico")
if not os.path.exists(ICON_ICO_PATH):
    ICON_ICO_PATH = os.path.join(_ASSETS_DIR, "icon.ico")


def get_app_icon_image(size: Tuple[int, int] = (40, 40)) -> Optional[ctk.CTkImage]:
    """Returns the 3D Crowned Neon Icon as a high-DPI CTkImage."""
    if os.path.exists(ICON_PNG_PATH):
        try:
            pil_img = Image.open(ICON_PNG_PATH)
            return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
        except Exception:
            pass
    return None


# --- Button Styling Helpers ---

def style_neon_emerald_button(btn: ctk.CTkButton):
    """Styles a button with the luminous Mint/Emerald Neon download glow."""
    btn.configure(
        fg_color=("#059669", "#059669"),
        hover_color=("#10B981", "#10B981"),
        text_color="#FFFFFF",
        border_width=1,
        border_color=("#10B981", "#34D399"),
        corner_radius=10
    )


def style_neon_cyan_button(btn: ctk.CTkButton):
    """Styles a button with the Electric Cyan / Aqua Neon play glow."""
    btn.configure(
        fg_color=("#0284C7", "#0284C7"),
        hover_color=("#0EA5E9", "#38BDF8"),
        text_color="#FFFFFF",
        border_width=1,
        border_color=("#38BDF8", "#38BDF8"),
        corner_radius=10
    )


def style_crown_gold_button(btn: ctk.CTkButton):
    """Styles a button with the 3D Royal Crown Gold shimmer."""
    btn.configure(
        fg_color=("#D97706", "#F59E0B"),
        hover_color=("#F59E0B", "#FBBF24"),
        text_color="#070A12",
        border_width=1,
        border_color=("#FDE047", "#FDE047"),
        corner_radius=10
    )


def style_glass_button(btn: ctk.CTkButton):
    """Styles a secondary button with frosted obsidian glass aesthetics."""
    btn.configure(
        fg_color=("#E2E8F0", "#1E293B"),
        hover_color=("#CBD5E1", "#334155"),
        text_color=("#0F172A", "#F8FAFC"),
        border_width=1,
        border_color=("#CBD5E1", "#334155"),
        corner_radius=10
    )


def style_danger_glass_button(btn: ctk.CTkButton):
    """Styles a cancel/remove button with frosted ruby glass aesthetics."""
    btn.configure(
        fg_color=("#FEE2E2", "#1E1B2E"),
        hover_color=("#FECACA", "#450A0A"),
        text_color=("#DC2626", "#F87171"),
        border_width=1,
        border_color=("#FCA5A5", "#7F1D1D"),
        corner_radius=10
    )


def style_card(frame: ctk.CTkFrame, corner_radius: int = 12):
    """Applies obsidian glass card styling with subtle metallic border."""
    frame.configure(
        fg_color=COLOR_CARD_BG,
        border_width=1,
        border_color=COLOR_CARD_BORDER,
        corner_radius=corner_radius
    )


def style_input_entry(entry: ctk.CTkEntry, corner_radius: int = 8):
    """Applies sleek dark glass entry styling with subtle cyan focus hint."""
    entry.configure(
        fg_color=COLOR_INPUT_BG,
        border_width=1,
        border_color=COLOR_INPUT_BORDER,
        corner_radius=corner_radius
    )
