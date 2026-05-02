"""Import Data view — file upload + Google Sheets + GCP Storage source tabs,
column mapping, imported-files list, and data preview.

Matches reference design mock (components/views.jsx ImportView).

Google Sheets / GCP connectors are UI placeholders — the input fields render
and the submit buttons show an info toast. Wire up to real APIs later.
"""
from __future__ import annotations

import html as html_mod
import os
import time

import pandas as pd
import streamlit as st

from lib.cache import ensure_registered, table_version
from lib.components import badge, empty_state, page_header
from lib.icons import svg
from lib.ingest import ingest_file, list_excel_sheets, load_metadata, resolve_demo_ingest_path
from lib.queries import column_names, head
from lib.sources import manual
from lib.state import (
    add_imported, get_active_info, get_active_table,
    imported_tables, remove_imported, session_id, set_active_table,
)

_SRC_TABS = [
    ("upload", "File Upload",   "upload"),
    ("gsheet", "Google Sheets", "table"),
    ("gcp",    "GCP Storage",   "layers"),
]


# ── Main render ──────────────────────────────────────────────────────────────
def render() -> None:
    if "import_src" not in st.session_state:
        st.session_state.import_src = "upload"

    # Hidden trigger buttons — source-tab switch
    for sid, _label, _icon in _SRC_TABS:
        if st.button("·", key=f"__src_{sid}"):
            st.session_state.import_src = sid
            st.rerun()

    # Hidden trigger buttons — file-row activation
    for tname in imported_tables():
        if st.button("·", key=f"__activate_{tname}"):
            set_active_table(tname)
            st.rerun()

    # Hidden Clear All trigger
    if st.button("·", key="__clear_all_files"):
        for tname in list(imported_tables()):
            remove_imported(tname)
        st.rerun()

    # Hidden Load Demo trigger (used in empty state)
    if st.button("·", key="__load_demo"):
        _load_demo()

    src = st.session_state.import_src

    page_header(
        "Import Data",
        "Upload files, connect Google Sheets, or pull from GCP Storage",
    )

    _render_source_tabs(src)

    if src == "upload":
        _render_upload()
    elif src == "gsheet":
        _render_gsheet()
    else:
        _render_gcp()

    _render_data_setup()
    _render_trim_panel()
    _render_file_list()
    _render_data_preview()


def _load_demo() -> None:
    sid = session_id()
    try:
        src_path = resolve_demo_ingest_path(sid)
        result = ingest_file(src_path, sid, sheet_name="Sheet1")
    except Exception as exc:
        st.error(f"Demo load failed: {exc}")
    else:
        add_imported(result.table_name)
        set_active_table(result.table_name)
        st.rerun()


# ── Source tabs (pill-style, click-through to hidden buttons) ───────────────
def _render_source_tabs(active: str) -> None:
    items = []
    for sid, label, icon in _SRC_TABS:
        cls = "rgf-src-tab" + (" active" if sid == active else "")
        items.append(
            f'<button type="button" class="{cls}" data-src="{sid}">'
            f'<span class="rgf-src-tab-icon">{svg(icon, size=15)}</span>'
            f'{html_mod.escape(label)}'
            f'</button>'
        )
    st.markdown(f'<div class="rgf-src-tabs">{"".join(items)}</div>',
                unsafe_allow_html=True)


# ── File Upload tab — custom overlay on top of st.file_uploader ──────────────
def _render_upload() -> None:
    with st.container(key="rgf_upload_shell"):
        uploaded = st.file_uploader(
            "upload",
            type=manual.SUPPORTED_EXTENSIONS,
            accept_multiple_files=False,
            label_visibility="collapsed",
            key="rgf_import_upload",
        )
        st.markdown(
            f'''
            <div class="rgf-drop-overlay">
              <div class="rgf-drop-icon">{svg("upload", size=24, color="#10b981")}</div>
              <div class="rgf-drop-title">Drop files here or click to browse</div>
              <div class="rgf-drop-sub">Supports .xlsx, .csv, .txt sensor data — up to 2 GB</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    if uploaded is not None:
        _process_uploaded(uploaded)


def _process_uploaded(uploaded) -> None:
    sid = session_id()
    src_path = manual.save(uploaded, sid)
    kb = src_path.stat().st_size / 1024
    st.markdown(
        f'<div class="rgf-upload-hint">'
        f'<span><strong>{html_mod.escape(uploaded.name)}</strong> &nbsp;·&nbsp; '
        f'{kb:,.0f} KB ready to import</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    sheet_name = None
    if src_path.suffix.lower() in (".xlsx", ".xls"):
        sheets = list_excel_sheets(src_path)
        if len(sheets) > 1:
            sheet_name = st.selectbox("Sheet", sheets, index=0, key="rgf_import_sheet")
        else:
            sheet_name = sheets[0]
    if st.button("Import Dataset", type="primary", key="rgf_import_btn"):
        try:
            result = ingest_file(src_path, sid, sheet_name=sheet_name)
        except Exception as exc:
            st.error(f"Import failed: {exc}")
        else:
            add_imported(result.table_name)
            set_active_table(result.table_name)
            st.rerun()


# ── Google Sheets tab ────────────────────────────────────────────────────────
def _render_gsheet() -> None:
    st.markdown(
        '''
        <div class="rgf-cloud-card">
          <div class="rgf-cloud-head">
            <div class="rgf-cloud-ico rgf-cloud-ico-g">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="3" width="18" height="18" rx="2" stroke="#34a853" stroke-width="1.8"/>
                <line x1="3" y1="9"  x2="21" y2="9"  stroke="#34a853" stroke-width="1.5"/>
                <line x1="3" y1="15" x2="21" y2="15" stroke="#34a853" stroke-width="1.5"/>
                <line x1="9" y1="3"  x2="9"  y2="21" stroke="#34a853" stroke-width="1.5"/>
              </svg>
            </div>
            <div>
              <div class="rgf-cloud-title">Connect Google Sheet</div>
              <div class="rgf-cloud-sub">Paste a shared Google Sheets URL to import data directly</div>
            </div>
          </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    c_in, c_btn = st.columns([4, 1], gap="small")
    with c_in:
        st.text_input(
            "Sheet URL",
            placeholder="https://docs.google.com/spreadsheets/d/...",
            label_visibility="collapsed",
            key="rgf_gsheet_url",
        )
    with c_btn:
        if st.button("Import Sheet", type="primary", use_container_width=True, key="rgf_gsheet_btn"):
            st.info("Google Sheets connector isn't wired up yet — set up OAuth credentials and try again.", icon=":material/power:")
    st.markdown(
        '<div class="rgf-cloud-tips">'
        f'<span class="rgf-cloud-tip">{svg("info", size=12)} Sheet must be shared (view access)</span>'
        f'<span class="rgf-cloud-tip">{svg("info", size=12)} First row used as column headers</span>'
        f'<span class="rgf-cloud-tip">{svg("info", size=12)} Auto-detects numeric columns</span>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── GCP Storage tab ──────────────────────────────────────────────────────────
def _render_gcp() -> None:
    st.markdown(
        '''
        <div class="rgf-cloud-card">
          <div class="rgf-cloud-head">
            <div class="rgf-cloud-ico rgf-cloud-ico-blue">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="#4285f4" stroke-width="1.8" stroke-linejoin="round"/>
                <path d="M2 17l10 5 10-5"          stroke="#4285f4" stroke-width="1.8" stroke-linejoin="round"/>
                <path d="M2 12l10 5 10-5"          stroke="#4285f4" stroke-width="1.8" stroke-linejoin="round"/>
              </svg>
            </div>
            <div>
              <div class="rgf-cloud-title">Google Cloud Storage</div>
              <div class="rgf-cloud-sub">Browse or enter a GCS bucket path to import sensor files</div>
            </div>
          </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    c_proj, c_bucket = st.columns(2, gap="small")
    with c_proj:
        st.text_input(
            "GCP Project",
            placeholder="your-gcp-project-id",
            key="rgf_gcp_project",
        )
    with c_bucket:
        st.text_input(
            "Bucket",
            placeholder="your-bucket-name",
            key="rgf_gcp_bucket",
        )

    c_path, c_btn = st.columns([4, 1], gap="small")
    with c_path:
        st.text_input(
            "GCS path",
            placeholder="path/to/sensor-data/ or gs://bucket/file.csv",
            label_visibility="collapsed",
            key="rgf_gcp_path",
        )
    with c_btn:
        if st.button("Browse Bucket", type="primary", use_container_width=True, key="rgf_gcp_btn"):
            st.info("GCS connector isn't wired up yet — add a service-account key in Settings first.", icon=":material/power:")

    # Disconnected-state preview — no fake file listing. Once the
    # connector is wired up this should render the real contents of
    # gs://<bucket>/<path>/. For now it's a clear "not connected" card.
    st.markdown(
        f'''
        <div class="rgf-gcp-browser">
          <div class="rgf-gcp-browser-hdr">Not connected</div>
          <div class="rgf-gcp-browser-empty">
            <span class="rgf-gcp-browser-empty-icon">{svg("database", size=22)}</span>
            <div class="rgf-gcp-browser-empty-text">
              Enter your GCP project + bucket above and click <b>Browse Bucket</b>
              to list files. Requires a service-account key with
              <code>storage.objects.list</code> permission.
            </div>
          </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


# ── Panel wrapping helper — uses st.container(key=) so children are grouped ──
def _panel_open(key: str, title: str, right_html: str = "") -> None:
    """Open a bordered panel using st.container — call within a ``with`` block.

    Note: this renders just the header. The body is whatever the caller puts
    inside the ``with st.container(key=key):`` scope. CSS (targeting
    ``.st-key-<key>``) provides the card chrome.
    """
    actions = f'<div class="rgf-panel-actions">{right_html}</div>'
    st.markdown(
        f'<div class="rgf-panel-hdr">'
        f'<span class="rgf-panel-title">{html_mod.escape(title)}</span>'
        f'{actions}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Data Setup — industry-standard "define your schema" step ───────────────
# One explicit panel with a row per analysis role (Time / Acceleration /
# Load). Each row shows: role label · column picker · unit picker · live
# min/max/n summary computed from the actual data. The user sees at a
# glance what column maps to what role AND what units the pipeline will
# treat it as — so wrong assignments or wrong units are visible before
# any downstream view is rendered.
_TIME_UNIT_CHOICES = [
    ("auto", "Auto (from header)"),
    ("s",    "Seconds (s)"),
    ("ms",   "Milliseconds (ms)"),
    ("us",   "Microseconds (µs)"),
    ("ns",   "Nanoseconds (ns)"),
]
_ACCEL_UNIT_CHOICES = [
    ("auto",   "Auto"),
    ("raw_g",  "Raw sensor (zero-mean → ±1g)"),
    ("g",      "±1g (already centered)"),
    ("mps2",   "Already in m/s²"),
    ("derive", "Derive from Load — a = F / M"),
]
_LOAD_UNIT_CHOICES = [
    ("auto", "Auto (treat as kN)"),
    ("kN",   "kN"),
    ("N",    "Newtons (N)"),
    ("lbf",  "Pound-force (lbf)"),
]


def _pick_col(cols: list[str], candidates: list[str]) -> str | None:
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    for cand in candidates:
        for c in cols:
            if cand.lower() in c.lower():
                return c
    return cols[0] if cols else None


def _render_data_setup() -> None:
    """Unified column-role + unit picker panel.

    Three rows (Time / Acceleration / Load), each row: column picker,
    unit picker, and a live stats chip showing min · max · n for the
    currently-selected column so the user can spot unit mismatches
    (e.g., Load summ peaking at 2,200 means it's in N, not kN).
    """
    info = get_active_info()

    if info:
        ensure_registered(info.table_name)
        v = table_version(info.table_name)
        cols = column_names(info.table_name, v) or ["—"]
    else:
        cols = ["—"]  # placeholder; widgets disabled

    ss = st.session_state

    # First-time OR when the active table changes OR when the auto-pick
    # policy version has been bumped (migration path for users who set
    # their mapping under an older auto-pick rule). Seed the column
    # picks from auto-detection so the user has sensible defaults to
    # override.
    AUTOPICK_VERSION = 2   # bump when the candidate lists change
    current_tbl = info.table_name if info else "_none_"
    needs_reseed = (
        ss.get("_rgf_colmap_table")   != current_tbl
        or ss.get("_rgf_colmap_ver")  != AUTOPICK_VERSION
    )
    if needs_reseed:
        ss["_rgf_colmap_table"] = current_tbl
        ss["_rgf_colmap_ver"]   = AUTOPICK_VERSION
        ss["rgf_map_time"]  = _pick_col(cols, ["time (s)", "time", "t"]) or cols[0]
        ss["rgf_map_accel"] = _pick_col(cols, ["scaled (m/s2)", "acceleration scaled", "accel scaled", "acceleration raw", "accel"]) or cols[0]
        ss["rgf_map_load"]  = _pick_col(cols, ["load (kn)", "load summ", "load sum", "load scaled", "load", "force", "LOAD"]) or cols[0]
        # Reset unit overrides to auto when a new file loads — the old
        # choice usually won't apply to the new file's semantics.
        ss["rgf_unit_time"]  = "auto"
        ss["rgf_unit_accel"] = "auto"
        ss["rgf_unit_load"]  = "auto"

    # Defensive defaults — if anything above missed (e.g. session state
    # partially restored after a hot-reload), fall back to the first
    # available column so widget render never KeyErrors.
    ss.setdefault("rgf_map_time",   cols[0])
    ss.setdefault("rgf_map_accel",  cols[0])
    ss.setdefault("rgf_map_load",   cols[0])
    ss.setdefault("rgf_unit_time",  "auto")
    ss.setdefault("rgf_unit_accel", "auto")
    ss.setdefault("rgf_unit_load",  "auto")

    # Live per-column stats for the three picked columns. Computed in one
    # DuckDB query per file (cached via table_version) so it's free on
    # re-render.
    stats = _column_stats(
        info, v,
        [ss["rgf_map_time"], ss["rgf_map_accel"], ss["rgf_map_load"]],
    ) if info else {}

    with st.container(key="rgf_panel_setup"):
        _panel_open(
            "rgf_panel_setup",
            "Data Setup",
            right_html=(
                badge("Edit anytime", "blue")
                if info else badge("Load a file to begin", "gray")
            ),
        )

        # 3-row layout. Each row = role label + column selector + unit
        # selector + stats chip. Rendered inside Streamlit columns so
        # the widgets line up vertically.
        _render_role_row(
            "TIME",
            "rgf_map_time", "rgf_unit_time",
            cols, _TIME_UNIT_CHOICES,
            stats_for=ss["rgf_map_time"],
            stats=stats,
            disabled=not info,
        )
        # When "Derive from Load" is chosen the accel column is unused
        # — grey it out so the UI reflects the active source of truth.
        accel_col_disabled = (not info) or (ss.get("rgf_unit_accel") == "derive")
        _render_role_row(
            "ACCELERATION",
            "rgf_map_accel", "rgf_unit_accel",
            cols, _ACCEL_UNIT_CHOICES,
            stats_for=ss["rgf_map_accel"],
            stats=stats,
            disabled=not info,
            column_disabled=accel_col_disabled,
        )
        _render_role_row(
            "LOAD",
            "rgf_map_load", "rgf_unit_load",
            cols, _LOAD_UNIT_CHOICES,
            stats_for=ss["rgf_map_load"],
            stats=stats,
            disabled=not info,
        )

        if info:
            st.markdown(
                '<div style="font-size:11px;color:var(--text-3);padding-top:6px;">'
                'Your choices flow into every view — Dashboard, Standard Analysis, '
                'UPM, Cycle, Raw Data, Report. Use the <b>stats chip</b> on the right '
                'to sanity-check ranges — e.g. a load column peaking at 2,000 is in N, '
                'not kN.</div>',
                unsafe_allow_html=True,
            )


def _render_role_row(
    label: str,
    col_key: str,
    unit_key: str,
    cols: list[str],
    unit_choices: list[tuple[str, str]],
    *,
    stats_for: str,
    stats: dict,
    disabled: bool,
    column_disabled: bool | None = None,
) -> None:
    """One row of the Data Setup wizard.

    ``column_disabled`` overrides ``disabled`` for the column picker only
    — lets the caller grey out the column dropdown while keeping the
    unit dropdown live (used when "Derive from Load" is selected).
    """
    if column_disabled is None:
        column_disabled = disabled
    role_col, col_col, unit_col, stats_col = st.columns(
        [0.85, 2.2, 1.6, 1.8], gap="small"
    )
    with role_col:
        st.markdown(
            f'<div class="rgf-setup-role">{label}</div>',
            unsafe_allow_html=True,
        )
    with col_col:
        cur = st.session_state.get(col_key, cols[0])
        st.selectbox(
            "Column",
            cols,
            index=cols.index(cur) if cur in cols else 0,
            key=col_key,
            label_visibility="collapsed",
            disabled=column_disabled,
        )
    with unit_col:
        keys = [k for k, _ in unit_choices]
        cur_unit = st.session_state.get(unit_key, "auto")
        st.selectbox(
            "Unit",
            keys,
            format_func=lambda k: dict(unit_choices)[k],
            index=keys.index(cur_unit) if cur_unit in keys else 0,
            key=unit_key,
            label_visibility="collapsed",
            disabled=disabled,
        )
    with stats_col:
        s = stats.get(stats_for)
        if s:
            st.markdown(
                '<div class="rgf-setup-stats">'
                f'<span>min <b>{_fmt_num(s["min"])}</b></span>'
                f'<span>max <b>{_fmt_num(s["max"])}</b></span>'
                f'<span>n <b>{s["n"]:,}</b></span>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="rgf-setup-stats rgf-setup-stats-empty">—</div>',
                unsafe_allow_html=True,
            )


def _fmt_num(v: float) -> str:
    """Compact sig-3 format — switches to scientific for very large / small."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if f == 0:
        return "0"
    ab = abs(f)
    if ab >= 1e6 or ab < 1e-3:
        return f"{f:.3g}"
    if ab >= 100:
        return f"{f:,.1f}"
    return f"{f:.3f}"


@st.cache_data(show_spinner=False)
def _column_stats(_info, version: float, cols: list[str]) -> dict:
    """One-shot min/max/count aggregation over the picked columns.

    Cached per (table, version, cols) — free on re-render as long as
    nothing's changed. Uses DuckDB so 170k-row files don't hit memory.
    """
    if not _info or not cols:
        return {}
    # Deduplicate the list of columns (3 roles may pick the same col)
    uniq = list(dict.fromkeys(cols))
    from lib.db import get_connection, quote_identifier, quote_table_identifier
    con = get_connection()
    tbl = quote_table_identifier(_info.table_name)
    select_bits = []
    for i, c in enumerate(uniq):
        qc = quote_identifier(c)
        select_bits.extend([
            f"MIN({qc}) AS min_{i}",
            f"MAX({qc}) AS max_{i}",
            f"COUNT({qc}) AS n_{i}",
        ])
    try:
        row = con.execute(f"SELECT {', '.join(select_bits)} FROM {tbl}").fetchone()
    except Exception:
        return {}
    out: dict = {}
    for i, c in enumerate(uniq):
        out[c] = {
            "min": row[i * 3],
            "max": row[i * 3 + 1],
            "n":   row[i * 3 + 2],
        }
    return out


# ── Trim time range panel ───────────────────────────────────────────────────
# Many acquisition rigs log multi-second tails of quiescent data either
# side of the actual impact. Without trimming, integration of any DC
# bias accumulates into multi-meter displacement garbage. This panel
# lets the user crop the time window once at ingest — the choice flows
# into ``run_processing()`` via session state and applies to every view.
def _render_trim_panel() -> None:
    info = get_active_info()
    ss = st.session_state

    ss.setdefault("rgf_trim_mode", "off")     # off / auto / manual
    ss.setdefault("rgf_trim_start_s", 0.0)
    ss.setdefault("rgf_trim_end_s",   0.0)

    with st.container(key="rgf_panel_trim"):
        _panel_open(
            "rgf_panel_trim",
            "Time Range",
            right_html=(
                badge("Trims every view", "blue")
                if info else badge("Load a file to begin", "gray")
            ),
        )

        if not info:
            st.markdown(
                '<div style="font-size:11px;color:var(--text-3);padding:6px 0;">'
                'After importing a file you can trim the working time window '
                'here — useful when acquisitions log long quiet tails on either '
                'side of the impact.</div>',
                unsafe_allow_html=True,
            )
            return

        # Pull the time + load columns the user has picked. We sniff the
        # full time range straight off DuckDB (cached), then offer either
        # auto-crop (event-window detection on Load) or a manual range
        # slider over the actual time values in seconds.
        t_col = ss.get("rgf_map_time")
        l_col = ss.get("rgf_map_load")
        if not (t_col and l_col):
            st.info("Pick the Time + Load columns in Data Setup first.",
                    icon=":material/info:")
            return

        bounds = _time_bounds_seconds(info, t_col)
        if bounds is None:
            st.info("Couldn't read the time column as numeric.",
                    icon=":material/warning:")
            return
        t0, t1 = bounds
        # Apply unit override if set — display range matches the actual
        # seconds the pipeline will see post-conversion.
        time_unit_scale = {
            "s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9,
        }.get(ss.get("rgf_unit_time", "auto"))
        if time_unit_scale is None:
            from lib.processing import infer_time_scale
            time_unit_scale, _ = infer_time_scale(t_col)
        t0_s, t1_s = float(t0) * time_unit_scale, float(t1) * time_unit_scale

        # Mode selector: Off / Auto / Manual
        mode_choices = [
            ("off",    "Use full recording"),
            ("auto",   "Auto-crop to impact (load-driven)"),
            ("manual", "Manual range"),
        ]
        keys = [k for k, _ in mode_choices]
        idx_mode = keys.index(ss["rgf_trim_mode"]) if ss["rgf_trim_mode"] in keys else 0
        st.selectbox(
            "Trim mode",
            keys,
            format_func=lambda k: dict(mode_choices)[k],
            index=idx_mode,
            key="rgf_trim_mode",
        )

        if ss["rgf_trim_mode"] == "manual":
            # Streamlit's slider has decent precision, but for sub-ms
            # impact widths the user wants float seconds with 4-digit
            # resolution. Step = (range / 500) gives ~500 detents.
            span = max(t1_s - t0_s, 1e-6)
            step = max(span / 500.0, 1e-6)
            cur_start = max(t0_s, min(ss.get("rgf_trim_start_s") or t0_s, t1_s))
            cur_end   = max(t0_s, min(ss.get("rgf_trim_end_s")   or t1_s, t1_s))
            if cur_end <= cur_start:
                cur_start, cur_end = t0_s, t1_s
            picked = st.slider(
                f"Range (s) — full file: {t0_s:.4f} → {t1_s:.4f}",
                min_value=float(t0_s), max_value=float(t1_s),
                value=(float(cur_start), float(cur_end)),
                step=float(step),
                key="rgf_trim_slider",
            )
            ss["rgf_trim_start_s"], ss["rgf_trim_end_s"] = picked

        elif ss["rgf_trim_mode"] == "auto":
            st.markdown(
                '<div style="font-size:11px;color:var(--text-3);padding:4px 0;">'
                'Auto-crop runs <code>detect_event_window</code> on the Load '
                'signal at 20% peak threshold + 50-sample contiguous-below-'
                'threshold rule, anchored at the load peak. Window applies '
                'to every downstream view.'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="font-size:11px;color:var(--text-3);padding:4px 0;">'
                'No trimming — every view sees the full recording. Switch '
                'to <b>Auto-crop</b> for impact-only analysis or <b>Manual '
                'range</b> to pick the window yourself.'
                '</div>',
                unsafe_allow_html=True,
            )


@st.cache_data(show_spinner=False)
def _time_bounds_seconds(_info, time_col: str) -> tuple[float, float] | None:
    """Min/max of the time column from DuckDB. Returns raw values
    (no unit conversion); caller applies the unit scale.
    """
    try:
        from lib.db import get_connection, quote_identifier, quote_table_identifier
        con = get_connection()
        tbl = quote_table_identifier(_info.table_name)
        qc = quote_identifier(time_col)
        row = con.execute(f"SELECT MIN({qc}), MAX({qc}) FROM {tbl}").fetchone()
        if row is None:
            return None
        lo, hi = row
        if lo is None or hi is None:
            return None
        return float(lo), float(hi)
    except Exception:
        return None


# ── Imported Files list ──────────────────────────────────────────────────────
def _render_file_list() -> None:
    tables = imported_tables()
    active = get_active_table()

    right_html = ""
    if tables:
        right_html = (
            '<button type="button" class="rgf-btn-sm" data-clear="all">Clear All</button>'
        )

    with st.container(key="rgf_panel_files"):
        _panel_open("rgf_panel_files", "Imported Files", right_html=right_html)
        if not tables:
            _render_files_empty()
        else:
            rows = []
            for tname in tables:
                info = load_metadata(tname)
                if info is None:
                    continue
                is_active = tname == active
                size_str = _format_size(info.parquet_path)
                date_str = _format_date(info.ingested_at)
                status_html = badge("Active", "green") if is_active else badge("Imported", "gray")
                rows.append(
                    f'<button type="button" class="rgf-file-row" data-activate="{tname}">'
                    f'<div class="rgf-file-ico rgf-file-ico-upload">{svg("report", size=18)}</div>'
                    f'<div style="flex:1; min-width:0; text-align:left;">'
                    f'<div class="rgf-file-name">{html_mod.escape(info.source_filename or info.table_name)}</div>'
                    f'<div class="rgf-file-meta">'
                    f'{size_str} · {info.row_count:,} rows · {info.column_count} cols · {date_str}'
                    f'<span class="rgf-file-src-chip">File</span>'
                    f'</div>'
                    f'</div>'
                    f'{status_html}'
                    f'</button>'
                )
            st.markdown("\n".join(rows), unsafe_allow_html=True)


def _render_files_empty() -> None:
    st.markdown(
        f'<div class="rgf-files-empty">'
        f'<div class="rgf-files-empty-icon">{svg("folder", size=32)}</div>'
        '<div class="rgf-files-empty-title">No files imported yet</div>'
        '<div class="rgf-files-empty-msg">Upload a file above, or try the demo dataset below.</div>'
        '<button type="button" class="rgf-btn-primary" data-action="load-demo">'
        'Load Demo Dataset</button>'
        '</div>',
        unsafe_allow_html=True,
    )


def _format_size(path_str: str) -> str:
    try:
        sz = os.path.getsize(path_str)
    except OSError:
        return "—"
    if sz < 1024:
        return f"{sz} B"
    if sz < 1024 * 1024:
        return f"{sz / 1024:.0f} KB"
    return f"{sz / 1024 / 1024:.1f} MB"


def _format_date(ts: float) -> str:
    try:
        return time.strftime("%Y-%m-%d", time.localtime(ts))
    except (ValueError, OSError):
        return "—"


# ── Data Preview ─────────────────────────────────────────────────────────────
def _render_data_preview() -> None:
    info = get_active_info()
    right_html = (
        f'<span style="font-size:11px;color:var(--text-3);font-family:var(--mono);">'
        f'{"Showing first 8 rows" if info else "no active dataset"}</span>'
    )
    with st.container(key="rgf_panel_preview"):
        _panel_open("rgf_panel_preview", "Data Preview", right_html=right_html)
        if not info:
            empty_state("eye_off", "Nothing to preview",
                        "Select a file from the list above to preview its first rows.")
        else:
            ensure_registered(info.table_name)
            v = table_version(info.table_name)
            df = head(info.table_name, v, 8)
            _render_preview_table(df)


def _render_preview_table(df: pd.DataFrame) -> None:
    if df.empty:
        empty_state("", "Empty result", "The active table has no rows.")
        return
    cols = ["#"] + list(df.columns)
    ths = "".join(f'<th>{html_mod.escape(str(c))}</th>' for c in cols)
    rows = []
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        tds = [f'<td class="rgf-preview-idx">{i}</td>']
        for c in df.columns:
            tds.append(f'<td>{_fmt_preview(row[c])}</td>')
        rows.append(f'<tr>{"".join(tds)}</tr>')
    st.markdown(
        f'<div style="overflow-x:auto">'
        f'<table class="rgf-preview-tbl">'
        f'<thead><tr>{ths}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table></div>',
        unsafe_allow_html=True,
    )


def _fmt_preview(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        a = abs(v)
        if a == 0:
            return "0"
        if a < 0.001:
            return f"{v:.3e}"
        if a < 1:
            return f"{v:.6f}"
        if a < 1000:
            return f"{v:.4f}"
        return f"{v:,.2f}"
    return html_mod.escape(str(v))
