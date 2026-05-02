"""RGF Geotechnical Analysis — Streamlit entry point.

Renders the app shell (sidebar, hidden trigger buttons, JS bridge) and
dispatches to the active view. Most of the heavy lifting lives in
sibling modules:

  ``lib.shell``    — sidebar HTML, NAV table, footer
  ``lib.bridge``   — JS click-dispatch (visible HTML → hidden ``st.button``)
  ``lib.theme``    — CSS template loader
  ``views/*.py``   — one module per top-level view

SPA-style routing pattern (no full-page reload on nav clicks):

    Visible nav button has ``data-nav="<view_id>"``.
    JS bridge clicks the matching hidden ``st.button(key="__nav_<vid>")``.
    Streamlit reruns; the script reads ``st.session_state.view`` and
    renders the matching view module. The URL stays in sync via
    ``st.query_params["view"]``.
"""
from __future__ import annotations

import streamlit as st

# Page config must be the FIRST Streamlit call.
st.set_page_config(
    page_title="RGF Geotechnical Analysis",
    # Material Symbols shortcode — proper vector favicon in the
    # browser tab (no emoji glyph). Any Material Symbols name works.
    page_icon=":material/ssid_chart:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from lib.bridge import inject_click_bridge
from lib.cache import ensure_all_imported_registered
from lib.shell import NAV, VALID_VIEW_IDS, render_sidebar
from lib.state import imported_tables, session_id
from lib.theme import install_theme


install_theme()
session_id()
ensure_all_imported_registered(imported_tables())


# ── Active view from URL or default ─────────────────────────────────────────
if "view" not in st.session_state:
    qp = st.query_params.get("view", "dashboard")
    if isinstance(qp, list):
        qp = qp[0] if qp else "dashboard"
    st.session_state.view = qp if qp in VALID_VIEW_IDS else "dashboard"

active_view = st.session_state.view


# ── Sidebar collapse state ──────────────────────────────────────────────────
# Click the logo (data-action="toggle-sidebar") → JS bridge clicks
# the hidden ``__sidebar_toggle`` button → flips the session flag and
# reruns. CSS in assets/rgf.css does the actual width / margin shift.
if "sidebar_collapsed" not in st.session_state:
    st.session_state.sidebar_collapsed = False
if st.button("·", key="__sidebar_toggle"):
    st.session_state.sidebar_collapsed = not st.session_state.sidebar_collapsed
    st.rerun()


# ── Hidden trigger buttons (one per nav item) ──────────────────────────────
# Real ``st.button``s — clicks go over the websocket (no browser nav).
# The visible nav items in lib/shell dispatch into these via JS.
for vid, _label, _icon in NAV:
    if st.button("·", key=f"__nav_{vid}"):
        st.session_state.view = vid
        st.query_params["view"] = vid
        st.rerun()


# ── Visible sidebar + JS bridge ─────────────────────────────────────────────
render_sidebar(active_view)
inject_click_bridge()


# ── Dispatch to the active view ─────────────────────────────────────────────
# Imports are deferred (inside each branch) so a failure in one view
# can't crash the whole app — the others still load.
if active_view == "dashboard":
    from views.dashboard import render as _render
elif active_view == "import":
    from views.import_data import render as _render
elif active_view == "standard":
    from views.standard_analysis import render as _render
elif active_view == "upm":
    from views.upm_analysis import render as _render
elif active_view == "cycles":
    from views.cycle_analysis import render as _render
elif active_view == "builder":
    from views.chart_builder import render as _render
elif active_view == "report":
    from views.report_builder import render as _render
elif active_view == "data":
    from views.raw_sample import render as _render
elif active_view == "settings":
    from views.settings import render as _render
else:
    from views.dashboard import render as _render

_render()
