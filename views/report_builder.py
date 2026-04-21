"""Report Builder — compose a client-ready PDF.

Matches ``components/views.jsx::ReportView`` 1:1:

    PageHeader | [Generate PDF]  (gradient-green SmallBtn)
    ────────────────────────────────────────────────────
    Grid: 320 px sidebar | 1fr preview
    ────────────────────────────────────────────────────
    Sidebar:
      ChartPanel "Report Sections" — toggleable list of sections
        [✓] Test Summary            (summary)
        [✓] Load vs Time Chart      (chart)
        [✓] Displacement Chart      (chart)
        [✓] UPM Force Decomposition (chart)
        [✓] Cycle Comparison Table  (table)
        [ ] Raw Data Appendix       (data)

      ChartPanel "Report Settings" — 5 editable text fields:
        Project Name · Client · Pile Reference · Test Date · Engineer

    Preview (white card, 40 px padding, max-width 640, centered):
      • Header — "RAPID PLATE LOAD TEST REPORT" uppercase accent
        + project name (24 px bold) + pile · date · engineer subtitle
      • Every included section renders BELOW the header, in order:
        summary → 6-cell KPI grid
        chart   → Canvas ChartPanel at 180 px
        table   → cycle comparison HTML table
        data    → first 20 rows of the raw dataset as a table

The Generate PDF button toggles ``body.rgf-printing-report`` on the
parent window and calls ``window.parent.print()``. The @media print
rules hide everything except the preview panel — the user saves as
PDF from their browser's print dialog.
"""
from __future__ import annotations

import html as html_mod

import numpy as np
import pandas as pd
import streamlit as st

from lib.cache import ensure_registered, table_version
from lib.charts.canvas import chart_panel, series
from lib.components import empty_state, page_header
from lib.cycles import detect_cycles
from lib.processing import (
    COL_DISP, COL_LOAD, COL_TIME, COL_VELOCITY,
    get_params, pick_column, run_processing,
)
from lib.queries import column_names, head
from lib.state import get_active_info


# Default sections — matches views.jsx::ReportView lines 397-404 exactly.
_DEFAULT_SECTIONS = [
    {"id": "summary",  "title": "Test Summary",            "type": "summary", "included": True},
    {"id": "load",     "title": "Load vs Time Chart",      "type": "chart",   "included": True},
    {"id": "disp",     "title": "Displacement Chart",      "type": "chart",   "included": True},
    {"id": "upm",      "title": "UPM Force Decomposition", "type": "chart",   "included": True},
    {"id": "cycles",   "title": "Cycle Comparison Table",  "type": "table",   "included": True},
    {"id": "raw",      "title": "Raw Data Appendix",       "type": "data",    "included": False},
]


def render() -> None:
    info = get_active_info()
    if not info:
        page_header(
            "Report Builder",
            "Compose and export a client-ready report",
        )
        empty_state(
            "report",
            "No active dataset",
            "Import a file (or click Load Demo Dataset) to build a report.",
        )
        return

    ensure_registered(info.table_name)
    v = table_version(info.table_name)
    cols = column_names(info.table_name, v) or []

    ss = st.session_state
    time_col = ss.get("rgf_map_time")  or pick_column(cols, ["time (s)", "time", "t"])
    accel_col = ss.get("rgf_map_accel") or pick_column(cols, ["scaled (m/s2)", "acceleration scaled", "accel scaled", "acceleration raw", "accel"])
    load_col = ss.get("rgf_map_load")   or pick_column(cols, ["load (kn)", "load summ", "load sum", "load scaled", "load", "force", "LOAD"])

    computed = run_processing(info.table_name, v, time_col, accel_col, load_col, get_params())
    if computed is None or computed.empty:
        page_header("Report Builder", "Compose and export a client-ready report")
        empty_state("alert", "Processing failed",
                    "Column mapping may be invalid — check Import Data.")
        return

    # ── Session state defaults ──────────────────────────────────────────────
    # Project metadata — all blank by default so nothing is assumed
    # about the test. The preview falls back to "Untitled Report" and
    # the filename when these are empty; the engineer fills them in
    # per-report. The old "Bridge Foundation Report" placeholder
    # implied a test type we don't actually know — removed.
    ss.setdefault("rb_sections", [dict(s) for s in _DEFAULT_SECTIONS])
    ss.setdefault("rb_project_name", "")
    ss.setdefault("rb_client", "")
    ss.setdefault("rb_pile", info.source_filename or "")
    ss.setdefault("rb_date", "")
    ss.setdefault("rb_engineer", "")

    # ── Hidden triggers for section toggles ────────────────────────────────
    for s in ss["rb_sections"]:
        if st.button("·", key=f"__rb_toggle_{s['id']}"):
            for i, ref in enumerate(ss["rb_sections"]):
                if ref["id"] == s["id"]:
                    ss["rb_sections"][i] = {**ref, "included": not ref["included"]}
                    break
            st.rerun()

    # ── Page header with Generate PDF gradient button ──────────────────────
    page_header(
        "Report Builder",
        "Compose and export a client-ready report",
        right_html=(
            '<button type="button" class="rgf-btn-gradient" '
            'data-action="rb-generate-pdf">Generate PDF</button>'
        ),
    )

    # ── Layout: 320-px sidebar + preview ───────────────────────────────────
    side_col, main_col = st.columns([1, 2.6], gap="medium")
    with side_col:
        _render_sections_panel()
        _render_settings_panel()
    with main_col:
        _render_preview(info, computed)


# ── Report Sections panel ───────────────────────────────────────────────────
def _render_sections_panel() -> None:
    """List of toggleable section rows + '+ Add' action (stub, opens
    no-op dialog — the design has it as a mock). Clicking a row fires
    the hidden ``__rb_toggle_<id>`` button via the JS bridge."""
    ss = st.session_state
    rows_html = []
    for s in ss["rb_sections"]:
        is_on = s["included"]
        check_svg = (
            '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" '
            'stroke="white" stroke-width="3" stroke-linecap="round" '
            'stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>'
            if is_on else ""
        )
        grip_svg = (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
            'stroke="#cbd5e1" stroke-width="2" stroke-linecap="round">'
            '<circle cx="9" cy="5" r="0.5" fill="currentColor"/>'
            '<circle cx="15" cy="5" r="0.5" fill="currentColor"/>'
            '<circle cx="9" cy="12" r="0.5" fill="currentColor"/>'
            '<circle cx="15" cy="12" r="0.5" fill="currentColor"/>'
            '<circle cx="9" cy="19" r="0.5" fill="currentColor"/>'
            '<circle cx="15" cy="19" r="0.5" fill="currentColor"/>'
            '</svg>'
        )
        rows_html.append(
            f'<div class="rgf-rb-section{" on" if is_on else ""}" '
            f'data-rb-toggle="{s["id"]}">'
            f'<span class="rgf-rb-check{" on" if is_on else ""}">{check_svg}</span>'
            f'<div class="rgf-rb-section-meta">'
            f'<div class="rgf-rb-section-title">{html_mod.escape(s["title"])}</div>'
            f'<div class="rgf-rb-section-type">{html_mod.escape(s["type"])}</div>'
            f'</div>'
            f'<span class="rgf-rb-grip">{grip_svg}</span>'
            f'</div>'
        )
    with st.container(key="rb_panel_sections"):
        st.markdown(
            '<div class="rgf-cb-panel-hdr">'
            '<span class="rgf-cb-panel-title">Report Sections</span>'
            '<span class="rgf-rb-badge-count">'
            f'{sum(1 for s in ss["rb_sections"] if s["included"])} '
            f'of {len(ss["rb_sections"])} included</span>'
            '</div>'
            f'<div class="rgf-rb-section-list">{"".join(rows_html)}</div>',
            unsafe_allow_html=True,
        )


# ── Report Settings panel — 5 editable fields ──────────────────────────────
def _render_settings_panel() -> None:
    with st.container(key="rb_panel_settings"):
        st.markdown(
            '<div class="rgf-cb-panel-hdr">'
            '<span class="rgf-cb-panel-title">Report Settings</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        _field("Project Name",   "rb_project_name")
        _field("Client",         "rb_client")
        _field("Pile Reference", "rb_pile")
        _field("Test Date",      "rb_date")
        _field("Engineer",       "rb_engineer")


def _field(label: str, session_key: str) -> None:
    st.markdown(
        f'<div class="rgf-cb-label">{html_mod.escape(label)}</div>',
        unsafe_allow_html=True,
    )
    st.session_state[session_key] = st.text_input(
        label, value=st.session_state.get(session_key, ""),
        label_visibility="collapsed", key=f"{session_key}_inp",
    )


# ── Report Preview ──────────────────────────────────────────────────────────
def _render_preview(info, computed: pd.DataFrame) -> None:
    """White card containing the report header + every included section,
    in display order, with REAL data from the processed dataframe."""
    ss = st.session_state

    with st.container(key="rgf_rb_preview"):
        # Header block — "RAPID PLATE LOAD TEST REPORT" accent tag +
        # project name + pile · date · engineer subtitle.
        project = html_mod.escape(ss["rb_project_name"] or "Untitled Report")
        subtitle_bits = []
        if ss["rb_pile"]:     subtitle_bits.append(f"Pile {html_mod.escape(ss['rb_pile'])}")
        if ss["rb_date"]:     subtitle_bits.append(html_mod.escape(ss["rb_date"]))
        if ss["rb_engineer"]: subtitle_bits.append(html_mod.escape(ss["rb_engineer"]))
        subtitle = " · ".join(subtitle_bits) or (info.source_filename or "")

        st.markdown(
            '<div class="rgf-rb-report">'
            '<div class="rgf-rb-report-header">'
            '<div class="rgf-rb-report-tag">Rapid Plate Load Test Report</div>'
            f'<div class="rgf-rb-report-title">{project}</div>'
            f'<div class="rgf-rb-report-sub">{subtitle}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Iterate sections in order, rendering only the included ones.
        for s in ss["rb_sections"]:
            if not s["included"]:
                continue
            if s["type"] == "summary":
                _render_summary_section(computed)
            elif s["id"] == "load":
                _render_chart_section("Load vs Time", computed,
                                      y_col=COL_LOAD, color="#10b981", y_label="Load (kN)")
            elif s["id"] == "disp":
                disp_max = float(np.abs(computed[COL_DISP]).max())
                scale, unit = _disp_units(disp_max)
                _render_chart_section("Displacement vs Time", computed,
                                      y_col=COL_DISP, color="#3b82f6",
                                      y_label=f"Displacement ({unit})",
                                      y_scale=scale)
            elif s["id"] == "upm":
                _render_upm_section(computed)
            elif s["type"] == "table":
                _render_cycles_section(computed)
            elif s["type"] == "data":
                _render_raw_data_section(info)

        st.markdown('</div>', unsafe_allow_html=True)


def _render_summary_section(df: pd.DataFrame) -> None:
    """6-cell KPI grid — Peak Load, Max Disp, Set Disp, Peak Vel,
    Samples, Duration. Values pulled from the processed frame."""
    peak_load = float(df[COL_LOAD].abs().max())
    disp_max_m = float(df[COL_DISP].abs().max())
    scale, unit = _disp_units(disp_max_m)
    max_disp = disp_max_m * scale
    last_disp = float(df[COL_DISP].dropna().iloc[-1]) * scale if not df[COL_DISP].dropna().empty else 0.0
    peak_vel_mms = float(df[COL_VELOCITY].abs().max()) * 1000.0
    duration = float(df[COL_TIME].iloc[-1] - df[COL_TIME].iloc[0])
    n = len(df)

    kpis = [
        ("Peak Load",         f"{peak_load:,.1f}",  "kN"),
        ("Max Displacement",  f"{max_disp:,.3f}",   unit),
        ("Set Displacement",  f"{last_disp:,.3f}",  unit),
        ("Peak Velocity",     f"{peak_vel_mms:,.3f}", "mm/s"),
        ("Samples",           f"{n:,}",             ""),
        ("Duration",          f"{duration:.4f}",    "s"),
    ]
    cells = "".join(
        f'<div class="rgf-rb-kpi-cell">'
        f'<span class="rgf-rb-kpi-label">{html_mod.escape(label)}</span>'
        f'<span class="rgf-rb-kpi-value">{html_mod.escape(value)} '
        f'<span class="rgf-rb-kpi-unit">{html_mod.escape(unit_str)}</span></span>'
        f'</div>'
        for label, value, unit_str in kpis
    )
    st.markdown(
        '<h3 class="rgf-rb-sec-title">Test Summary</h3>'
        f'<div class="rgf-rb-kpi-grid">{cells}</div>',
        unsafe_allow_html=True,
    )


def _render_chart_section(
    title: str, df: pd.DataFrame, *,
    y_col: str, color: str, y_label: str, y_scale: float = 1.0,
) -> None:
    """Canvas chart wrapped in a bg-soft tinted card — same engine as
    every other view in the app, so the dark-theme preview stays
    consistent. The PDF that prints from this view is dark-themed too,
    matching the on-screen look 1:1."""
    st.markdown(
        f'<h3 class="rgf-rb-sec-title">{html_mod.escape(title)}</h3>'
        f'<div class="rgf-rb-chart-card">',
        unsafe_allow_html=True,
    )
    chart_panel(
        title,
        [series(df[y_col].to_numpy() * y_scale, color, title)],
        x_data=df[COL_TIME].to_numpy(),
        x_label="Time (s)",
        y_label=y_label,
        height=200,
        actions_html="",
        key=f"rb_{y_col.lower().replace(' ', '_').replace('(', '').replace(')', '')}",
    )
    st.markdown('</div>', unsafe_allow_html=True)


def _render_upm_section(df: pd.DataFrame) -> None:
    """Force components overlay — Fma + Fkx + Total Force."""
    has_upm = "Fma (kN)" in df.columns
    st.markdown(
        '<h3 class="rgf-rb-sec-title">UPM Force Decomposition</h3>'
        '<div class="rgf-rb-chart-card">',
        unsafe_allow_html=True,
    )
    if not has_upm:
        st.markdown(
            '<div class="rgf-rb-note">UPM columns not present — '
            'set Mass + Stiffness on Standard Analysis and reprocess.</div>',
            unsafe_allow_html=True,
        )
    else:
        chart_panel(
            "UPM Force Components",
            [
                series(df["Fma (kN)"].to_numpy(),         "#3b82f6", "F=ma", filled=False),
                series(df["Fkx (kN)"].to_numpy(),         "#f59e0b", "F=kx", filled=False),
                series(df["Total Force (kN)"].to_numpy(), "#8b5cf6", "Total", filled=False, dashed=True),
            ],
            x_data=df[COL_TIME].to_numpy(),
            x_label="Time (s)",
            y_label="Force (kN)",
            height=220,
            actions_html="",
            key="rb_upm",
        )
    st.markdown('</div>', unsafe_allow_html=True)


def _render_cycles_section(df: pd.DataFrame) -> None:
    """HTML table of detected cycles — compact, same row spec as Dashboard."""
    cycles = detect_cycles(df)
    st.markdown(
        '<h3 class="rgf-rb-sec-title">Cycle Comparison</h3>',
        unsafe_allow_html=True,
    )
    if not cycles:
        st.markdown(
            '<div class="rgf-rb-note">No cycles detected.</div>',
            unsafe_allow_html=True,
        )
        return
    rows = "".join(
        f'<tr>'
        f'<td>#{c["cycle_no"]}</td>'
        f'<td>{c["peak_load"]:,.1f} kN</td>'
        f'<td>{c["max_disp_m"]*1e6:,.2f} µm</td>'
        f'<td>{c["set_disp_m"]*1e6:,.2f} µm</td>'
        f'<td>{c["peak_vel"]*1000:,.3f} mm/s</td>'
        f'<td>{c["duration_s"]*1000:,.2f} ms</td>'
        f'</tr>'
        for c in cycles
    )
    st.markdown(
        '<table class="rgf-rb-table">'
        '<thead><tr>'
        '<th>Cycle</th><th>Peak Load</th><th>Max Disp</th>'
        '<th>Set Disp</th><th>Peak Vel</th><th>Duration</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody>'
        '</table>',
        unsafe_allow_html=True,
    )


def _render_raw_data_section(info) -> None:
    """First 20 rows of the raw active table — simple HTML table."""
    df = head(info.table_name, table_version(info.table_name), n=20)
    if df.empty:
        return
    header = "".join(f"<th>{html_mod.escape(str(c))}</th>" for c in df.columns)
    rows = []
    for _, row in df.iterrows():
        cells = "".join(
            f"<td>{html_mod.escape(f'{v:.4f}' if isinstance(v, (int, float)) else str(v))}</td>"
            for v in row
        )
        rows.append(f"<tr>{cells}</tr>")
    st.markdown(
        '<h3 class="rgf-rb-sec-title">Raw Data Appendix</h3>'
        '<div class="rgf-rb-note" style="margin-bottom:8px">'
        f'First {len(df)} of {info.row_count:,} rows'
        '</div>'
        '<table class="rgf-rb-table rgf-rb-table-mono">'
        f'<thead><tr>{header}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table>',
        unsafe_allow_html=True,
    )


# ── Small helpers ───────────────────────────────────────────────────────────
def _disp_units(d_max_m: float) -> tuple[float, str]:
    if d_max_m > 0 and d_max_m < 0.01:
        return 1e6, "µm"
    if d_max_m < 1:
        return 1000.0, "mm"
    return 1.0, "m"
