"""lib/bridge.py — JS click-dispatch bridge.

Streamlit's HTML sanitiser strips inline ``onclick`` handlers, so the
visible HTML buttons (sidebar nav, source tabs, cycle pills, settings
tabs, etc.) can't directly fire Streamlit-side state updates. The
bridge instead:

* Renders an iframe containing a single capture-phase ``click`` listener
  attached to ``parent.document``.
* When the listener sees an element with one of the known ``data-*``
  attributes, it locates the matching hidden ``st.button`` (keyed
  ``__<prefix>_<value>``) and ``.click()``s it, which Streamlit picks
  up over the websocket and reruns the script.
* The handler is attached only once (``doc.__rgfBridged`` flag) but
  the iframe is re-injected on every rerun — Streamlit removes the
  iframe from the DOM whenever it isn't in the current render tree,
  and that GCs the closure that holds the handler. Re-injecting keeps
  it alive.

To add a new prefix-attribute → key mapping, append to ``ATTRS`` at
the top of the inline script. To add a non-prefix one-off
(data-action="..."), extend the action chain near the bottom.
"""
from __future__ import annotations

import streamlit.components.v1 as components


_BRIDGE_HTML = """
<script>
(function () {
  const doc = window.parent && window.parent.document;
  if (!doc || doc.__rgfBridged) return;

  const ATTRS = [
    ['data-nav',           '.st-key-__nav_'],
    ['data-src',           '.st-key-__src_'],
    ['data-activate',      '.st-key-__activate_'],
    ['data-cycle',         '.st-key-__cycle_'],
    ['data-cb-type',       '.st-key-__cb_type_'],
    ['data-cb-y',          '.st-key-__cb_y_'],
    ['data-rb-toggle',     '.st-key-__rb_toggle_'],
    ['data-rd-page',       '.st-key-__rd_page_'],
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
      // data-action handlers (non-prefix one-offs)
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
          // Download the Chart Builder canvas as PNG. The canvas lives
          // inside an st.components.v1.html iframe — reach into its
          // contentDocument and use toBlob().
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
          // st.download_button renders as an <a> (with a child <button>).
          // Clicking the <a> fires the download. We click whichever of
          // the two the bridge finds first.
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
"""


def inject_click_bridge() -> None:
    """Render the JS bridge iframe (height=0). Idempotent — the script
    short-circuits via ``doc.__rgfBridged`` so per-rerun cost is O(1)."""
    components.html(_BRIDGE_HTML, height=0)
