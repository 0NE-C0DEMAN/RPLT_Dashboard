"""lib/shell.py — App shell rendering.

Pulls the static HTML pieces of ``app.py`` (sidebar nav + footer) into
a self-contained module so the entry script stays small and the shell
chrome can be unit-tested / restyled in isolation.

Public:
    ``NAV``                       — list of (view_id, label, icon_name) tuples
    ``VALID_VIEW_IDS``            — set of valid IDs for URL/state validation
    ``render_sidebar(active)``    — render the nav rail + active-test footer
"""
from __future__ import annotations

import html as html_mod

import streamlit as st

from lib.icons import svg
from lib.state import get_active_info


# ── Navigation metadata ──────────────────────────────────────────────────────
# Order = visible top-to-bottom. ``icon_name`` must match a key in
# ``lib.icons.ICONS``. Adding a row here + a dispatch branch in app.py
# is all it takes to introduce a new view.
NAV: list[tuple[str, str, str]] = [
    ("dashboard", "Dashboard",         "dashboard"),
    ("import",    "Import Data",       "upload"),
    ("standard",  "Standard Analysis", "chart"),
    ("upm",       "UPM Analysis",      "wave"),
    ("cycles",    "Cycle Analysis",    "cycle"),
    ("builder",   "Chart Builder",     "layers"),
    ("report",    "Report Builder",    "report"),
    ("data",      "Raw Data",          "table"),
    ("settings",  "Settings",          "settings"),
]
VALID_VIEW_IDS: set[str] = {v for v, _, _ in NAV}


def _footer_html() -> str:
    """Sidebar footer block — shows the active-test summary or a
    placeholder when no file has been imported yet."""
    info = get_active_info()
    if not info:
        return (
            '<div class="rgf-sb-foot-lbl">No Active Test</div>'
            '<div class="rgf-sb-foot-name">Import a file to begin</div>'
        )
    name = html_mod.escape(info.source_filename or info.table_name)
    meta = f"{info.row_count:,} rows · {info.column_count} cols"
    return (
        '<div class="rgf-sb-foot-lbl">Active Test</div>'
        f'<div class="rgf-sb-foot-name">{name}</div>'
        f'<div class="rgf-sb-foot-meta">{meta}</div>'
    )


def render_sidebar(active_view: str) -> None:
    """Render the static sidebar HTML.

    Visible nav items dispatch to hidden ``st.button``s via the JS
    bridge in ``lib.bridge`` (data-nav="<view_id>"). The logo doubles
    as the collapse toggle (data-action="toggle-sidebar").
    """
    nav_items: list[str] = []
    for vid, label, icon_name in NAV:
        cls = "rgf-nav-item" + (" active" if vid == active_view else "")
        # data-nav dispatches to the hidden st.button via the JS bridge.
        # data-label drives the collapsed-state hover tooltip.
        nav_items.append(
            f'<button type="button" class="{cls}" data-nav="{vid}" '
            f'data-label="{html_mod.escape(label)}">'
            f'<span class="rgf-nav-icon">{svg(icon_name, size=18)}</span>'
            f'<span class="rgf-nav-label">{html_mod.escape(label)}</span>'
            f'</button>'
        )

    sidebar_cls = "rgf-sidebar"
    if st.session_state.get("sidebar_collapsed"):
        sidebar_cls += " rgf-sidebar-collapsed"

    st.markdown(
        f"""
        <div class="{sidebar_cls}">
          <div class="rgf-logo" data-action="toggle-sidebar" title="Toggle sidebar">
            <div class="rgf-logo-mark">RP</div>
            <div class="rgf-logo-text">
              <div class="rgf-logo-title">RPLT</div>
              <div class="rgf-logo-sub">RGF Geotechnical</div>
            </div>
          </div>
          <div class="rgf-nav-list">{"".join(nav_items)}</div>
          <div class="rgf-sidebar-footer">{_footer_html()}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
