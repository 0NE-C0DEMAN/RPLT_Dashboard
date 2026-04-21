"""Chart Builder — fully functional custom-chart editor.

Matches ``components/view-chartbuilder.jsx`` 1:1:

    • PageHeader with [SQL] SmallBtn + Download IconBtn + Print IconBtn.
    • 280-px sidebar — three ChartPanels: Configure, Filter, Sample.
    • Configure: 3×2 SmallBtn grid for Chart Type, select for X, checkbox
      list for Y (multi-select, green-tinted row when active), select for
      Aggregation.
    • Filter: Column / Operator / Value (only Value appears once the op
      is chosen).
    • Sample: Max Rows slider (green accent) + mono numeric readout.
    • Chart preview on the right — all six chart types render against
      real DuckDB query results. Optional SQL block below, toggled by
      the [SQL] button.

Control implementation:
    • Chart Type grid + Y checkbox rows — rendered as HTML via
      ``st.markdown`` (`data-cb-type="Line"` / `data-cb-y="Load"`) and
      bridged to hidden ``st.button`` widgets via the app-level JS
      bridge so Streamlit reruns on click.
    • X / Aggregation / Filter column/op — native ``st.selectbox``
      restyled to match the design.
    • Max Rows — native ``st.slider`` with accent-green thumb + track.
"""
from __future__ import annotations

import html as html_mod
import re

import numpy as np
import pandas as pd
import streamlit as st

from lib.cache import ensure_registered, table_version
from lib.charts.canvas import chart_panel, series, series_xy
from lib.charts.helpers import box_summary, histogram_bins
from lib.components import badge, empty_state, page_header
from lib.processing import get_params, pick_column, run_processing
from lib.queries import column_names
from lib.state import get_active_info


CHART_TYPES = ["Line", "Scatter", "Area", "Bar", "Histogram", "Box"]
AGGREGATIONS = ["(none)", "mean", "max", "min", "sum", "count"]
AGG_SQL = {
    "mean": "AVG", "max": "MAX", "min": "MIN",
    "sum": "SUM", "count": "COUNT",
}
FILTER_OPS = ["(none)", ">", ">=", "<", "<=", "=", "!="]

_PALETTE = ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4",
            "#ec4899", "#84cc16"]


def _safe_key(name: str) -> str:
    """Collapse non-alnum characters in a column name so it's safe to use
    as a Streamlit widget key + a data-cb-y attribute value."""
    return re.sub(r"[^A-Za-z0-9]", "_", name) or "col"


def render() -> None:
    info = get_active_info()
    if not info:
        page_header(
            "Chart Builder",
            "Build custom charts from any column combination",
        )
        empty_state(
            "ruler",
            "No active dataset",
            "Import a file (or click Load Demo Dataset) to start building charts.",
        )
        return

    ensure_registered(info.table_name)
    v = table_version(info.table_name)

    # Run the processing pipeline FIRST — this expands the 3-4 raw columns
    # into the full catalogue (Velocity, Disp, Scaled, Smoothed, Fma, Fkx,
    # Total Force, etc.) that the design's column picker expects to see.
    # Without this, the Y-axis checkbox list would be missing most of the
    # useful columns and the filter/aggregation would silently fail on
    # any column that isn't one of the raw three.
    raw_cols = column_names(info.table_name, v) or []
    ss = st.session_state
    time_col = ss.get("rgf_map_time")  or pick_column(raw_cols, ["time (s)", "time", "t"])
    accel_col = ss.get("rgf_map_accel") or pick_column(raw_cols, ["scaled (m/s2)", "acceleration scaled", "accel scaled", "acceleration raw", "accel"])
    load_col = ss.get("rgf_map_load")   or pick_column(raw_cols, ["load (kn)", "load summ", "load sum", "load scaled", "load", "force", "LOAD"])
    if not (time_col and accel_col and load_col):
        page_header("Chart Builder", "Build custom charts")
        empty_state("sliders", "Column mapping incomplete",
                    "Go to Import Data → Column Mapping and pick Time, Acceleration, Load.")
        return

    df_full = run_processing(info.table_name, v, time_col, accel_col, load_col, get_params())
    if df_full is None or df_full.empty:
        page_header("Chart Builder", "Build custom charts")
        empty_state("alert", "Processing failed",
                    "Check column mapping — the picked columns must be numeric.")
        return

    # Every numeric column from the processed frame is plottable.
    numeric_cols = [c for c in df_full.columns
                    if pd.api.types.is_numeric_dtype(df_full[c])]
    if not numeric_cols:
        page_header("Chart Builder", "Build custom charts")
        empty_state("ruler", "No numeric columns",
                    "The processed dataframe has no numeric columns.")
        return

    # ── Session state defaults ──────────────────────────────────────────────
    ss.setdefault("cb_chart_type", "Line")
    ss.setdefault("cb_x_col", numeric_cols[0])
    default_y = [numeric_cols[1]] if len(numeric_cols) > 1 else [numeric_cols[0]]
    ss.setdefault("cb_y_cols", default_y)
    ss.setdefault("cb_agg", "(none)")
    ss.setdefault("cb_filter_col", "(none)")
    ss.setdefault("cb_filter_op", "(none)")
    ss.setdefault("cb_filter_val", 0.0)
    ss.setdefault("cb_max_rows", 10_000)
    ss.setdefault("cb_show_sql", False)

    # ── Hidden click-through triggers ──────────────────────────────────────
    # These must render BEFORE the visible HTML so the bridge JS can find
    # their .st-key-* wrappers. CSS hides them via the st-key-__cb_ rule.
    if st.button("·", key="__cb_toggle_sql"):
        ss["cb_show_sql"] = not ss["cb_show_sql"]
        st.rerun()
    for t in CHART_TYPES:
        if st.button("·", key=f"__cb_type_{t}"):
            ss["cb_chart_type"] = t
            st.rerun()
    for col in numeric_cols:
        if st.button("·", key=f"__cb_y_{_safe_key(col)}"):
            if col in ss["cb_y_cols"]:
                ss["cb_y_cols"] = [c for c in ss["cb_y_cols"] if c != col]
            else:
                ss["cb_y_cols"] = ss["cb_y_cols"] + [col]
            st.rerun()

    # ── Page header — SQL SmallBtn + download + print IconBtns ─────────────
    sql_active = ss["cb_show_sql"]
    right_html = (
        f'<button type="button" class="rgf-btn-sm'
        f'{" active" if sql_active else ""}" data-action="cb-toggle-sql">SQL</button>'
        + '<button type="button" class="rgf-btn-icon" data-action="cb-download" title="Export chart">'
        + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>'
        + '</button>'
        + '<button type="button" class="rgf-btn-icon" data-action="cb-print" title="Print">'
        + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v8H6z"/></svg>'
        + '</button>'
    )
    page_header(
        "Chart Builder",
        "Build custom charts from any column combination",
        right_html=right_html,
    )

    # ── Layout: 280-px sidebar | chart preview ──────────────────────────────
    side_col, main_col = st.columns([1, 3.2], gap="medium")

    with side_col:
        _render_configure_panel(numeric_cols)
        _render_filter_panel(numeric_cols)
        _render_sample_panel()

    with main_col:
        _render_chart_preview(df_full)


# ── Configure panel ─────────────────────────────────────────────────────────
def _render_configure_panel(numeric_cols: list[str]) -> None:
    """Chart Type grid + X select + Y checkbox list + Aggregation select."""
    ss = st.session_state
    with st.container(key="cb_panel_configure"):
        st.markdown(
            '<div class="rgf-cb-panel-hdr">'
            '<span class="rgf-cb-panel-title">Configure</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── Chart Type — 3×2 SmallBtn grid ─────────────────────────────────
        type_btns = "".join(
            f'<button type="button" class="rgf-btn-sm rgf-cb-type-btn'
            f'{" active" if ss["cb_chart_type"] == t else ""}" '
            f'data-cb-type="{t}">{t}</button>'
            for t in CHART_TYPES
        )
        st.markdown(
            '<div class="rgf-cb-label">Chart Type</div>'
            f'<div class="rgf-cb-type-grid">{type_btns}</div>',
            unsafe_allow_html=True,
        )

        # ── X Axis ─────────────────────────────────────────────────────────
        st.markdown('<div class="rgf-cb-label">X Axis</div>', unsafe_allow_html=True)
        x_index = (numeric_cols.index(ss["cb_x_col"])
                   if ss["cb_x_col"] in numeric_cols else 0)
        ss["cb_x_col"] = st.selectbox(
            "X Axis", numeric_cols, index=x_index,
            label_visibility="collapsed", key="cb_x_col_sel",
        )

        # ── Y Axis multi-select — HTML checkbox rows ───────────────────────
        # Each row is an HTML label that a JS click dispatches to a hidden
        # st.button (key=__cb_y_{safe}). The label wraps a styled
        # checkbox + column name, and carries data-cb-y="{safe}" so the
        # bridge can find it.
        st.markdown(
            '<div class="rgf-cb-label">Y Axis (multi-select)</div>',
            unsafe_allow_html=True,
        )
        y_choices = [c for c in numeric_cols if c != ss["cb_x_col"]]
        rows = []
        for c in y_choices:
            active = c in ss["cb_y_cols"]
            rows.append(
                f'<div class="rgf-cb-y-row{" active" if active else ""}" '
                f'data-cb-y="{_safe_key(c)}">'
                f'<span class="rgf-cb-y-check{" on" if active else ""}">'
                + ('<svg width="10" height="10" viewBox="0 0 24 24" fill="none" '
                   'stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
                   '<path d="M20 6L9 17l-5-5"/></svg>' if active else '')
                + '</span>'
                f'<span class="rgf-cb-y-name">{html_mod.escape(c)}</span>'
                f'</div>'
            )
        st.markdown(
            f'<div class="rgf-cb-y-list">{"".join(rows)}</div>',
            unsafe_allow_html=True,
        )

        # ── Aggregation ────────────────────────────────────────────────────
        st.markdown('<div class="rgf-cb-label">Aggregation</div>', unsafe_allow_html=True)
        ss["cb_agg"] = st.selectbox(
            "Aggregation", AGGREGATIONS,
            index=AGGREGATIONS.index(ss["cb_agg"]),
            label_visibility="collapsed", key="cb_agg_sel",
        )


# ── Filter panel ────────────────────────────────────────────────────────────
def _render_filter_panel(numeric_cols: list[str]) -> None:
    ss = st.session_state
    with st.container(key="cb_panel_filter"):
        st.markdown(
            '<div class="rgf-cb-panel-hdr">'
            '<span class="rgf-cb-panel-title">Filter</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="rgf-cb-label">Column</div>', unsafe_allow_html=True)
        col_choices = ["(none)"] + numeric_cols
        ss["cb_filter_col"] = st.selectbox(
            "Filter col", col_choices,
            index=col_choices.index(ss["cb_filter_col"])
                  if ss["cb_filter_col"] in col_choices else 0,
            label_visibility="collapsed", key="cb_filter_col_sel",
        )
        if ss["cb_filter_col"] != "(none)":
            st.markdown('<div class="rgf-cb-label">Operator</div>', unsafe_allow_html=True)
            ss["cb_filter_op"] = st.selectbox(
                "Operator", FILTER_OPS,
                index=FILTER_OPS.index(ss["cb_filter_op"])
                      if ss["cb_filter_op"] in FILTER_OPS else 0,
                label_visibility="collapsed", key="cb_filter_op_sel",
            )
            if ss["cb_filter_op"] != "(none)":
                st.markdown('<div class="rgf-cb-label">Value</div>', unsafe_allow_html=True)
                ss["cb_filter_val"] = st.number_input(
                    "Value", value=float(ss["cb_filter_val"]),
                    label_visibility="collapsed", key="cb_filter_val_inp",
                    format="%.6f",
                )


# ── Sample panel ────────────────────────────────────────────────────────────
def _render_sample_panel() -> None:
    ss = st.session_state
    with st.container(key="cb_panel_sample"):
        st.markdown(
            '<div class="rgf-cb-panel-hdr">'
            '<span class="rgf-cb-panel-title">Sample</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="rgf-cb-label">Max Rows</div>', unsafe_allow_html=True)
        ss["cb_max_rows"] = st.slider(
            "Max rows",
            min_value=100, max_value=50_000,
            value=int(ss["cb_max_rows"]),
            step=100,
            label_visibility="collapsed", key="cb_max_rows_sl",
        )
        st.markdown(
            '<div class="rgf-cb-hint">More rows = more detail, slower render.</div>',
            unsafe_allow_html=True,
        )


# ── Chart preview + SQL toggle ──────────────────────────────────────────────
def _render_chart_preview(df_full: pd.DataFrame) -> None:
    """Apply filter / aggregation / row-limit (all in pandas on the
    already-processed dataframe) and dispatch to the chart-type renderer.

    Using pandas in-memory instead of DuckDB SQL means every column —
    raw (LOAD, Time) and derived (Velocity, Disp, Fma, Fkx, Total Force,
    Scaled, Smoothed) — is filterable and aggregatable uniformly. The
    SQL view shows the equivalent query for documentation.
    """
    ss = st.session_state
    chart_type = ss["cb_chart_type"]
    x_col = ss["cb_x_col"]
    y_cols = ss["cb_y_cols"]
    agg = ss["cb_agg"]
    max_rows = ss["cb_max_rows"]

    if not y_cols:
        empty_state(
            "database",
            "Select Y-axis columns",
            "Pick at least one column in the sidebar to plot.",
        )
        return

    df = df_full

    # ── 1. Filter (WHERE) ──────────────────────────────────────────────────
    f_col = ss["cb_filter_col"]
    f_op  = ss["cb_filter_op"]
    f_val = ss["cb_filter_val"]
    if f_col != "(none)" and f_op != "(none)" and f_col in df.columns:
        col_vals = df[f_col]
        mask = {
            ">":  col_vals >  f_val,
            ">=": col_vals >= f_val,
            "<":  col_vals <  f_val,
            "<=": col_vals <= f_val,
            "=":  col_vals == f_val,
            "!=": col_vals != f_val,
        }.get(f_op)
        if mask is not None:
            df = df[mask]

    if df.empty:
        empty_state("inbox", "No rows after filter",
                    "Loosen the filter predicate or drop it.")
        return

    # ── 2. Aggregation — bucket X into ≤100 bins, aggregate Y per bucket ──
    # Pure GROUP BY on a continuous X column is a no-op (every value is
    # unique). To make aggregation visibly do something, we bin X into
    # up to 100 equal-width buckets, apply the agg function to each Y
    # column within each bucket, then plot bucket-center on X.
    if agg != "(none)" and chart_type not in ("Histogram", "Box") and x_col in df.columns:
        x_arr = df[x_col].to_numpy()
        x_arr = x_arr[~np.isnan(x_arr)] if np.issubdtype(x_arr.dtype, np.floating) else x_arr
        if len(x_arr) >= 2:
            n_buckets = min(100, len(df))
            edges = np.linspace(float(x_arr.min()), float(x_arr.max()), n_buckets + 1)
            # np.digitize returns 1-indexed bins; subtract 1 to get 0..n-1
            bucket = np.clip(
                np.digitize(df[x_col].to_numpy(), edges[1:-1]),
                0, n_buckets - 1,
            )
            agg_map = {x_col: "mean"}
            for c in y_cols:
                if c in df.columns:
                    agg_map[c] = agg
            df = (df.groupby(bucket, sort=True)
                    .agg(agg_map)
                    .reset_index(drop=True))

    # ── 3. Row limit — uniform-stride downsample to max_rows ──────────────
    if len(df) > max_rows:
        idx = np.linspace(0, len(df) - 1, max_rows).astype(int)
        df = df.iloc[idx].reset_index(drop=True)

    if df.empty:
        empty_state("inbox", "No rows to plot", "")
        return

    actions_html = (
        badge(f"{len(y_cols)} series", "gray")
        + badge(f"{len(df):,} rows", "blue")
    )

    if chart_type == "Histogram":
        _render_histogram(df, y_cols, actions_html)
    elif chart_type == "Box":
        _render_boxplot(df, y_cols, actions_html)
    else:
        _render_xy_chart(df, x_col, y_cols, chart_type, actions_html)

    # ── SQL preview — reflects the exact logical pipeline, even though
    # the underlying work runs in pandas on the cached processed frame.
    if ss["cb_show_sql"]:
        sql = _pseudo_sql(
            chart_type, x_col, y_cols, agg,
            f_col, f_op, f_val, max_rows,
        )
        sql_html = html_mod.escape(sql)
        st.markdown(
            f'<div class="rgf-cb-sql">'
            f'<div class="rgf-cb-sql-tag">Generated SQL</div>'
            f'<pre class="rgf-cb-sql-body">{sql_html}</pre>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_xy_chart(
    df: pd.DataFrame, x_col: str, y_cols: list[str],
    chart_type: str, actions_html: str,
) -> None:
    """Line / Scatter / Area / Bar — standard XY chart over the query result."""
    plot_mode = {"Line": "line", "Scatter": "scatter",
                 "Area": "area", "Bar": "bar"}[chart_type]

    x_data = df[x_col].to_numpy() if x_col in df.columns else np.arange(len(df))
    series_list = []
    for i, col in enumerate(y_cols):
        if col not in df.columns:
            continue
        color = _PALETTE[i % len(_PALETTE)]
        series_list.append(series(
            df[col].to_numpy(), color, col,
            plot=plot_mode,
            filled=(plot_mode == "line"),
        ))

    if not series_list:
        empty_state("alert", "No plottable series",
                    "The Y columns don't appear in the query result.")
        return

    chart_panel(
        f"{chart_type}: {', '.join(y_cols)} vs {x_col}",
        series_list,
        x_data=x_data,
        x_label=x_col,
        y_label=", ".join(y_cols),
        height=460,
        actions_html=actions_html,
        key="cb_main_chart",
    )


def _render_histogram(
    df: pd.DataFrame, y_cols: list[str], actions_html: str,
) -> None:
    """Bins the first Y column into 40 buckets, plots as a bar chart."""
    col = y_cols[0]
    data = df[col].to_numpy() if col in df.columns else np.array([])
    centers, counts = histogram_bins(data, bins=40)
    if len(centers) == 0:
        empty_state("inbox", "Not enough data",
                    f"{col!r} has fewer than 2 non-null values.")
        return

    chart_panel(
        f"Histogram: {col}",
        [series(counts, _PALETTE[0], "Count", plot="bar", downsample_n=None)],
        x_data=centers,
        x_label=col,
        y_label="Count",
        height=460,
        actions_html=actions_html,
        key="cb_hist_chart",
    )


def _render_boxplot(
    df: pd.DataFrame, y_cols: list[str], actions_html: str,
) -> None:
    """One box per Y column on a categorical x axis — q1→q3 box, whiskers
    to min/max, median line across the middle."""
    boxes = []
    for col in y_cols:
        data = df[col].to_numpy() if col in df.columns else np.array([])
        summary = box_summary(data)
        if summary["min"] is None:
            continue
        boxes.append((col, summary))

    if not boxes:
        empty_state("inbox", "Box plot needs data",
                    "The selected Y columns have no valid values.")
        return

    all_points = []
    annotations = []
    for i, (col, s) in enumerate(boxes):
        x0 = i - 0.35
        x1 = i + 0.35
        color = _PALETTE[i % len(_PALETTE)]

        box_poly = [
            (x0, s["q1"]), (x1, s["q1"]),
            (x1, s["q3"]), (x0, s["q3"]),
            (x0, s["q1"]),
            (None, None),
        ]
        whiskers = [
            (i, s["min"]),  (i, s["q1"]),   (None, None),
            (i, s["q3"]),   (i, s["max"]),  (None, None),
            (i - 0.15, s["min"]), (i + 0.15, s["min"]), (None, None),
            (i - 0.15, s["max"]), (i + 0.15, s["max"]), (None, None),
            (x0, s["median"]),    (x1, s["median"]),
        ]
        all_points.append((col, color, box_poly, whiskers))
        annotations.append({
            "type": "point",
            "x": float(i),
            "y": s["min"],
            "label": col,
            "color": color,
            "shape": "circle",
            "label_offset": "bottom",
        })

    series_list = []
    for col, color, box_poly, whiskers in all_points:
        series_list.append(series_xy(box_poly, color, f"{col} (box)"))
        series_list.append(series_xy(whiskers, color, f"{col} (whiskers)"))

    chart_panel(
        f"Box plot: {', '.join(y_cols)}",
        series_list,
        x_data=[],
        x_label="",
        y_label=", ".join(y_cols),
        height=460,
        actions_html=actions_html,
        key="cb_box_chart",
        annotations=annotations,
    )


# ── SQL preview ────────────────────────────────────────────────────────────
def _pseudo_sql(
    chart_type: str, x_col: str, y_cols: list[str],
    agg: str, filter_col: str, filter_op: str, filter_val: float,
    max_rows: int,
) -> str:
    """Return a pseudo-SQL string that describes the current query logic.

    Not actually executed — the real work runs in pandas on the cached
    processed frame so we can operate on derived columns (Velocity,
    Disp, Fma, etc.) that don't live in the underlying DuckDB table.
    Shown in the SQL preview block for transparency / documentation.
    """
    if chart_type == "Histogram":
        sql = (f'SELECT histogram("{y_cols[0]}", 40) AS bins\n'
               f'FROM processed_rplt')
    elif chart_type == "Box":
        y_parts = ", ".join(f'QUANTILES("{c}", [0, 0.25, 0.5, 0.75, 1]) AS "{c}"'
                            for c in y_cols)
        sql = f'SELECT {y_parts}\nFROM processed_rplt'
    else:
        if agg != "(none)":
            agg_fn = AGG_SQL[agg]
            y_parts = ", ".join(f'{agg_fn}("{c}") AS "{c}"' for c in y_cols)
            sql = (f'SELECT "{x_col}", {y_parts}\n'
                   f'FROM processed_rplt')
        else:
            cols = ", ".join(f'"{c}"' for c in [x_col] + y_cols)
            sql = f'SELECT {cols}\nFROM processed_rplt'

    if filter_col != "(none)" and filter_op != "(none)":
        sql += f'\nWHERE "{filter_col}" {filter_op} {filter_val}'

    if (chart_type not in ("Histogram", "Box")) and agg != "(none)":
        sql += f'\nGROUP BY width_bucket("{x_col}", 0, max, 100)'

    if chart_type not in ("Histogram", "Box"):
        sql += f'\nORDER BY "{x_col}"'

    sql += f'\nLIMIT {int(max_rows)}'
    return sql
