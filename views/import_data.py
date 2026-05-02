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
from lib.queries import head
from lib.sources import manual
from lib.state import (
    add_imported, get_active_info, get_active_table,
    imported_tables, remove_imported, session_id, set_active_table,
)
# Data Setup + Trim panels live in a sibling module to keep this file
# focused on source-tab dispatch + file list + preview. The shared
# ``_panel_open`` chrome helper lives there too — re-imported here for
# the imported-files / data-preview panels.
from views._import_panels import _panel_open, render_data_setup, render_trim_panel

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

    render_data_setup()
    render_trim_panel()
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
