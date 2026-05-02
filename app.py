"""RGF Geotechnical Analysis — sidebar-navigated dashboard.

Routing pattern (avoids full page reload, matches SPA behaviour of the
reference design mock):

    * Visible HTML nav items carry a ``data-nav="<view_id>"`` attribute.
    * A small injected script (via ``st.components.v1.html``) runs in an
      iframe, reaches up to ``parent.document``, and attaches a click
      handler to every ``[data-nav]`` element. On click it locates the
      matching hidden ``st.button`` (``.st-key-__nav_<vid> button``) and
      calls ``.click()``.
    * Streamlit receives the click over its websocket, the hidden
      button's handler sets ``st.session_state.view`` plus
      ``st.query_params["view"]`` (URL stays shareable), then reruns.
    * The sidebar HTML regenerates with the new active class.

Inline ``onclick`` attributes are stripped by Streamlit's HTML
sanitizer, so the JS must be injected via components.v1.html (iframe,
unsanitised JS context) rather than a ``<script>`` block in markdown.
"""
from __future__ import annotations

import html as html_mod

import streamlit as st

# Page config must be first Streamlit call
st.set_page_config(
    page_title="RGF Geotechnical Analysis",
    # Material Symbols shortcode — ``:material/<name>:`` — renders a
    # proper vector favicon in the browser tab instead of the emoji
    # chart glyph. Any Material Symbols name works.
    page_icon=":material/ssid_chart:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from lib.cache import ensure_all_imported_registered
from lib.icons import svg
from lib.state import get_active_info, imported_tables, session_id
from lib.theme import install_theme

install_theme()
session_id()
ensure_all_imported_registered(imported_tables())


# ── Navigation metadata ────────────────────────────────────────────────────
NAV: list[tuple[str, str, str]] = [
    # (view_id, label, icon_name)
    ("dashboard", "Dashboard",         "dashboard"),
    ("import",    "Import Data",       "upload"),
    ("standard",  "Standard Analysis", "chart"),
    ("upm",       "UPM Analysis",      "wave"),
    ("cycles",    "Cycle Analysis",    "cycle"),
    ("builder",   "Chart Builder",     "layers"),
    ("report",    "Report Builder",    "report"),
    ("data",      "Raw Data",          "table"),
    ("settings",  "Settings",          "settings"),
]
_VALID_VIEWS = {v for v, _, _ in NAV}


# ── Initialize active view from URL or default ─────────────────────────────
if "view" not in st.session_state:
    qp = st.query_params.get("view", "dashboard")
    if isinstance(qp, list):
        qp = qp[0] if qp else "dashboard"
    st.session_state.view = qp if qp in _VALID_VIEWS else "dashboard"

active_view = st.session_state.view


# ── Sidebar collapse state (click logo or header toggle to flip) ───────────
if "sidebar_collapsed" not in st.session_state:
    st.session_state.sidebar_collapsed = False

# Hidden trigger for the sidebar toggle — wired to the logo/header via
# data-action="toggle-sidebar" in the JS bridge.
if st.button("·", key="__sidebar_toggle"):
    st.session_state.sidebar_collapsed = not st.session_state.sidebar_collapsed
    st.rerun()


# ── Hidden trigger buttons (one per nav item) ──────────────────────────────
# Rendered via real st.button widgets so clicks go over the websocket (no
# browser navigation). The visible <a> items in the sidebar HTML dispatch to
# these via JS: document.querySelector('.st-key-__nav_<vid> button').click()
for vid, _label, _icon in NAV:
    if st.button("·", key=f"__nav_{vid}"):
        st.session_state.view = vid
        st.query_params["view"] = vid
        st.rerun()


# ── Sidebar footer: active-test summary ────────────────────────────────────
def _footer_html() -> str:
    info = get_active_info()
    if not info:
        return (
            '<div class="rgf-sb-foot-lbl">No Active Test</div>'
            '<div class="rgf-sb-foot-name">Import a file to begin</div>'
        )
    name = html_mod.escape(info.source_filename or info.table_name)
    meta = f"{info.row_count:,} rows · {info.column_count} cols"
    return (
        '<div class="rgf-sb-foot-lbl">Active Test</div>'
        f'<div class="rgf-sb-foot-name">{name}</div>'
        f'<div class="rgf-sb-foot-meta">{meta}</div>'
    )


# ── Render the visible sidebar (static HTML, click-through to hidden btns) ─
_nav_items: list[str] = []
for vid, label, icon_name in NAV:
    cls = "rgf-nav-item" + (" active" if vid == active_view else "")
    # data-nav dispatches to the hidden st.button via the JS bridge.
    # data-label drives the collapsed-state hover tooltip.
    _nav_items.append(
        f'<button type="button" class="{cls}" data-nav="{vid}" '
        f'data-label="{html_mod.escape(label)}">'
        f'<span class="rgf-nav-icon">{svg(icon_name, size=18)}</span>'
        f'<span class="rgf-nav-label">{html_mod.escape(label)}</span>'
        f'</button>'
    )

sidebar_cls = "rgf-sidebar"
if st.session_state.get("sidebar_collapsed"):
    sidebar_cls += " rgf-sidebar-collapsed"

st.markdown(
    f"""
    <div class="{sidebar_cls}">
      <div class="rgf-logo" data-action="toggle-sidebar" title="Toggle sidebar">
        <div class="rgf-logo-mark">RP</div>
        <div class="rgf-logo-text">
          <div class="rgf-logo-title">RPLT</div>
          <div class="rgf-logo-sub">RGF Geotechnical</div>
        </div>
      </div>
      <div class="rgf-nav-list">{"".join(_nav_items)}</div>
      <div class="rgf-sidebar-footer">{_footer_html()}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Click-dispatch bridge (iframe-scoped script) ────────────────────────────
# Wires every element with a data-nav/data-src/data-activate attribute in
# parent.document to its matching hidden Streamlit button. The listener
# has to be (re-)attached inside an iframe that Streamlit keeps alive —
# if we skip injecting on some reruns, Streamlit removes the iframe from
# the DOM and the browser invalidates the closure holding the handler,
# which breaks every click. So we always inject; the script short-circuits
# on re-entry via ``doc.__rgfBridged`` so the work per rerun is O(1).
st.components.v1.html(
    """
    <script>
    (function () {
      const doc = window.parent && window.parent.document;
      if (!doc || doc.__rgfBridged) return;

      const ATTRS = [
        ['data-nav',      '.st-key-__nav_'],
        ['data-src',      '.st-key-__src_'],
        ['data-activate', '.st-key-__activate_'],
        ['data-cycle',    '.st-key-__cycle_'],
        ['data-cb-type',  '.st-key-__cb_type_'],
        ['data-cb-y',     '.st-key-__cb_y_'],
        ['data-rb-toggle', '.st-key-__rb_toggle_'],
        ['data-rd-page',  '.st-key-__rd_page_'],
        ['data-settings-tab', '.st-key-__settings_tab_'],
        ['data-std-composite', '.st-key-__std_composite_'],
      ];

      if (!doc.__rgfBridged) {
        doc.__rgfBridged = true;
        doc.addEventListener('click', (ev) => {
          // Prefix-attribute dispatch: data-nav / data-src / …
          for (const [attr, prefix] of ATTRS) {
            const el = ev.target.closest('[' + attr + ']');
            if (!el) continue;
            ev.preventDefault(); ev.stopPropagation();
            const key = el.getAttribute(attr);
            const hidden = doc.querySelector(prefix + key + ' button');
            if (hidden) hidden.click();
            return;
          }
          // data-clear="all" → Clear All files button
          const clr = ev.target.closest('[data-clear]');
          if (clr) {
            ev.preventDefault(); ev.stopPropagation();
            const btn = doc.querySelector('.st-key-__clear_all_files button');
            if (btn) btn.click();
            return;
          }
          // data-action handlers
          const actEl = ev.target.closest('[data-action]');
          if (actEl) {
            ev.preventDefault(); ev.stopPropagation();
            const action = actEl.getAttribute('data-action');
            if (action === 'load-demo') {
              const btn = doc.querySelector('.st-key-__load_demo button');
              if (btn) btn.click();
            } else if (action === 'toggle-sidebar') {
              const btn = doc.querySelector('.st-key-__sidebar_toggle button');
              if (btn) btn.click();
            } else if (action === 'cb-toggle-sql') {
              const btn = doc.querySelector('.st-key-__cb_toggle_sql button');
              if (btn) btn.click();
            } else if (action === 'cb-download') {
              // Download the Chart Builder canvas as PNG. The canvas
              // lives inside an st.components.v1.html iframe — reach
              // into its contentDocument and use toBlob().
              const iframe = doc.querySelector(
                '[class*="st-key-rgf_chart_panel_cb_"] iframe, '
                + '[class*="st-key-rgf_chart_panel_"] iframe'
              );
              const cv = iframe && iframe.contentDocument
                         && iframe.contentDocument.getElementById('c');
              if (cv) {
                const out = document.createElement('canvas');
                out.width = cv.width; out.height = cv.height;
                const octx = out.getContext('2d');
                octx.fillStyle = '#0a0f18';
                octx.fillRect(0, 0, out.width, out.height);
                octx.drawImage(cv, 0, 0);
                out.toBlob((blob) => {
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url; a.download = 'chart_builder.png';
                  document.body.appendChild(a); a.click();
                  document.body.removeChild(a); URL.revokeObjectURL(url);
                });
              }
            } else if (action === 'rd-filter-toggle') {
              const btn = doc.querySelector('.st-key-__rd_filter_btn button');
              if (btn) btn.click();
            } else if (action === 'rd-export-csv') {
              // st.download_button renders as an <a> (with a child
              // <button>). Clicking the <a> fires the download. We click
              // whichever of the two the bridge finds first.
              const dl = doc.querySelector(
                '.st-key-__rd_export_csv a, .st-key-__rd_export_csv button'
              );
              if (dl) dl.click();
            } else if (action === 'export-dashboard') {
              // Dashboard Export — downloads the processed dataset as CSV.
              const dl = doc.querySelector(
                '.st-key-__dash_export_csv a, .st-key-__dash_export_csv button'
              );
              if (dl) dl.click();
            } else if (action === 'settings-save') {
              const btn = doc.querySelector('.st-key-__settings_save button');
              if (btn) btn.click();
            } else if (action === 'settings-reset') {
              const btn = doc.querySelector('.st-key-__settings_reset button');
              if (btn) btn.click();
            } else if (action === 'rb-generate-pdf') {
              // Scope the print to the Report Builder's preview card:
              // add .rgf-printing-report on <body> → the @media print
              // rules in rgf.css hide everything else. Give the browser
              // a tick to apply the style change before opening the
              // dialog (otherwise Chrome occasionally snapshots the
              // pre-style DOM). Cleans up on afterprint.
              const parentBody = doc.body;
              parentBody.classList.add('rgf-printing-report');
              const restore = () => {
                parentBody.classList.remove('rgf-printing-report');
                window.parent.removeEventListener('afterprint', restore);
              };
              window.parent.addEventListener('afterprint', restore);
              setTimeout(() => {
                try { window.parent.print(); }
                catch (err) {
                  console.error('[rb-generate-pdf] print failed:', err);
                  restore();
                }
              }, 80);
            } else if (action === 'cb-print') {
              // Tag <body> with .rgf-printing so the @media print rules
              // in rgf.css hide everything except the Chart Builder's
              // current chart iframe. Untag after the dialog closes
              // (afterprint event) so the page returns to normal.
              const parentBody = doc.body;
              parentBody.classList.add('rgf-printing');
              const restore = () => {
                parentBody.classList.remove('rgf-printing');
                window.parent.removeEventListener('afterprint', restore);
              };
              window.parent.addEventListener('afterprint', restore);
              window.parent.print();
            }
            return;
          }
        }, true);  // capture phase — fires before Streamlit's own handlers
      }
    })();
    </script>
    """,
    height=0,
)


# ── Dispatch to the active view ────────────────────────────────────────────
if active_view == "dashboard":
    from views.dashboard import render as _render
elif active_view == "import":
    from views.import_data import render as _render
elif active_view == "standard":
    from views.standard_analysis import render as _render
elif active_view == "upm":
    from views.upm_analysis import render as _render
elif active_view == "cycles":
    from views.cycle_analysis import render as _render
elif active_view == "builder":
    from views.chart_builder import render as _render
elif active_view == "report":
    from views.report_builder import render as _render
elif active_view == "data":
    from views.raw_sample import render as _render
elif active_view == "settings":
    from views.settings import render as _render
else:
    from views.dashboard import render as _render

_render()
