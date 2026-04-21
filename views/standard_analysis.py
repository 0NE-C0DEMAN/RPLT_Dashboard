"""Standard Analysis view — Canvas charts with RPLT-specific annotations.

Layout:

    ┌─────────────────────────────────────────────────┐
    │ Standard Analysis  [All Signals] [Load Only]    │
    │ Processing toolbar                              │
    ├──────────────────────────┬──────────────────────┤
    │ Load vs Time (Peak dot)  │ Displacement vs Time │  (240)
    ├──────────────────────────┼──────────────────────┤
    │ Velocity vs Time (v=0)   │ Acceleration Raw+Sm. │  (200)
    ├──────────────────────────┼──────────────────────┤
    │ Load vs Displacement     │ Phase Space          │  (260)
    │ (hysteresis + Peak + UP) │ (vel vs disp loop +  │
    │                          │  Start / End markers)│
    └──────────────────────────┴──────────────────────┘

Row 3 reproduces the RPLT-specific plots we had in the old ECharts
dashboard: the Load-vs-Displacement hysteresis loop and the Phase-Space
(velocity-vs-displacement) closed curve, both with proper markers.
"""
from __future__ import annotations

import numpy as np
import streamlit as st

from lib.cache import ensure_registered, table_version
from lib.charts.canvas import chart_panel, icon_btn, series, series_xy, small_btn
from lib.charts.helpers import detect_event_window, find_unloading_point
from lib.components import empty_state, page_header
from lib.processing import (
    COL_ACCEL, COL_DISP, COL_LOAD, COL_SMOOTHED, COL_TIME, COL_VELOCITY,
    pick_column, render_controls, run_processing,
)
from lib.queries import column_names
from lib.state import get_active_info


# Series colours (match views.jsx::StandardView + our dashboard).
_COLOR_LOAD    = "#10b981"
_COLOR_DISP    = "#3b82f6"
_COLOR_VEL     = "#f59e0b"
_COLOR_ACCEL   = "#8b5cf6"
_COLOR_ACCEL_R = "#cbd5e1"
_COLOR_PHASE   = "#8b5cf6"

# Marker colours — mirror the old ECharts look.
_C_PEAK        = "#10b981"
_C_UP          = "#ef4444"
_C_V0          = "#ef4444"
_C_START       = "#10b981"
_C_END         = "#8b5cf6"

_H_ROW1 = 240
_H_ROW2 = 200
_H_ROW3 = 260


def render() -> None:
    info = get_active_info()
    if info is None:
        page_header(
            "Standard Analysis",
            "Load, displacement, and velocity from processed sensor data",
        )
        empty_state(
            "database",
            "No active dataset",
            "Import a file (or click Load Demo Dataset) to populate the charts.",
        )
        return

    ensure_registered(info.table_name)
    v = table_version(info.table_name)
    cols = column_names(info.table_name, v) or []

    right_html = (
        '<button type="button" class="rgf-btn-sm active">All Signals</button>'
        '<button type="button" class="rgf-btn-sm">Load Only</button>'
    )
    page_header(
        "Standard Analysis",
        "Load, displacement, and velocity from processed sensor data",
        right_html=right_html,
    )

    time_col = st.session_state.get("rgf_map_time") or pick_column(
        cols, ["time (s)", "time", "t"])
    accel_col = st.session_state.get("rgf_map_accel") or pick_column(
        cols, ["scaled (m/s2)", "acceleration scaled", "accel scaled", "acceleration raw", "accel"])
    load_col = st.session_state.get("rgf_map_load") or pick_column(
        cols, ["load (kn)", "load summ", "load sum", "load scaled", "load", "force", "LOAD"])

    time_col, accel_col, load_col, params = render_controls(
        cols, time_col, accel_col, load_col, key_prefix="std",
    )

    computed = run_processing(info.table_name, v, time_col, accel_col, load_col, params)
    if computed is None or computed.empty:
        empty_state("alert", "Processing failed",
                    "Check the column mapping — the columns must be numeric.")
        return

    t = computed[COL_TIME].to_numpy()
    load = computed[COL_LOAD].to_numpy()
    disp_m = computed[COL_DISP].to_numpy()
    vel_ms = computed[COL_VELOCITY].to_numpy()

    # Derive landmarks — peak load, v=0 crossing.
    peak_idx = int(np.argmax(np.abs(load)))
    v0_idx = _find_first_zero_crossing(vel_ms, start=peak_idx)

    peak_t = float(t[peak_idx])
    peak_load = float(load[peak_idx])
    v0_t = float(t[v0_idx]) if v0_idx is not None else None

    # Displacement unit auto-pick (µm for sub-mm motion, else mm).
    disp_max = float(np.abs(disp_m).max())
    disp_scale, disp_unit = _disp_units(disp_max)
    disp_scaled = disp_m * disp_scale
    vel_mms = vel_ms * 1000.0

    # ── Row 1: Load vs Time + Displacement vs Time ───────────────────────────
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        peak_label = f"Peak {peak_load:,.0f} kN"
        chart_panel(
            "Load vs Time",
            [series(load, _COLOR_LOAD, "Load (kN)")],
            x_data=t,
            x_label="Time (s)", y_label="Load (kN)",
            height=_H_ROW1,
            actions_html=icon_btn("download", title="Export"),
            key="std_load",
            annotations=[
                {"type": "point", "x": peak_t, "y": peak_load,
                 "label": peak_label, "color": _C_PEAK, "shape": "circle",
                 "label_offset": "top"},
            ],
        )
    with c2:
        mm_active = disp_unit == "mm"
        chart_panel(
            "Displacement vs Time",
            [series(disp_m * 1000.0, _COLOR_DISP, "Displacement")],
            x_data=t,
            x_label="Time (s)", y_label=f"Displacement ({disp_unit})",
            height=_H_ROW1,
            actions_html=(
                small_btn("mm", active=mm_active, group="unit",
                          data={"factor": "1"})
                + small_btn("µm", active=not mm_active, group="unit",
                            data={"factor": "1000"})
                + icon_btn("download", title="Export")
            ),
            key="std_disp",
        )

    # ── Row 2: Velocity (with v=0 vline) + Acceleration Raw vs Smoothed ──────
    c3, c4 = st.columns(2, gap="medium")
    with c3:
        vel_annotations = []
        if v0_t is not None:
            vel_annotations.append(
                {"type": "vline", "x": v0_t, "label": "v=0", "color": _C_V0}
            )
        chart_panel(
            "Velocity vs Time",
            [series(vel_mms, _COLOR_VEL, "Velocity (mm/s)")],
            x_data=t,
            x_label="Time (s)", y_label="Velocity (mm/s)",
            height=_H_ROW2,
            actions_html=icon_btn("download", title="Export"),
            key="std_vel",
            annotations=vel_annotations,
        )
    with c4:
        has_smoothed = COL_SMOOTHED in computed.columns
        accel_series = [
            series(computed[COL_ACCEL], _COLOR_ACCEL_R, "Raw",
                   dashed=True, filled=False),
        ]
        if has_smoothed:
            accel_series.append(
                series(computed[COL_SMOOTHED], _COLOR_ACCEL, "Smoothed", filled=False)
            )
        chart_panel(
            "Acceleration — Raw vs Smoothed",
            accel_series,
            x_data=t,
            x_label="Time (s)", y_label="Accel (m/s²)",
            height=_H_ROW2,
            actions_html=(
                small_btn("Overlay", active=True, group="mode",
                          data={"mode": "overlay"})
                + small_btn("Split", active=False, group="mode",
                            data={"mode": "split"})
                + icon_btn("download", title="Export")
            ),
            key="std_accel",
        )

    # ── Row 3: Load vs Displacement (hysteresis) + Phase Space ───────────────
    # Crop to the impact event so the hysteresis and phase loops don't
    # stretch across the long flat tails of the recording (which would
    # squash the interesting part to a few pixels).
    ev_start, ev_end = detect_event_window(
        load, threshold_pct=0.02, buffer_pct=0.3, min_buffer=40,
    )
    # Further downsample the cropped window to keep the canvas snappy.
    ev_len = ev_end - ev_start
    target_n = 800
    if ev_len > target_n:
        idx = np.linspace(ev_start, ev_end - 1, target_n).astype(int)
    else:
        idx = np.arange(ev_start, ev_end)
    load_ev = load[idx]
    disp_ev = disp_scaled[idx]  # already scaled to µm / mm per auto-pick
    vel_ev = vel_mms[idx]
    peak_idx_ev = int(np.argmax(np.abs(load_ev)))
    up_idx_ev = find_unloading_point(load_ev, vel_ev)
    if up_idx_ev is None or up_idx_ev <= 0 or up_idx_ev >= len(load_ev) - 1:
        up_idx_ev = peak_idx_ev

    c5, c6 = st.columns(2, gap="medium")
    with c5:
        _render_load_vs_disp(load_ev, disp_ev, peak_idx_ev, up_idx_ev, disp_unit)
    with c6:
        _render_phase_space(vel_ev, disp_ev, disp_unit)


# ── Row-3 chart builders ─────────────────────────────────────────────────────
def _render_load_vs_disp(
    load_ev: np.ndarray, disp_ev: np.ndarray,
    peak_idx_ev: int, up_idx_ev: int, disp_unit: str,
) -> None:
    """Load vs Displacement hysteresis — solid loading + dashed unloading.

    Uses XY-pair series so each point carries its own (disp, load); no
    shared-x assumption, which is what broke the earlier impl — a
    non-monotonic x-axis (the same displacement value appears on both
    the loading and unloading branches) can't be represented as parallel
    y-arrays against a single x list.

    Inputs are already cropped to the event window by ``render()``.
    """
    n = len(load_ev)
    if n < 3:
        return

    # XY pairs for each branch. Overlap at up_idx so the two halves meet
    # visually.
    loading_xy = [(float(disp_ev[i]), float(load_ev[i])) for i in range(up_idx_ev + 1)]
    unloading_xy = [(float(disp_ev[i]), float(load_ev[i])) for i in range(up_idx_ev, n)]

    peak_disp = float(disp_ev[peak_idx_ev])
    peak_load = float(load_ev[peak_idx_ev])
    up_disp = float(disp_ev[up_idx_ev])
    up_load = float(load_ev[up_idx_ev])

    annotations = [
        # Origin cross — dashed guides at x=0 and y=0 so the viewer can
        # read off the elastic/plastic displacement split at load=0.
        {"type": "vline", "x": 0.0, "color": "#94a3b8"},
        {"type": "hline", "y": 0.0, "color": "#94a3b8"},
        {"type": "point", "x": peak_disp, "y": peak_load,
         "label": "Peak", "color": _C_PEAK, "shape": "circle",
         "label_offset": "top"},
    ]
    if up_idx_ev != peak_idx_ev:
        annotations.append(
            {"type": "point", "x": up_disp, "y": up_load,
             "label": "UP", "color": _C_UP, "shape": "diamond",
             "label_offset": "right"}
        )

    chart_panel(
        f"Load (kN) vs Displacement ({disp_unit})",
        [
            series_xy(loading_xy, _COLOR_LOAD, "Loading"),
            series_xy(unloading_xy, "#34d399", "Unloading", dashed=True),
        ],
        x_data=[],  # unused in XY mode, but chart_panel still expects x_data
        x_label=f"Displacement ({disp_unit})",
        y_label="Load (kN)",
        height=_H_ROW3,
        actions_html=icon_btn("download", title="Export"),
        key="std_lvd",
        annotations=annotations,
    )


def _render_phase_space(
    vel_ev: np.ndarray, disp_ev: np.ndarray, disp_unit: str,
) -> None:
    """Phase Space — velocity vs displacement, closed-loop curve.

    Uses series_xy so (disp, vel) pairs carry their own x-coords — the
    curve is a closed loop, so x is non-monotonic and can't be treated
    as a shared axis across samples.
    """
    n = len(vel_ev)
    if n < 3:
        return

    xy = [(float(disp_ev[i]), float(vel_ev[i])) for i in range(n)]

    chart_panel(
        f"Phase Space (mm/s vs {disp_unit})",
        [series_xy(xy, _COLOR_PHASE, "Trajectory")],
        x_data=[],
        x_label=f"Displacement ({disp_unit})",
        y_label="Velocity (mm/s)",
        height=_H_ROW3,
        actions_html=icon_btn("download", title="Export"),
        key="std_phase",
        annotations=[
            # Origin cross — subtle dashed guides at x=0 and y=0 to
            # visualize the coordinate frame of the phase trajectory.
            {"type": "vline", "x": 0.0, "color": "#94a3b8"},
            {"type": "hline", "y": 0.0, "color": "#94a3b8"},
            # Start / End markers on the trajectory.
            {"type": "point", "x": float(disp_ev[0]),  "y": float(vel_ev[0]),
             "label": "Start", "color": _C_START, "shape": "circle",
             "label_offset": "bottom"},
            {"type": "point", "x": float(disp_ev[-1]), "y": float(vel_ev[-1]),
             "label": "End", "color": _C_END, "shape": "circle",
             "label_offset": "right"},
        ],
    )


# ── Small helpers ────────────────────────────────────────────────────────────
def _disp_units(d_max_m: float) -> tuple[float, str]:
    if d_max_m > 0 and d_max_m < 0.01:
        return 1e6, "µm"
    if d_max_m < 1:
        return 1000.0, "mm"
    return 1.0, "m"


def _find_first_zero_crossing(arr: np.ndarray, *, start: int = 0) -> int | None:
    """Return index where ``arr`` first crosses zero on or after ``start``.

    Used to annotate the Velocity chart with the v=0 marker — the moment
    of peak displacement (where kinetic energy has been fully converted).
    """
    if len(arr) < 2:
        return None
    s = max(0, min(start, len(arr) - 2))
    signs = np.sign(arr[s:])
    # Find first zero or sign flip
    crossings = np.where(np.diff(signs) != 0)[0]
    if len(crossings) == 0:
        return None
    return s + int(crossings[0]) + 1
