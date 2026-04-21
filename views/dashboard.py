"""Dashboard view — overview KPIs + 4 charts + cycle summary table.

Matches the reference design mock (components/view-dashboard.jsx):

    ┌─────────────────────────────────────────────────────────┐
    │ Dashboard                                       [badge] │
    │ <project> — Pile <ref>                                  │
    ├─────────────────────────────────────────────────────────┤
    │  Peak Load | Max Disp | Set Disp | Peak Velocity        │ (KPI row)
    ├──────────────────────────┬──────────────────────────────┤
    │ Load vs Time             │ Displacement vs Time          │
    ├──────────────────────────┼──────────────────────────────┤
    │ Velocity vs Time         │ Acceleration (raw + smoothed) │
    ├──────────────────────────┴──────────────────────────────┤
    │ Cycle Summary (table)                                    │
    └─────────────────────────────────────────────────────────┘

Real data is sourced from the active imported table. Auto-detects
columns via the column-mapping session state (rgf_map_time / accel / load).
When no table is active, renders an empty state.
"""
from __future__ import annotations

import html as html_mod

import numpy as np
import pandas as pd
import streamlit as st

from lib.cache import ensure_registered, table_version
from lib.charts.canvas import chart_panel, icon_btn, series, small_btn
from lib.components import badge, empty_state, page_header
from lib.cycles import detect_cycles
from lib.icons import svg
from lib.processing import (
    COL_ACCEL, COL_DISP, COL_LOAD, COL_SMOOTHED, COL_TIME, COL_VELOCITY,
    get_params, pick_column, run_processing,
)
from lib.state import get_active_info
from lib.tokens import (
    ACCENT, BG_SOFT, BORDER, BORDER_SOFT, SURFACE, TEXT, TEXT_3,
)

# ── Chart palette (matches design: green / blue / amber / violet / grey) ─────
_COLOR_LOAD     = "#10b981"
_COLOR_DISP     = "#3b82f6"
_COLOR_VEL      = "#f59e0b"
_COLOR_ACCEL    = "#8b5cf6"  # smoothed
_COLOR_ACCEL_R  = "#6e7d92"  # raw (muted)


# ── Main render ──────────────────────────────────────────────────────────────
def render() -> None:
    info = get_active_info()
    if info is None:
        page_header("Dashboard", "Rapid Plate Load Test overview")
        empty_state(
            "database",
            "No active dataset",
            "Go to Import Data and load a file (or click Load Demo Dataset) "
            "to populate the dashboard.",
        )
        return

    ensure_registered(info.table_name)
    v = table_version(info.table_name)

    # Resolve the 3 columns — prefer the user's column-mapping selection,
    # fall back to auto-detect on the active table's columns.
    from lib.queries import column_names
    cols = column_names(info.table_name, v) or []
    time_col = st.session_state.get("rgf_map_time")  or pick_column(cols, ["time (s)", "time", "t"])
    accel_col = st.session_state.get("rgf_map_accel") or pick_column(cols, ["scaled (m/s2)", "acceleration scaled", "accel scaled", "acceleration raw", "accel"])
    load_col = st.session_state.get("rgf_map_load")   or pick_column(cols, ["load (kn)", "load summ", "load sum", "load scaled", "load", "force", "LOAD"])

    if not (time_col and accel_col and load_col and time_col in cols and accel_col in cols and load_col in cols):
        page_header("Dashboard", info.source_filename or info.table_name)
        empty_state(
            "sliders",
            "Column mapping incomplete",
            "Go to Import Data → Column Mapping and pick Time, Acceleration, "
            "and Load columns.",
        )
        return

    # Run the compute pipeline (cached)
    params = get_params()
    computed = run_processing(info.table_name, v, time_col, accel_col, load_col, params)
    if computed is None or computed.empty:
        page_header("Dashboard", info.source_filename or info.table_name)
        empty_state("alert", "Processing failed",
                    "Check the column mapping — the selected columns must be numeric.")
        return

    cycles = detect_cycles(computed)
    kpis = _compute_kpis(computed)

    # ── Hidden download target for the Export button ─────────────────────────
    # The visible Export button in the page header is a plain HTML
    # <button> (st.markdown doesn't render Streamlit widgets inline with
    # text), so we expose a hidden ``st.download_button`` that the JS
    # bridge clicks via ``data-action="export-dashboard"``. Exports the
    # fully processed dataset — time/accel/load/velocity/displacement.
    csv_bytes = computed.to_csv(index=False).encode("utf-8")
    export_name = f"{info.table_name}_dashboard.csv"
    st.download_button(
        "·", data=csv_bytes, file_name=export_name, mime="text/csv",
        key="__dash_export_csv",
    )

    # ── Page header ───────────────────────────────────────────────────────────
    # Matches view-dashboard.jsx line 7-9: Badge + SmallBtn(Icon + " Export").
    right = (
        badge(f"{len(cycles)} Cycle{'s' if len(cycles) != 1 else ''}", "green")
        + '<button type="button" class="rgf-btn-sm" data-action="export-dashboard">'
        + f'{svg("download", size=13)} Export'
        + '</button>'
    )
    page_header(
        "Dashboard",
        f"{info.source_filename or info.table_name} · {info.row_count:,} samples",
        right_html=right,
    )

    # ── KPI row (4 cards, each with sparkline) ───────────────────────────────
    _render_kpi_row(computed, kpis)

    # ── Main chart row (2 charts) ────────────────────────────────────────────
    # Chart heights — match the design's 1:1 feel. ui.jsx sets height={220}
    # on the main row / {180} on the secondary row; those refer to the inner
    # canvas. Using the same numbers here so layout matches.
    _H_MAIN = 240   # main row (Load, Displacement)
    _H_SECOND = 200  # secondary row (Velocity, Acceleration)

    x = computed[COL_TIME]

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        chart_panel(
            "Load vs Time",
            [series(computed[COL_LOAD], _COLOR_LOAD, "Load (kN)")],
            x_data=x,
            x_label="Time (s)", y_label="Load (kN)",
            height=_H_MAIN,
            actions_html=(
                small_btn("kN", active=True)
                + icon_btn("download", title="Export")
            ),
            key="load",
        )
    with c2:
        # Feed the chart displacement in mm as the baseline; the in-iframe
        # unit toggle applies a ×1000 factor for µm on click.
        disp_mm = computed[COL_DISP] * 1000.0
        disp_max_um = float(computed[COL_DISP].abs().max()) * 1e6
        # Start in µm when the signal is sub-millimetre; else mm.
        start_um = disp_max_um < 10_000  # 10 mm
        chart_panel(
            "Displacement vs Time",
            [series(disp_mm, _COLOR_DISP, "Displacement")],
            x_data=x,
            x_label="Time (s)", y_label=f"Displacement ({'µm' if start_um else 'mm'})",
            height=_H_MAIN,
            actions_html=(
                small_btn("mm", active=not start_um, group="unit",
                           data={"factor": "1"})
                + small_btn("µm", active=start_um, group="unit",
                             data={"factor": "1000"})
                + icon_btn("download", title="Export")
            ),
            key="disp",
        )

    # ── Secondary chart row ──────────────────────────────────────────────────
    c3, c4 = st.columns(2, gap="medium")
    with c3:
        chart_panel(
            "Velocity vs Time",
            [series(computed[COL_VELOCITY] * 1000.0, _COLOR_VEL, "Velocity (mm/s)")],
            x_data=x,
            x_label="Time (s)", y_label="Velocity (mm/s)",
            height=_H_SECOND,
            actions_html=icon_btn("download", title="Export"),
            key="vel",
        )
    with c4:
        has_smoothed = COL_SMOOTHED in computed.columns
        accel_series = [
            series(computed[COL_ACCEL], _COLOR_ACCEL_R, "Raw",
                    dashed=True, filled=False)
        ]
        if has_smoothed:
            accel_series.append(
                series(computed[COL_SMOOTHED], _COLOR_ACCEL, "Smoothed", filled=False)
            )
        chart_panel(
            "Acceleration",
            accel_series,
            x_data=x,
            x_label="Time (s)", y_label="Accel (m/s²)",
            height=_H_SECOND,
            # Both traces visible by default — matches view-dashboard.jsx.
            # Each button is an independent toggle (multi-select).
            actions_html=(
                small_btn("Smoothed", active=has_smoothed, group="trace",
                          data={"label": "Smoothed"})
                + small_btn("Raw", active=True, group="trace",
                            data={"label": "Raw"})
                + icon_btn("download", title="Export")
            ),
            key="accel",
        )

    # ── Cycle summary table ──────────────────────────────────────────────────
    _render_cycle_table(cycles, disp_unit=kpis["disp_unit"])


# ── KPI computation ──────────────────────────────────────────────────────────
def _compute_kpis(df: pd.DataFrame) -> dict:
    peak_load = float(df[COL_LOAD].abs().max())
    disp_max_m = float(df[COL_DISP].abs().max())
    disp_scale, disp_unit = _disp_units(disp_max_m)
    max_disp = disp_max_m * disp_scale
    last_disp_series = df[COL_DISP].dropna()
    set_disp = float(last_disp_series.iloc[-1]) * disp_scale if not last_disp_series.empty else 0.0
    peak_vel = float(df[COL_VELOCITY].abs().max()) * 1000.0  # m/s → mm/s
    return dict(
        peak_load=peak_load,
        max_disp=max_disp, set_disp=set_disp, disp_unit=disp_unit,
        peak_vel=peak_vel,
    )


# ── KPI row ──────────────────────────────────────────────────────────────────
# Design (ui.jsx KpiCard line 24-25): accent-card spark is green (#10b981);
# every other spark is muted slate (#cbd5e1). Matches the mock's visual
# hierarchy — only the hero KPI "Peak Load" draws attention with its spark.
_SPARK_ACCENT = "#10b981"
_SPARK_MUTED  = "#cbd5e1"


def _render_kpi_row(df: pd.DataFrame, k: dict) -> None:
    disp_scale, _ = _disp_units(df[COL_DISP].abs().max())
    load_spark = _downsample(df[COL_LOAD].to_numpy(),                   n=80)
    disp_spark = _downsample((df[COL_DISP] * disp_scale).to_numpy(),    n=80)
    vel_spark  = _downsample((df[COL_VELOCITY] * 1000.0).to_numpy(),    n=80)

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        _kpi("Peak Load",        _fmt_num(k["peak_load"]),              "kN",
             spark=load_spark, spark_color=_SPARK_ACCENT, accent=True)
    with c2:
        _kpi("Max Displacement", _fmt_num(k["max_disp"], decimals=3),   k["disp_unit"],
             spark=disp_spark, spark_color=_SPARK_MUTED)
    with c3:
        _kpi("Set Displacement", _fmt_num(k["set_disp"], decimals=3),   k["disp_unit"],
             spark=disp_spark[-40:], spark_color=_SPARK_MUTED)
    with c4:
        _kpi("Peak Velocity",    _fmt_num(k["peak_vel"], decimals=2),   "mm/s",
             spark=vel_spark, spark_color=_SPARK_MUTED)


def _kpi(label: str, value: str, unit: str, *,
         spark=None, spark_color: str = ACCENT, accent: bool = False) -> None:
    accent_cls = " rgf-kpi-accent" if accent else ""
    spark_html = (
        f'<div class="rgf-kpi-spark">{_svg_spark(spark, spark_color)}</div>'
        if spark is not None else ""
    )
    st.markdown(
        f'<div class="rgf-kpi{accent_cls}">'
        f'<div class="rgf-kpi-top">'
        f'<span class="rgf-kpi-label">{html_mod.escape(label)}</span>'
        f'</div>'
        f'<div class="rgf-kpi-row">'
        f'<span class="rgf-kpi-value">{html_mod.escape(value)}</span>'
        f'<span class="rgf-kpi-unit">{html_mod.escape(unit)}</span>'
        f'</div>'
        f'{spark_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _svg_spark(data, color: str, width: int = 120, height: int = 24) -> str:
    """Inline SVG sparkline — matches the design's tiny per-KPI chart."""
    arr = np.asarray(data, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 2:
        return ""
    mn, mx = float(np.min(arr)), float(np.max(arr))
    rng = (mx - mn) or 1.0
    pad = 3
    pts = []
    for i, v in enumerate(arr):
        x = pad + (i / (len(arr) - 1)) * (width - pad * 2)
        y = pad + (height - pad * 2) - ((v - mn) / rng) * (height - pad * 2)
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    last_x = pad + (width - pad * 2)
    fill_poly = f"{pad:.1f},{height - pad:.1f} {poly} {last_x:.1f},{height - pad:.1f}"
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<polygon points="{fill_poly}" fill="{color}" fill-opacity="0.12" />'
        f'<polyline points="{poly}" fill="none" stroke="{color}" '
        f'stroke-width="1.5" stroke-linejoin="round" />'
        f'</svg>'
    )


# Chart panel + SmallBtn + IconBtn now live in lib/charts/canvas. The
# ``chart_panel`` / ``series`` / ``small_btn`` / ``icon_btn`` imports at the
# top of this file are the public surface every view can use.



# ── Cycle Summary table ──────────────────────────────────────────────────────
def _render_cycle_table(cycles: list[dict], disp_unit: str = "mm") -> None:
    """Render the Cycle Summary panel via st.components.v1.html.

    We use an iframe-scoped renderer instead of st.markdown because
    Streamlit's sanitiser rewrites ``<table>`` elements (it collapses
    them onto its built-in dataframe styling, which kills our design
    chrome). The iframe bypasses that and renders the HTML verbatim.
    """
    if not cycles:
        empty_panel = _cycle_panel_html(
            cycle_count=0, table_body="",
            table_head=_cycle_headers_html(),
            disp_unit=disp_unit, empty=True,
        )
        _inject_cycle_iframe(empty_panel, height=150)
        return

    # Displacement values now come from detect_cycles in METRES; scale to
    # whichever unit the KPI cards are showing (mm or µm) so the table
    # reads consistently with the rest of the Dashboard.
    disp_scale = 1e6 if disp_unit == "µm" else 1000.0
    disp_fmt = "{:,.2f}" if disp_unit == "µm" else "{:,.3f}"

    rows_html: list[str] = []
    for c in cycles:
        max_d = c["max_disp_m"] * disp_scale
        set_d = c["set_disp_m"] * disp_scale
        rows_html.append(
            "<tr>"
            f'<td><span class="pill">#{c["cycle_no"]}</span></td>'
            f'<td class="num">{c["peak_load"]:,.1f} <span class="u">kN</span></td>'
            f'<td class="num">{disp_fmt.format(max_d)} <span class="u">{disp_unit}</span></td>'
            f'<td class="num">{disp_fmt.format(set_d)} <span class="u">{disp_unit}</span></td>'
            f'<td class="num">{c["peak_vel"]:.3f} <span class="u">m/s</span></td>'
            f'<td class="num">{c["duration_s"]:.4f} <span class="u">s</span></td>'
            "</tr>"
        )

    html = _cycle_panel_html(
        cycle_count=len(cycles),
        table_head=_cycle_headers_html(),
        table_body="".join(rows_html),
        disp_unit=disp_unit,
    )
    # Panel chrome (62) + rows × row height (~45) + safety buffer
    row_h = 45
    height = 72 + len(cycles) * row_h + 24
    _inject_cycle_iframe(html, height=height)


def _cycle_headers_html() -> str:
    return "".join(
        f"<th>{h}</th>"
        for h in ["Cycle", "Peak Load", "Max Disp", "Set Disp", "Peak Vel", "Duration"]
    )


def _cycle_panel_html(
    *, cycle_count: int, table_head: str, table_body: str,
    disp_unit: str, empty: bool = False,
) -> str:
    """Return a full self-contained HTML document for the cycle panel.

    CSS is inlined so the iframe doesn't need access to assets/rgf.css.
    Colours come through as concrete hex values from lib.tokens so the
    panel matches the rest of the dark theme.
    """
    body = (
        '<div class="empty">No cycles detected — load signal didn\'t cross the 30% threshold.</div>'
        if empty else
        f'<div class="wrap">'
        f'<table>'
        f'<thead><tr>{table_head}</tr></thead>'
        f'<tbody>{table_body}</tbody>'
        f'</table>'
        f'</div>'
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    font-family: 'DM Sans', system-ui, sans-serif;
    background: transparent;
    color: {TEXT};
    -webkit-font-smoothing: antialiased;
  }}
  .panel {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    overflow: hidden;
    display: flex; flex-direction: column;
  }}
  .hdr {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 14px 18px 0; gap: 8px;
  }}
  .title {{ font-size: 13px; font-weight: 600; color: {TEXT}; }}
  .badge {{
    display: inline-block;
    padding: 3px 8px; font-size: 10px; font-weight: 600;
    border-radius: 5px; letter-spacing: 0.03em;
    background: rgba(59,130,246,0.15); color: #3b82f6;
  }}
  .body {{ padding: 8px 12px 12px; }}
  .wrap {{ width: 100%; overflow-x: auto; }}
  table {{
    width: 100%; border-collapse: collapse; font-size: 13px;
  }}
  thead tr {{ border-bottom: 2px solid {BORDER}; }}
  th {{
    padding: 10px 14px; text-align: left;
    font-size: 11px; font-weight: 600;
    color: {TEXT_3}; text-transform: uppercase; letter-spacing: 0.04em;
    background: transparent;
  }}
  tbody tr {{ border-bottom: 1px solid {BORDER_SOFT}; transition: background .15s; }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody tr:hover {{ background: {BG_SOFT}; }}
  td {{
    padding: 12px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500; color: {TEXT}; font-size: 13px;
    vertical-align: middle;
  }}
  td.num {{ font-variant-numeric: tabular-nums; }}
  .pill {{
    display: inline-block; padding: 3px 8px; border-radius: 5px;
    background: {BG_SOFT}; color: {TEXT};
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600; font-size: 12px;
  }}
  .u {{
    color: {TEXT_3}; font-size: 11px; font-weight: 400;
    font-family: 'JetBrains Mono', monospace;
  }}
  .empty {{
    padding: 36px 20px; text-align: center;
    color: {TEXT_3}; font-size: 13px;
  }}
</style></head>
<body>
  <div class="panel">
    <div class="hdr">
      <span class="title">Cycle Summary</span>
      <span class="badge">{cycle_count} cycle{'s' if cycle_count != 1 else ''} detected</span>
    </div>
    <div class="body">
      {body}
    </div>
  </div>
</body></html>"""


def _inject_cycle_iframe(html: str, *, height: int) -> None:
    st.components.v1.html(html, height=height, scrolling=False)


# ── Small helpers ────────────────────────────────────────────────────────────
def _downsample(arr: np.ndarray, n: int = 80) -> np.ndarray:
    """Return a length-``n`` sample of the array via uniform striding."""
    arr = np.asarray(arr, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) <= n:
        return arr
    idx = np.linspace(0, len(arr) - 1, n).astype(int)
    return arr[idx]


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


def _disp_units(d_max_m: float) -> tuple[float, str]:
    if d_max_m > 0 and d_max_m < 0.01:
        return 1e6, "µm"
    if d_max_m < 1:
        return 1000.0, "mm"
    return 1.0, "m"


