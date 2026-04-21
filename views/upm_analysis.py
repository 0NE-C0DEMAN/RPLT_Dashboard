"""UPM Analysis — Unloading-Point-Method force decomposition.

Charts mirror the reference notebook (RPLT_Fully_Integrated.ipynb) exactly:

  • Plot 8 — UPM Force Components vs Time     (Fma, Fkx, Total Force overlay)
  • Plot 7 — UPM Force vs Displacement         (Fma, Fkx, Total Force vs disp)

The raw Load trace is deliberately absent from this view — it's 3-4 orders
of magnitude larger than the force components and would dwarf them on a
shared y-axis. It already lives on Dashboard / Standard Analysis anyway.

Layout (vertical stack, full width per chart so the fine structure of
the force components stays legible):

    ┌─────────────────────────────────────────────────┐
    │ UPM Analysis                        [UPM badge] │
    │ Unloading-Point-Method force decomposition      │
    ├─────────────────────────────────────────────────┤
    │ ProcessingToolbar                               │
    ├─────────────────────────────────────────────────┤
    │ Force Components vs Time (full width, 280 px)   │
    ├─────────────────────────────────────────────────┤
    │ Force vs Displacement   (full width, 280 px)    │
    ├─────────────────────────────────────────────────┤
    │ UPM Parameters (4-cell grid, full width)        │
    └─────────────────────────────────────────────────┘
"""
from __future__ import annotations

import html as html_mod

import numpy as np
import streamlit as st

from lib.cache import ensure_registered, table_version
from lib.charts.canvas import chart_panel, icon_btn, series, series_xy, small_btn
from lib.charts.helpers import detect_event_window
from lib.components import badge, empty_state, page_header
from lib.processing import (
    COL_DISP, COL_LOAD, COL_TIME,
    pick_column, render_controls, run_processing,
)
from lib.queries import column_names
from lib.state import get_active_info


# Colours match the notebook's matplotlib reference + our design tokens.
_C_FMA   = "#3b82f6"   # blue — inertial (m·a)
_C_FKX   = "#f59e0b"   # amber — elastic (k·x)
_C_TOTAL = "#8b5cf6"   # violet — summed total (plotted dashed per notebook)


def render() -> None:
    info = get_active_info()
    if info is None:
        page_header("UPM Analysis", "Unloading-Point-Method force decomposition")
        empty_state(
            "wave",
            "No active dataset",
            "Import a file (or click Load Demo Dataset) to populate the UPM charts.",
        )
        return

    ensure_registered(info.table_name)
    v = table_version(info.table_name)
    cols = column_names(info.table_name, v) or []

    page_header(
        "UPM Analysis",
        "Unloading-Point-Method force decomposition",
        right_html=badge("UPM", "violet"),
    )

    time_col = st.session_state.get("rgf_map_time") or pick_column(
        cols, ["time (s)", "time", "t"])
    accel_col = st.session_state.get("rgf_map_accel") or pick_column(
        cols, ["scaled (m/s2)", "acceleration scaled", "accel scaled", "acceleration raw", "accel"])
    load_col = st.session_state.get("rgf_map_load") or pick_column(
        cols, ["load (kn)", "load summ", "load sum", "load scaled", "load", "force", "LOAD"])

    time_col, accel_col, load_col, params = render_controls(
        cols, time_col, accel_col, load_col, key_prefix="upm",
    )

    computed = run_processing(
        info.table_name, v, time_col, accel_col, load_col, params,
    )
    if computed is None or computed.empty:
        empty_state("alert", "Processing failed",
                    "Check the column mapping — the columns must be numeric.")
        return

    if "Fma (kN)" not in computed.columns:
        empty_state(
            "alert", "UPM not computed",
            "Set UPM mass and stiffness in the toolbar and reprocess.",
        )
        return

    # ── Event-window crop ────────────────────────────────────────────────────
    # Fma/Fkx are only meaningful during the impact. Cropping to the event
    # window keeps the charts focused on the milliseconds that matter — same
    # approach the notebook takes implicitly by only calling create_plots()
    # on a single-event dataframe.
    t     = computed[COL_TIME].to_numpy()
    load  = computed[COL_LOAD].to_numpy()
    fma   = computed["Fma (kN)"].to_numpy()
    fkx   = computed["Fkx (kN)"].to_numpy()
    total = computed["Total Force (kN)"].to_numpy()
    disp_mm = computed[COL_DISP].to_numpy() * 1000.0

    ev_start, ev_end = detect_event_window(
        load, threshold_pct=0.02, buffer_pct=0.3, min_buffer=40,
    )
    ev_len = ev_end - ev_start
    target_n = 1000
    if ev_len > target_n:
        idx = np.linspace(ev_start, ev_end - 1, target_n).astype(int)
    else:
        idx = np.arange(ev_start, ev_end)
    t_ev, fma_ev, fkx_ev, total_ev, disp_ev = (
        t[idx], fma[idx], fkx[idx], total[idx], disp_mm[idx]
    )

    # ── Row 1: Force Components vs Time (notebook Plot 8) ────────────────────
    # Overlay / Stacked toggle is wired up in canvas.js (group="mode") —
    # "stacked" forces every series into filled-area mode, "overlay" keeps
    # them as lines. The client applies it with zero server round-trip.
    chart_panel(
        "UPM Force Components vs Time",
        [
            series(fma_ev,   _C_FMA,   "F=ma (Inertia)", filled=False),
            series(fkx_ev,   _C_FKX,   "F=kx (Spring)",  filled=False),
            series(total_ev, _C_TOTAL, "Total Force",    filled=False, dashed=True),
        ],
        x_data=t_ev,
        x_label="Time (s)",
        y_label="Force (kN)",
        height=280,
        actions_html=(
            small_btn("Overlay", active=True,  group="mode", data={"mode": "overlay"})
            + small_btn("Stacked", active=False, group="mode", data={"mode": "stacked"})
            + icon_btn("download", title="Export")
        ),
        key="upm_force_time",
        annotations=[
            # Zero reference for easy sign-change reading.
            {"type": "hline", "y": 0.0, "color": "#94a3b8"},
        ],
    )

    # ── Row 2: Force vs Displacement (notebook Plot 7) ───────────────────────
    # XY mode because disp is non-monotonic — the plate moves down, peaks,
    # then rebounds through disp=0; a shared-x array would squash the
    # return path.
    fma_xy   = list(zip(disp_ev.tolist(), fma_ev.tolist()))
    fkx_xy   = list(zip(disp_ev.tolist(), fkx_ev.tolist()))
    total_xy = list(zip(disp_ev.tolist(), total_ev.tolist()))

    chart_panel(
        "UPM Force vs Displacement",
        [
            series_xy(fma_xy,   _C_FMA,   "F=ma (Inertia)"),
            series_xy(fkx_xy,   _C_FKX,   "F=kx (Spring)"),
            series_xy(total_xy, _C_TOTAL, "Total Force", dashed=True),
        ],
        x_data=[],
        x_label="Displacement (mm)",
        y_label="Force (kN)",
        height=280,
        actions_html=icon_btn("download", title="Export"),
        key="upm_force_disp",
        annotations=[
            # Origin cross — lets the viewer read off the force at rest
            # and the displacement where forces cross zero.
            {"type": "vline", "x": 0.0, "color": "#94a3b8"},
            {"type": "hline", "y": 0.0, "color": "#94a3b8"},
        ],
    )

    # ── UPM Parameters panel ─────────────────────────────────────────────────
    _render_upm_params_panel(computed, params)


# ── UPM Parameters panel ─────────────────────────────────────────────────────
def _render_upm_params_panel(computed, params: dict) -> None:
    """Render the 4-cell UPM Parameters panel (matches views.jsx lines 329-344)."""
    peak_fma   = float(computed["Fma (kN)"].abs().max())
    peak_fkx   = float(computed["Fkx (kN)"].abs().max())
    peak_total = float(computed["Total Force (kN)"].abs().max())
    mobilized  = peak_fkx  # per Unloading-Point Method convention

    cells = [
        ("Mass",                 f"{params['upm_mass']:,.0f}",      "kg"),
        ("Stiffness",            f"{params['upm_stiffness']:,.0f}", "N/m"),
        ("Peak F=ma",            f"{peak_fma:,.2f}",                "kN"),
        ("Peak F=kx",            f"{peak_fkx:,.4f}",                "kN"),
        ("UPM Capacity",         f"{peak_total:,.2f}",              "kN"),
        ("Mobilized Resistance", f"{mobilized:,.4f}",               "kN"),
    ]

    cells_html = "".join(
        f'<div class="rgf-upm-cell">'
        f'<div class="rgf-upm-cell-label">{html_mod.escape(label)}</div>'
        f'<span class="rgf-upm-cell-value">{html_mod.escape(value)}</span>'
        f'<span class="rgf-upm-cell-unit">{html_mod.escape(unit)}</span>'
        f'</div>'
        for label, value, unit in cells
    )

    st.markdown(
        f'<div class="rgf-upm-panel">'
        f'<div class="rgf-upm-hdr">'
        f'<span class="rgf-upm-title">UPM Parameters</span>'
        f'</div>'
        f'<div class="rgf-upm-grid">{cells_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
