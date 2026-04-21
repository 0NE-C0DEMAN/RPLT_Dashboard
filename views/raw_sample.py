"""Raw Data view — searchable / filterable / exportable sample table.

Matches ``components/views.jsx::RawDataView`` 1:1 and fills in every
bit the design only mocked up:

    PageHeader "Raw Data" ─────────── [🔍 search] [🪣 filter] [⬇ CSV]
    ────────────────────────────────────────────────────────────
    Sample Data                                      [N rows]
      ┌──────────────────────────────────────────────────────┐
      │ #   Time   Accel   Load   Vel   Disp   Fma   Fkx   … │  ← sticky
      ├──────────────────────────────────────────────────────┤
      │  1  0.000  12.3   823.0  0.24 −3.37   0.12  0.002   │
      │  2  0.000  13.1  1601.8  0.25 −5.45   0.13  0.003   │
      │  …                                                   │
      └──────────────────────────────────────────────────────┘
    Showing 1–20 of 6,315   [Prev][1][2][3]…[316][Next]

Every control is wired:
  • **Search** — matches any column via a pandas contains-all-strings mask.
    Clearing the box restores the full table.
  • **Filter** — toggle reveals a column + operator + value form. Numeric
    ops (> >= < <= = !=) operate on the raw column; string contains for
    non-numerics.
  • **Export CSV** — ``st.download_button`` emits the *post-search-and-
    filter* frame (not the current page), so what you see is what
    lands in the file.
  • **Pagination** — 20 rows per page. Prev / page-numbers / Next drive
    ``st.session_state["rd_page"]`` through the JS click-bridge.
  • **Load column** — when present, its cells tint accent-green so the
    hero signal stands out in a wall of mono numerics (design L544).
"""
from __future__ import annotations

import html as html_mod

import numpy as np
import pandas as pd
import streamlit as st

from lib.cache import ensure_registered, table_version
from lib.components import empty_state, page_header
from lib.processing import get_params, pick_column, run_processing
from lib.queries import column_names
from lib.state import get_active_info


_PAGE_SIZE = 20


# Design spec columns + the processed-df column they map from + an
# optional scale factor. Matches views.jsx::RawDataView line 531 exactly.
# `scale` converts raw units → display units (e.g., Disp is stored in m
# but the report + data table display in mm).
_DISPLAY_COLUMNS = [
    # (display name,           source column,                scale)
    ("Time (s)",                "Time (s)",                   1.0),
    ("Accel (m/s²)",            "Scaled (m/s2)",              1.0),
    ("Accel Smoothed (m/s²)",   "Scaled (m/s2) Smoothed",     1.0),
    ("Load (kN)",               "Load (kN)",                  1.0),
    ("Velocity (m/s)",          "Velocity (m/s)",             1.0),
    ("Disp (mm)",               "Disp (m)",                   1000.0),
    ("F=ma (kN)",               "Fma (kN)",                   1.0),
    ("F=kx (kN)",               "Fkx (kN)",                   1.0),
]


def _build_display_df(df_src: pd.DataFrame) -> pd.DataFrame:
    """Project the processed frame onto the design's column set with
    clean units + pretty headers. Columns that aren't present in the
    source (e.g. UPM hasn't been computed) are skipped gracefully."""
    out = {}
    for display_name, src_name, scale in _DISPLAY_COLUMNS:
        if src_name in df_src.columns:
            out[display_name] = df_src[src_name] * scale if scale != 1.0 else df_src[src_name]
    return pd.DataFrame(out)


def render() -> None:
    info = get_active_info()
    if not info:
        page_header("Raw Data", "Full sample table with search and export")
        empty_state(
            "sliders",
            "No active dataset",
            "Import a file (or click Load Demo Dataset) to browse its rows.",
        )
        return

    ensure_registered(info.table_name)
    v = table_version(info.table_name)
    cols = column_names(info.table_name, v) or []

    # Use the processed dataframe so the table shows the full derived-column
    # catalogue (Velocity, Disp, Fma, Fkx, Smoothed, Total Force) — same
    # as the Chart Builder did. Cached by run_processing so it's cheap
    # across reruns.
    ss = st.session_state
    time_col = ss.get("rgf_map_time")  or pick_column(cols, ["time (s)", "time", "t"])
    accel_col = ss.get("rgf_map_accel") or pick_column(cols, ["scaled (m/s2)", "acceleration scaled", "accel scaled", "acceleration raw", "accel"])
    load_col = ss.get("rgf_map_load")   or pick_column(cols, ["load (kn)", "load summ", "load sum", "load scaled", "load", "force", "LOAD"])
    df_full = run_processing(info.table_name, v, time_col, accel_col, load_col, get_params())
    if df_full is None or df_full.empty:
        page_header("Raw Data", "Full sample table with search and export")
        empty_state("alert", "Processing failed",
                    "Check column mapping — the columns must be numeric.")
        return

    # Project onto the 9-column design spec with proper units + pretty
    # headers. Downstream search / filter / pagination operate on this.
    df = _build_display_df(df_full)
    if df.empty:
        page_header("Raw Data", "Full sample table with search and export")
        empty_state("sliders", "No display columns",
                    "The processed frame doesn't include any of the "
                    "standard RPLT columns.")
        return

    # Session state defaults
    ss.setdefault("rd_search", "")
    ss.setdefault("rd_filter_open", False)
    ss.setdefault("rd_filter_col", "(none)")
    ss.setdefault("rd_filter_op", "(none)")
    ss.setdefault("rd_filter_val", "")
    ss.setdefault("rd_page", 1)

    # ── Header row — title LEFT, search pill + filter icon + export icon
    #    RIGHT, all on one line exactly like views.jsx::RawDataView. ──────
    _render_header_row(info, df)

    # ── Optional filter form (below the header, toggle-controlled) ────────
    if ss["rd_filter_open"]:
        _render_filter_panel(df)

    # ── Apply search + filter to get the working dataframe ─────────────────
    df_view = _apply_search(df, ss["rd_search"])
    df_view = _apply_filter(
        df_view, ss["rd_filter_col"], ss["rd_filter_op"], ss["rd_filter_val"],
    )

    if df_view.empty:
        empty_state(
            "inbox", "No matching rows",
            "Widen the search string or clear the filter.",
        )
        return

    # ── Main data table + pagination ───────────────────────────────────────
    _render_data_panel(df_view)


# ── Header row — title LEFT, search/filter/export icons RIGHT ──────────────
def _render_header_row(info, df_full: pd.DataFrame) -> None:
    """Matches ``views.jsx::RawDataView`` L515-524 — PageHeader with the
    three controls packed inline on the right side:

      "Raw Data"  <subtitle>      [🔍 Search samples…] [▤] [⬇]

    Filter + Export are HTML ``<button>``s with inline SVG — data-action
    attributes bridge to the real hidden ``st.button`` / hidden
    ``st.download_button`` Streamlit widgets below. This avoids relying
    on ``st.button(icon=":material/…:")`` which renders as plain text
    on older Streamlit versions.

    The search is a native ``st.text_input`` with the magnifying-glass
    icon painted inside via a CSS ``::before`` rule on the baseweb
    wrapper (reliable positioning regardless of the Streamlit wrapper
    chain).
    """
    ss = st.session_state

    # Hidden widgets that the HTML action buttons bridge into.
    # The filter-open toggle flips session state on click;
    # the download button pre-serves the current filtered CSV blob.
    if st.button("·", key="__rd_filter_btn"):
        ss["rd_filter_open"] = not ss["rd_filter_open"]
        st.rerun()

    df_view = _apply_search(df_full, ss["rd_search"])
    df_view = _apply_filter(
        df_view, ss["rd_filter_col"],
        ss["rd_filter_op"], ss["rd_filter_val"],
    )
    csv_bytes = df_view.to_csv(index=False).encode("utf-8")
    st.download_button(
        "·",
        data=csv_bytes,
        file_name="rplt_raw_data.csv",
        mime="text/csv",
        key="__rd_export_csv",
    )

    # Visible header row — title + controls inline.
    with st.container(key="rgf_rd_header"):
        col_title, col_search, col_actions = st.columns(
            [5, 2.2, 1.0], gap="small"
        )

        with col_title:
            subtitle = (
                f"{info.source_filename or info.table_name} · "
                f"{info.row_count:,} rows · {info.column_count} cols"
            )
            st.markdown(
                '<div class="rgf-pghdr-block">'
                '<h1 class="rgf-pghdr-title">Raw Data</h1>'
                f'<p class="rgf-pghdr-sub">{html_mod.escape(subtitle)}</p>'
                '</div>',
                unsafe_allow_html=True,
            )

        with col_search:
            # ``rgf-rd-search`` class on the stTextInput wrapper flags it
            # for the ::before search icon + left-padding-for-icon CSS.
            ss["rd_search"] = st.text_input(
                "Search",
                value=ss["rd_search"],
                placeholder="Search samples…",
                label_visibility="collapsed",
                key="rd_search_inp",
            )

        with col_actions:
            # Two square icon buttons — filter + download — rendered as
            # HTML so the SVG paths are guaranteed to show. Data-action
            # attrs wire them to the hidden Streamlit widgets above via
            # the app-level JS bridge (see app.py ATTRS / data-action).
            filter_active_cls = " active" if ss["rd_filter_open"] else ""
            st.markdown(
                f'<div class="rgf-rd-icon-row">'
                # Filter icon — filter funnel SVG
                f'<button type="button" class="rgf-btn-icon{filter_active_cls}" '
                'data-action="rd-filter-toggle" title="Filter">'
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
                'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
                'stroke-linejoin="round">'
                '<path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z"/>'
                '</svg></button>'
                # Download icon — download arrow SVG (same as dashboard export)
                '<button type="button" class="rgf-btn-icon" '
                'data-action="rd-export-csv" title="Export CSV">'
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
                'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
                'stroke-linejoin="round">'
                '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
                '<path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>'
                '</svg></button>'
                '</div>',
                unsafe_allow_html=True,
            )


# ── Filter form ─────────────────────────────────────────────────────────────
def _render_filter_panel(df: pd.DataFrame) -> None:
    """Three-field filter: column / operator / value. Only visible when
    the Filter icon in the header is toggled on."""
    ss = st.session_state
    with st.container(key="rgf_rd_filter"):
        st.markdown(
            '<div class="rgf-rd-filter-hdr">Filter rows</div>',
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns([2, 1, 2], gap="small")
        with c1:
            col_choices = ["(none)"] + list(df.columns)
            ss["rd_filter_col"] = st.selectbox(
                "Column", col_choices,
                index=col_choices.index(ss["rd_filter_col"])
                    if ss["rd_filter_col"] in col_choices else 0,
                label_visibility="collapsed", key="rd_filter_col_sel",
            )
        with c2:
            ops = ["(none)", ">", ">=", "<", "<=", "=", "!=", "contains"]
            ss["rd_filter_op"] = st.selectbox(
                "Op", ops,
                index=ops.index(ss["rd_filter_op"])
                    if ss["rd_filter_op"] in ops else 0,
                label_visibility="collapsed", key="rd_filter_op_sel",
            )
        with c3:
            ss["rd_filter_val"] = st.text_input(
                "Value", value=ss["rd_filter_val"],
                placeholder="Value…",
                label_visibility="collapsed", key="rd_filter_val_inp",
            )


# ── Data panel — table + pagination ────────────────────────────────────────
def _render_data_panel(df: pd.DataFrame) -> None:
    """Sticky-header mono table inside a ChartPanel, followed by the
    pagination footer (Prev / numbered pages with ellipsis / Next)."""
    ss = st.session_state
    total_rows = len(df)
    total_pages = max(1, (total_rows + _PAGE_SIZE - 1) // _PAGE_SIZE)

    # Clamp the current page to the new range after the filter shrinks it.
    page = int(ss.get("rd_page", 1))
    page = max(1, min(page, total_pages))
    ss["rd_page"] = page

    start = (page - 1) * _PAGE_SIZE
    end = min(start + _PAGE_SIZE, total_rows)
    window = df.iloc[start:end]

    # Hidden triggers for every visible page number button — declared
    # BEFORE the HTML so the bridge finds them on first render.
    for p in range(1, total_pages + 1):
        if st.button("·", key=f"__rd_page_{p}"):
            ss["rd_page"] = p
            st.rerun()
    for action in ("prev", "next"):
        if st.button("·", key=f"__rd_page_{action}"):
            delta = -1 if action == "prev" else 1
            ss["rd_page"] = max(1, min(total_pages, page + delta))
            st.rerun()

    # Build the HTML table
    header_cells = "".join(
        f'<th>{html_mod.escape(str(c))}</th>' for c in window.columns
    )
    header_cells = '<th class="rgf-rd-rownum">#</th>' + header_cells

    load_cols = {c for c in window.columns if "load" in c.lower()}
    rows_html: list[str] = []
    for local_idx, (orig_idx, row) in enumerate(window.iterrows(), start=start + 1):
        cells = [f'<td class="rgf-rd-rownum">{local_idx}</td>']
        for col, val in zip(window.columns, row):
            tdcls = ' class="rgf-rd-load"' if col in load_cols else ""
            cells.append(f'<td{tdcls}>{_fmt_cell(val)}</td>')
        row_cls = "rgf-rd-row" + (" alt" if local_idx % 2 == 0 else "")
        rows_html.append(f'<tr class="{row_cls}">{"".join(cells)}</tr>')

    table_html = (
        '<div class="rgf-rd-table-scroll">'
        '<table class="rgf-rd-table">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table>'
        '</div>'
    )

    pagination_html = _render_pagination_html(page, total_pages, start, end, total_rows)

    st.markdown(
        '<div class="rgf-rd-panel">'
        '<div class="rgf-rd-panel-hdr">'
        '<span class="rgf-rd-panel-title">Sample Data</span>'
        f'<span class="rgf-rd-panel-count">{total_rows:,} rows</span>'
        '</div>'
        f'{table_html}'
        f'{pagination_html}'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_pagination_html(
    page: int, total_pages: int, start: int, end: int, total_rows: int,
) -> str:
    """Pagination footer — "Showing X–Y of N" on the left, Prev / [pages]
    / Next on the right. Pages show current ± 2 neighbours with ellipsis
    and the last page pinned, same as the design."""
    # Build the set of page numbers to show: 1, current-1..current+1,
    # last. Collapse gaps into ellipsis tokens.
    shown: list[object] = []
    def add(p):
        if p < 1 or p > total_pages: return
        if p not in shown: shown.append(p)
    add(1)
    for d in (-1, 0, 1):
        add(page + d)
    add(total_pages)

    # Intersperse ellipses where there's a gap > 1
    with_ellipsis: list[object] = []
    last = 0
    for p in sorted(p for p in shown if isinstance(p, int)):
        if last and p - last > 1:
            with_ellipsis.append("…")
        with_ellipsis.append(p)
        last = p

    btns = []
    # Prev
    prev_disabled = " disabled" if page == 1 else ""
    btns.append(
        f'<button type="button" class="rgf-btn-sm" '
        f'data-rd-page="prev"{prev_disabled}>Prev</button>'
    )
    for item in with_ellipsis:
        if item == "…":
            btns.append('<span class="rgf-rd-ellipsis">…</span>')
        else:
            active = " active" if item == page else ""
            btns.append(
                f'<button type="button" class="rgf-btn-sm{active}" '
                f'data-rd-page="{item}">{item}</button>'
            )
    # Next
    next_disabled = " disabled" if page == total_pages else ""
    btns.append(
        f'<button type="button" class="rgf-btn-sm" '
        f'data-rd-page="next"{next_disabled}>Next</button>'
    )

    return (
        '<div class="rgf-rd-pagination">'
        f'<span class="rgf-rd-pagination-info">'
        f'Showing {start + 1:,}–{end:,} of {total_rows:,}'
        '</span>'
        f'<div class="rgf-rd-pagination-btns">{"".join(btns)}</div>'
        '</div>'
    )


# ── Search + filter predicates ──────────────────────────────────────────────
def _apply_search(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Row contains the query in ANY column (case-insensitive). Numeric
    cells are stringified before matching. Empty query = pass-through."""
    q = (query or "").strip().lower()
    if not q:
        return df
    # Build a boolean mask: any cell converted to str contains the query.
    mask = np.zeros(len(df), dtype=bool)
    for col in df.columns:
        as_str = df[col].astype(str).str.lower()
        mask |= as_str.str.contains(q, regex=False, na=False)
    return df[mask]


def _apply_filter(
    df: pd.DataFrame, col: str, op: str, val_str: str,
) -> pd.DataFrame:
    """Column filter. Numeric operators work on numeric columns; the
    ``contains`` operator works on anything."""
    if col == "(none)" or op == "(none)" or col not in df.columns:
        return df
    val_str = (val_str or "").strip()
    if not val_str and op != "contains":
        return df
    col_vals = df[col]
    if op == "contains":
        return df[col_vals.astype(str).str.contains(val_str, case=False, regex=False, na=False)]
    # Numeric ops
    try:
        val_num = float(val_str)
    except ValueError:
        return df  # bad input → no filter applied
    if not pd.api.types.is_numeric_dtype(col_vals):
        return df
    cmp = {
        ">":  col_vals >  val_num,
        ">=": col_vals >= val_num,
        "<":  col_vals <  val_num,
        "<=": col_vals <= val_num,
        "=":  col_vals == val_num,
        "!=": col_vals != val_num,
    }.get(op)
    return df[cmp] if cmp is not None else df


# ── Cell formatter ──────────────────────────────────────────────────────────
def _fmt_cell(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    if isinstance(val, (int, np.integer)):
        return f"{int(val):,}"
    if isinstance(val, (float, np.floating)):
        a = abs(float(val))
        if a == 0:
            return "0"
        if a < 0.001:
            return f"{val:.6f}"
        if a < 1:
            return f"{val:.4f}"
        if a < 1000:
            return f"{val:.3f}"
        return f"{val:,.2f}"
    return html_mod.escape(str(val))
