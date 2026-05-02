"""
lib/tokens.py — Design tokens (single source of truth).

Dark-mode palette: navy sidebar + dark content surfaces. Emerald green
accent preserved. DM Sans body + JetBrains Mono numerics.
"""
from __future__ import annotations

from pathlib import Path

# Project root — used to locate assets/rgf.css
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Core palette — DARK adaptation of the reference design mock ────────────────
# Design is technically light (#f3f5f9 page, #ffffff cards). User prefers a
# dark adaptation: grey-navy page + deeper-dark cards + navy sidebar.
BG             = "#1d2737"   # page background — grey-navy
SURFACE        = "#0a0f18"   # card / panel background — deepest dark
BG_SOFT        = "#141c2b"   # subtle inner surfaces (pills, hover targets)
BG_ROW_ALT     = "#0d1222"   # table striping
BORDER         = "#2a3750"   # default border
BORDER_SOFT    = "#1a2335"   # row separators / softer dividers
NAVY           = "#0f1729"   # sidebar / header bar
NAVY_LIGHT     = "#1a2744"
TEXT           = "#e6edf3"   # primary text (near-white)
TEXT_2         = "#a7b4c2"   # secondary text
TEXT_3         = "#6e7d92"   # tertiary / muted text
NAV_TEXT       = "#7a8599"   # sidebar nav idle
NAV_ICON       = "#566378"   # sidebar nav icon idle
NAV_MUTED      = "#64748b"   # sidebar subtitles
GRID           = "#1e2840"   # plot grid lines

# ── Accent (green / emerald) — dark-theme tuned ──────────────────────────────
ACCENT         = "#10b981"   # brand primary
ACCENT_DARK    = "#059669"   # primary button hover
ACCENT_LIGHT   = "#064e3b"   # tint bg (dark green tint)
ACCENT_SOFT    = "#34d399"   # progress bar lighter stop
ACCENT_DEEP    = "#a7f3d0"   # text on dark green surfaces
ACCENT_BORDER  = "#065f46"   # tag border
ACCENT_TINT    = "#0f2d1f"   # hover bg (dark green tint)

# ── Neutrals ──────────────────────────────────────────────────────────────────
SLATE          = "#64748b"
SLATE_MUTED    = "#94a3b8"
HOVER_SOFT     = "#1e2840"   # button hover bg (dark)
UPLOAD_BG      = "#141c2b"   # file uploader default bg (dark)
WHITE          = "#ffffff"

# ── Status colours (deltas, alerts, badges) — dark-theme tuned ───────────────
DELTA_UP_BG    = "#0f2d1d"
DELTA_UP_TEXT  = "#4ade80"
DELTA_DOWN_BG  = "#2d1515"
DELTA_DOWN_TEXT = "#f87171"
WARN_BG        = "#2a200e"
WARN_BORDER    = "#78350f"
WARN_TEXT      = "#fbbf24"
WARN_ICON      = "#f59e0b"

# ── Cloud-provider accents (unchanged hex, work on dark bg too) ──────────────
GOOGLE_GREEN   = "#34a853"
GOOGLE_BLUE    = "#4285f4"

# ── Radii ─────────────────────────────────────────────────────────────────────
RADIUS_SM = 7
RADIUS_MD = 10
RADIUS_LG = 14

# ── Sidebar dimensions ────────────────────────────────────────────────────────
SIDEBAR_W          = 240
SIDEBAR_W_COLLAPSED = 64


def tokens_dict() -> dict[str, str | int]:
    """Flat dict for CSS template interpolation via ``str.format_map``.

    Every name here must appear verbatim as ``{NAME}`` in assets/rgf.css.
    """
    return {
        "BG":             BG,
        "SURFACE":        SURFACE,
        "BG_SOFT":        BG_SOFT,
        "BG_ROW_ALT":     BG_ROW_ALT,
        "BORDER":         BORDER,
        "BORDER_SOFT":    BORDER_SOFT,
        "NAVY":           NAVY,
        "NAVY_LIGHT":     NAVY_LIGHT,
        "TEXT":           TEXT,
        "TEXT_2":         TEXT_2,
        "TEXT_3":         TEXT_3,
        "NAV_TEXT":       NAV_TEXT,
        "NAV_ICON":       NAV_ICON,
        "NAV_MUTED":      NAV_MUTED,
        "GRID":           GRID,
        "ACCENT":         ACCENT,
        "ACCENT_DARK":    ACCENT_DARK,
        "ACCENT_LIGHT":   ACCENT_LIGHT,
        "ACCENT_SOFT":    ACCENT_SOFT,
        "ACCENT_DEEP":    ACCENT_DEEP,
        "ACCENT_BORDER":  ACCENT_BORDER,
        "ACCENT_TINT":    ACCENT_TINT,
        "SLATE":          SLATE,
        "SLATE_MUTED":    SLATE_MUTED,
        "HOVER_SOFT":     HOVER_SOFT,
        "UPLOAD_BG":      UPLOAD_BG,
        "WHITE":          WHITE,
        "DELTA_UP_BG":    DELTA_UP_BG,
        "DELTA_UP_TEXT":  DELTA_UP_TEXT,
        "DELTA_DOWN_BG":  DELTA_DOWN_BG,
        "DELTA_DOWN_TEXT": DELTA_DOWN_TEXT,
        "WARN_BG":        WARN_BG,
        "WARN_BORDER":    WARN_BORDER,
        "WARN_TEXT":      WARN_TEXT,
        "WARN_ICON":      WARN_ICON,
        "GOOGLE_GREEN":   GOOGLE_GREEN,
        "GOOGLE_BLUE":    GOOGLE_BLUE,
        "RADIUS_SM":      RADIUS_SM,
        "RADIUS_MD":      RADIUS_MD,
        "RADIUS_LG":      RADIUS_LG,
        "SIDEBAR_W":      SIDEBAR_W,
        "SIDEBAR_W_COLLAPSED": SIDEBAR_W_COLLAPSED,
    }
