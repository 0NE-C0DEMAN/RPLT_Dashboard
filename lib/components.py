"""
lib/components.py — Reusable UI components.

Shared shell helpers used by every view. Styles live in assets/rgf.css
under the .rgf-* class tree.

Public:
    page_header(title, subtitle="", right_html="")  — title + subtitle + actions
    badge(text, color="green")                      — inline coloured pill
    empty_state(icon, title, message)               — centered placeholder

Bespoke KPI cards (with sparklines, accent variants) are rendered
in-view — see ``views/dashboard.py::_render_kpi_row`` and
``views/cycle_analysis.py::_render_cycle_kpi_row``.
"""
from __future__ import annotations

import html as html_mod

import streamlit as st

from lib.icons import ICONS, svg


# ── Page header ──────────────────────────────────────────────────────────────
def page_header(title: str, subtitle: str = "", right_html: str = "") -> None:
    """Render a page title + subtitle with optional right-aligned action area.

    ``right_html`` is raw HTML injected into the actions slot (e.g. badges,
    SmallBtn markup). Title/subtitle are escaped.
    """
    sub = f'<p class="rgf-pghdr-sub">{html_mod.escape(subtitle)}</p>' if subtitle else ""
    actions = f'<div class="rgf-pghdr-actions">{right_html}</div>' if right_html else ""
    st.markdown(
        f'<div class="rgf-pghdr">'
        f'<div>'
        f'<h1 class="rgf-pghdr-title">{html_mod.escape(title)}</h1>'
        f'{sub}'
        f'</div>'
        f'{actions}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Badge ────────────────────────────────────────────────────────────────────
def badge(text: str, color: str = "green") -> str:
    """Return an inline HTML pill. ``color`` ∈ {green, blue, amber, violet, cyan, gray}."""
    color_cls = f"rgf-badge-{color}" if color in {"green", "blue", "amber", "violet", "cyan", "gray"} else "rgf-badge-gray"
    return f'<span class="rgf-badge {color_cls}">{html_mod.escape(text)}</span>'


# ── Empty state ──────────────────────────────────────────────────────────────
def empty_state(icon: str, title: str, message: str) -> None:
    """Centered placeholder.

    ``icon`` resolution order:
      1. If it matches a key in ``lib.icons.ICONS`` → render as an SVG
         (stroke-only, picks up the .rgf-empty-icon colour via currentColor).
      2. Otherwise, if truthy, render the string verbatim inside the icon
         slot (emoji fallback — kept for back-compat with any legacy call).
      3. If empty → omit the icon slot entirely.
    """
    if icon in ICONS:
        inner = svg(icon, size=36)
        icon_html = f'<div class="rgf-empty-icon rgf-empty-icon-svg">{inner}</div>'
    elif icon:
        icon_html = (
            f'<div class="rgf-empty-icon">{html_mod.escape(icon)}</div>'
        )
    else:
        icon_html = ''
    st.markdown(
        f'<div class="rgf-empty-state">'
        f'{icon_html}'
        f'<div class="rgf-empty-title">{html_mod.escape(title)}</div>'
        f'<div class="rgf-empty-message">{html_mod.escape(message)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
