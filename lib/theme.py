"""
lib/theme.py — Theme installation.

Loads assets/rgf.css (a template interpolated with lib.tokens). Plotly
and ECharts have been removed from the project; every chart now uses
the Canvas-based panel in ``lib/charts/canvas``, so no chart-library
templates need registering here.

Public surface (used by app.py and views/):
    install_theme()   — called once per session by app.py
    COLORS            — legacy-friendly dict, backed by lib.tokens
    CHART_PALETTE     — re-export of lib.tokens.CHART_PALETTE
"""
from __future__ import annotations

import streamlit as st

from lib.tokens import (
    ACCENT, ACCENT_DARK, ACCENT_LIGHT,
    BG, SURFACE, BORDER,
    NAVY, TEXT, TEXT_2, TEXT_3,
    PROJECT_ROOT, tokens_dict,
)

_CSS_PATH = PROJECT_ROOT / "assets" / "rgf.css"


# ── Legacy public dict (kept for chart_builder + any external callers) ───────
COLORS = {
    "accent":      ACCENT,
    "accent_dark": ACCENT_DARK,
    "accent_light": ACCENT_LIGHT,
    "bg":          BG,
    "bg_card":     SURFACE,
    "border":      BORDER,
    "text":        TEXT,
    "text_muted":  TEXT_2,
    "text_subtle": TEXT_3,
    "navy":        NAVY,
}


# ``mtime`` is a cache key — when the CSS file changes on disk, the mtime
# changes, Streamlit's @cache_resource treats it as a new function call
# and re-reads the template. Without this, edits to assets/rgf.css only
# took effect on a full `streamlit run` restart — hot-reload via F5
# picked up the old cached string and new CSS rules wouldn't apply.
@st.cache_resource
def _load_css(mtime: float = 0.0) -> str:
    template = _CSS_PATH.read_text(encoding="utf-8")
    return template.format_map(tokens_dict())


def install_theme() -> None:
    """Inject the CSS template. Re-reads from disk if the file changed."""
    mtime = _CSS_PATH.stat().st_mtime
    st.markdown(f"<style>{_load_css(mtime)}</style>", unsafe_allow_html=True)
