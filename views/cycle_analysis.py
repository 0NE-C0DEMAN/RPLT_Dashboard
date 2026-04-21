"""Cycle Analysis — per-cycle drilldown + side-by-side comparison.

Matches views.jsx::CycleView 1:1:

    ┌─────────────────────────────────────────────────┐
    │ Cycle Analysis    [Cycle 1] [Cycle 2] [Cycle 3] │
    │ Compare individual impact cycles side by side   │
    ├─────────────────────────────────────────────────┤
    │ Peak Load | Max Disp | Set Disp | Peak Vel | Dur│  (5 KPI cards)
    ├──────────────────────────┬──────────────────────┤
    │ Cycle N — Load vs Time   │ Cycle N — Disp vs T  │  (240 px)
    ├──────────────────────────┴──────────────────────┤
    │ Cycle Overlay — Load Comparison                 │  (260 px, all cycles)
    └─────────────────────────────────────────────────┘

Cycle selector uses the same visible-SmallBtn + hidden-st.button + JS-bridge
pattern as the nav bar: click the visible button → JS finds the matching
.st-key-__cycle_N hidden button → Streamlit reruns with the new cycle
active. See app.py for the bridge that wires data-cycle → hidden buttons.
"""
from __future__ import annotations

import html as html_mod

import numpy as np
import streamlit as st

from lib.cache import ensure_registered, table_version
from lib.charts.canvas import chart_panel, icon_btn, series
from lib.components import empty_state, page_header
from lib.cycles import cycle_window, detect_cycles
from lib.processing import (
    COL_DISP, COL_LOAD, COL_TIME,
    pick_column, run_processing, get_params,
)
from lib.queries import column_names
from lib.state import get_active_info


_SESSION_KEY = "rgf_active_cycle"   # 1-based cycle number


# Cycle-overlay palette — cycles through these in order.
_CYCLE_PALETTE = [
    "#10b981", "#3b82f6", "#f59e0b", "#8b5cf6",
    "#ef4444", "#06b6d4", "#ec4899", "#84cc16",
]


def render() -> None:
    info = get_active_info()
    if info is None:
        page_header("Cycle Analysis", "Compare individual impact cycles side by side")
        empty_state(
            "cycle",
            "No active dataset",
            "Import a file (or click Load Demo Dataset) to populate cycle analysis.",
        )
        return

    ensure_registered(info.table_name)
    v = table_version(info.table_name)
    cols = column_names(info.table_name, v) or []

    time_col = st.session_state.get("rgf_map_time")  or pick_column(cols, ["time (s)", "time", "t"])
    accel_col = st.session_state.get("rgf_map_accel") or pick_column(cols, ["scaled (m/s2)", "acceleration scaled", "accel scaled", "acceleration raw", "accel"])
    load_col = st.session_state.get("rgf_map_load")   or pick_column(cols, ["load (kn)", "load summ", "load sum", "load scaled", "load", "force", "LOAD"])

    if not (time_col and accel_col and load_col):
        page_header("Cycle Analysis", "Compare individual impact cycles side by side")
        empty_state("sliders", "Column mapping incomplete",
                    "Go to Import Data → Column Mapping and pick Time, Acceleration, Load.")
        return

    computed = run_processing(info.table_name, v, time_col, accel_col, load_col, get_params())
    if computed is None or computed.empty:
        page_header("Cycle Analysis", "Compare individual impact cycles side by side")
        empty_state("alert", "Processing failed", "Column mapping may be invalid — check the types.")
        return

    cycles = detect_cycles(computed)
    if not cycles:
        page_header("Cycle Analysis", "Compare individual impact cycles side by side")
        empty_state("cycle", "No cycles detected",
                    "Load signal didn't cross the 30% peak threshold.")
        return

    # ── Active cycle state + hidden triggers ─────────────────────────────────
    total_cycles = len(cycles)
    active_no = _get_active_cycle_no(total_cycles)

    # Hidden st.button per cycle — the JS bridge (app.py) clicks these when a
    # visible data-cycle="N" SmallBtn is tapped. Writing to session state
    # here and rerunning makes the new cycle take effect.
    for c in cycles:
        if st.button("·", key=f"__cycle_{c['cycle_no']}"):
            st.session_state[_SESSION_KEY] = c["cycle_no"]
            st.rerun()

    # ── Page header with cycle-selector SmallBtns ────────────────────────────
    selector_buttons = "".join(
        (
            '<button type="button" class="rgf-btn-sm'
            + (' active' if c['cycle_no'] == active_no else '')
            + f'" data-cycle="{c["cycle_no"]}">Cycle {c["cycle_no"]}</button>'
        )
        for c in cycles
    )
    page_header(
        "Cycle Analysis",
        "Compare individual impact cycles side by side",
        right_html=selector_buttons,
    )

    # ── Active cycle slice + KPIs ────────────────────────────────────────────
    active_cycle = next(c for c in cycles if c["cycle_no"] == active_no)
    seg = cycle_window(computed, active_cycle)
    disp_unit, disp_scale = _pick_disp_unit(active_cycle["max_disp_m"])

    _render_cycle_kpi_row(active_cycle, disp_unit, disp_scale)

    # ── Row: Load vs Time + Displacement vs Time (per cycle) ─────────────────
    t_seg = seg[COL_TIME].to_numpy()
    load_seg = seg[COL_LOAD].to_numpy()
    disp_seg = seg[COL_DISP].to_numpy() * disp_scale

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        chart_panel(
            f"Cycle {active_no} — Load vs Time",
            [series(load_seg, "#10b981", "Load (kN)")],
            x_data=t_seg,
            x_label="Time (s)", y_label="Load (kN)",
            height=240,
            actions_html=icon_btn("download", title="Export"),
            key=f"cyc_{active_no}_load",
        )
    with c2:
        chart_panel(
            f"Cycle {active_no} — Displacement vs Time",
            [series(disp_seg, "#3b82f6", f"Displacement ({disp_unit})")],
            x_data=t_seg,
            x_label="Time (s)", y_label=f"Displacement ({disp_unit})",
            height=240,
            actions_html=icon_btn("download", title="Export"),
            key=f"cyc_{active_no}_disp",
        )

    # ── Full-width cycle overlay (all cycles on one Load-vs-Time chart) ─────
    _render_cycle_overlay(computed, cycles)


# ── Cycle selector helpers ───────────────────────────────────────────────────
def _get_active_cycle_no(total_cycles: int) -> int:
    """Return the currently-active cycle number (1-based), clamped to range."""
    n = st.session_state.get(_SESSION_KEY, 1)
    if not isinstance(n, int) or n < 1 or n > total_cycles:
        n = 1
        st.session_state[_SESSION_KEY] = n
    return n


# ── KPI row (5 cards) ────────────────────────────────────────────────────────
def _render_cycle_kpi_row(c: dict, disp_unit: str, disp_scale: float) -> None:
    """Five KPI cards matching views.jsx::CycleView lines 365-370."""
    peak_load = c["peak_load"]
    max_disp  = c["max_disp_m"] * disp_scale
    set_disp  = c["set_disp_m"] * disp_scale
    peak_vel_mms = c["peak_vel"] * 1000.0
    duration = c["duration_s"]

    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    with c1: _kpi("Peak Load",        _fmt_num(peak_load),                 "kN",      accent=True)
    with c2: _kpi("Max Displacement", _fmt_num(max_disp, decimals=3),      disp_unit)
    with c3: _kpi("Set Displacement", _fmt_num(set_disp, decimals=3),      disp_unit)
    with c4: _kpi("Peak Velocity",    _fmt_num(peak_vel_mms, decimals=2),  "mm/s")
    with c5: _kpi("Duration",         _fmt_num(duration, decimals=4),      "s")


def _kpi(label: str, value: str, unit: str, *, accent: bool = False) -> None:
    accent_cls = " rgf-kpi-accent" if accent else ""
    st.markdown(
        f'<div class="rgf-kpi{accent_cls}">'
        f'<div class="rgf-kpi-top">'
        f'<span class="rgf-kpi-label">{html_mod.escape(label)}</span>'
        f'</div>'
        f'<div class="rgf-kpi-row">'
        f'<span class="rgf-kpi-value">{html_mod.escape(value)}</span>'
        f'<span class="rgf-kpi-unit">{html_mod.escape(unit)}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Cycle Overlay (all cycles, time-normalized) ──────────────────────────────
def _render_cycle_overlay(df, cycles: list[dict]) -> None:
    """All cycles on one Load-vs-Time chart, time-normalized to each cycle's
    window start so the curves align left-to-right for comparison."""
    # Find the longest window so we can use its x-axis. Then interpolate
    # each cycle's load onto that shared time base, zero-origin.
    max_len = max(c["end_idx"] - c["start_idx"] for c in cycles)
    t_ref = np.linspace(0, 1, max_len)  # normalized [0..1] time within cycle

    series_list = []
    for i, c in enumerate(cycles):
        seg = df.iloc[c["start_idx"]:c["end_idx"]]
        if len(seg) < 2:
            continue
        t_local = seg[COL_TIME].to_numpy()
        t_norm = (t_local - t_local[0]) / max(1e-9, (t_local[-1] - t_local[0]))
        load_resampled = np.interp(t_ref, t_norm, seg[COL_LOAD].to_numpy())
        color = _CYCLE_PALETTE[i % len(_CYCLE_PALETTE)]
        series_list.append(
            series(load_resampled, color, f"Cycle {c['cycle_no']}", filled=False)
        )

    # Compute elapsed-time axis in ms based on median cycle duration.
    mean_dur = float(np.mean([c["duration_s"] for c in cycles]))
    t_axis_ms = t_ref * mean_dur * 1000.0  # ms

    chart_panel(
        "Cycle Overlay — Load Comparison",
        series_list,
        x_data=t_axis_ms,
        x_label="Elapsed (ms, normalized)",
        y_label="Load (kN)",
        height=260,
        actions_html=(
            f'<span class="rgf-badge rgf-badge-cyan">All cycles ({len(cycles)})</span>'
        ),
        key="cyc_overlay",
    )


# ── Small helpers ────────────────────────────────────────────────────────────
def _pick_disp_unit(d_max_m: float) -> tuple[str, float]:
    """Return (unit-label, scale-factor-from-metres) for a given magnitude."""
    if d_max_m > 0 and d_max_m < 0.01:
        return "µm", 1e6
    if d_max_m < 1:
        return "mm", 1000.0
    return "m", 1.0


def _fmt_num(val: float, decimals: int | None = None) -> str:
    if decimals is not None:
        return f"{val:,.{decimals}f}"
    a = abs(val)
    if a == 0:
        return "0"
    if a < 0.01:
        return f"{val:.4f}"
    if a < 100:
        return f"{val:,.2f}"
    if a < 10_000:
        return f"{val:,.1f}"
    return f"{val:,.0f}"
