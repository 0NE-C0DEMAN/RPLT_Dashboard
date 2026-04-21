"""Settings view — processing defaults that actually drive the pipeline.

Everything in this view writes to session state keys that
``lib/processing.py::get_params()`` reads. Nothing else in the app touches
these values, so if it's here it matters.

Layout (single view, no tab bar — there's one section now; tabs will
come back if/when we add more domains):

    PageHeader "Settings" | subtitle
    ───────────────────────────────────────────────────────
    Panel: Smoothing Defaults
      Apply Smoothing  | Smoothing Window  | Smoothing Weight
    Panel: UPM Defaults
      Default Mass (kg) | Default Stiffness (N/m)

    ───────────────────────────────────────────────────────
                      [Reset to Defaults] [Save Settings]

Previous iterations of this view had Company Information, Sensor
Calibration, PDF / Chart Export, and GCP Connection tabs. They were all
cosmetic — not one of their session-state keys was ever read by the
processing pipeline, Chart Builder, Report Builder, or anything else.
They've been deleted. Values that belong at the report or dataset level
(project name, client, engineer) live in the Report Builder's own
settings panel instead.
"""
from __future__ import annotations

import html as html_mod
from contextlib import contextmanager

import streamlit as st

from lib.components import page_header


# ── Defaults — empty strings for numbers so the user is forced to enter
#    per-test values. The pipeline still has hard-coded fallbacks in
#    ``lib/processing.py`` if the user leaves everything blank. ──────────
_DEFAULTS = {
    "settings_smoothing_on":     "Enabled by default",
    "settings_smoothing_window": "120",
    "settings_smoothing_weight": "linear",
    "settings_upm_mass":         "",   # intentionally blank — per-test
    "settings_upm_stiffness":    "",   # intentionally blank — per-test
}


def render() -> None:
    ss = st.session_state
    for k, v in _DEFAULTS.items():
        ss.setdefault(k, v)

    # Save + Reset hidden triggers — bridged from the footer action buttons.
    # ``:material/<name>:`` references Streamlit's built-in Material Symbols
    # set, so the toast ships a proper vector icon instead of an emoji.
    if st.button("·", key="__settings_save"):
        st.toast("Settings saved", icon=":material/check_circle:")
    if st.button("·", key="__settings_reset"):
        for k, v in _DEFAULTS.items():
            ss[k] = v
        st.toast("Settings reset to defaults", icon=":material/restart_alt:")
        st.rerun()

    page_header(
        "Settings",
        "Processing defaults used by every view. Leave mass / stiffness "
        "blank and enter them per-test, or set house defaults here.",
    )

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        with _panel("Smoothing Defaults"):
            _select("Apply Smoothing", "settings_smoothing_on",
                    ["Enabled by default", "Disabled by default"])
            _number(
                "Smoothing Window",
                "settings_smoothing_window",
                min_value=2, max_value=10_000, step=1,
                help_text="Range: 2 – 10,000 samples. Larger = smoother but "
                          "more delay through the impact peak.",
            )
            _select("Smoothing Weight", "settings_smoothing_weight",
                    ["linear", "exponential", "uniform"])
    with col2:
        with _panel("UPM Defaults"):
            _text(
                "Default Mass (kg)", "settings_upm_mass", mono=True,
                help_text="Reaction-mass of the drop weight. Per-test value "
                          "— leave blank and enter it on Standard Analysis "
                          "if it varies by rig.",
                placeholder="e.g. 12,000",
            )
            _text(
                "Default Stiffness (N/m)", "settings_upm_stiffness", mono=True,
                help_text="Pile-soil system stiffness. Typical range: "
                          "10⁵ – 10⁷ N/m.",
                placeholder="e.g. 1,397,000",
            )

    # ── Footer: Reset + Save buttons ───────────────────────────────────────
    st.markdown(
        '<div class="rgf-settings-footer">'
        '<button type="button" class="rgf-btn-sm" '
        'data-action="settings-reset">Reset to Defaults</button>'
        '<button type="button" class="rgf-btn-save" '
        'data-action="settings-save">Save Settings</button>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Panel helpers ───────────────────────────────────────────────────────────
_PANEL_COUNTER = {"n": 0}


def _slug(title: str) -> str:
    return (
        title.lower()
             .replace("&", "and")
             .replace(" ", "_")
             .replace("-", "_")
             .replace(",", "")
             .replace(".", "")
    )


@contextmanager
def _panel(title: str):
    """Open a ChartPanel-style container as a REAL DOM container.

    ``st.container(key=...)`` renders a ``<div class="st-key-<key>">``
    with the child widgets as actual DOM descendants, so the CSS card
    chrome wraps them. Using a unique counter in the key avoids
    collisions when the same title appears twice in the layout.
    """
    _PANEL_COUNTER["n"] += 1
    key = f"rgf_set_pnl_{_slug(title)}_{_PANEL_COUNTER['n']}"
    c = st.container(key=key)
    with c:
        st.markdown(
            f'<div class="rgf-settings-panel-hdr">{html_mod.escape(title)}</div>',
            unsafe_allow_html=True,
        )
        yield


def _label(label: str) -> None:
    st.markdown(
        f'<div class="rgf-settings-label">{html_mod.escape(label)}</div>',
        unsafe_allow_html=True,
    )


def _text(label: str, session_key: str, *, mono: bool = False,
          help_text: str = "", placeholder: str = "") -> None:
    _label(label)
    cls = "rgf-mono-field" if mono else "rgf-text-field"
    st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
    st.session_state[session_key] = st.text_input(
        label, value=str(st.session_state.get(session_key, "")),
        label_visibility="collapsed", key=f"{session_key}_inp",
        placeholder=placeholder,
    )
    st.markdown('</div>', unsafe_allow_html=True)
    if help_text:
        st.markdown(
            f'<div class="rgf-settings-hint-sm">{html_mod.escape(help_text)}</div>',
            unsafe_allow_html=True,
        )


def _number(label: str, session_key: str, *, min_value: int, max_value: int,
            step: int = 1, help_text: str = "") -> None:
    _label(label)
    st.markdown('<div class="rgf-mono-field">', unsafe_allow_html=True)
    # The session-state key stores the value as a string so string- and
    # number-backed widgets can share ``_parse_number`` downstream.
    try:
        cur = int(str(st.session_state.get(session_key, min_value)).replace(",", ""))
    except (ValueError, TypeError):
        cur = min_value
    picked = st.number_input(
        label,
        value=max(min_value, min(max_value, cur)),
        min_value=min_value, max_value=max_value, step=step,
        label_visibility="collapsed", key=f"{session_key}_inp",
    )
    st.session_state[session_key] = str(int(picked))
    st.markdown('</div>', unsafe_allow_html=True)
    if help_text:
        st.markdown(
            f'<div class="rgf-settings-hint-sm">{html_mod.escape(help_text)}</div>',
            unsafe_allow_html=True,
        )


def _select(label: str, session_key: str, options: list[str]) -> None:
    _label(label)
    current = st.session_state.get(session_key, options[0])
    idx = options.index(current) if current in options else 0
    st.session_state[session_key] = st.selectbox(
        label, options, index=idx,
        label_visibility="collapsed", key=f"{session_key}_inp",
    )
