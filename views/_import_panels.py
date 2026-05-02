"""views/_import_panels.py — Data Setup + Trim panels for Import Data.

Both panels are tightly coupled (share session-state keys, share the
``_panel_open`` chrome helper, share the auto-pick stats query) so they
live together in one private module. ``views.import_data`` imports
``render_data_setup`` and ``render_trim_panel`` and calls them from its
top-level render(). Module name is underscore-prefixed so it doesn't
show up as a sibling view in any directory listing of ``views/``.
"""
from __future__ import annotations

import html as html_mod

import streamlit as st

from lib.cache import ensure_registered, table_version
from lib.components import badge
from lib.queries import column_names
from lib.state import get_active_info


# ── Panel wrapping helper ───────────────────────────────────────────────────
def _panel_open(key: str, title: str, right_html: str = "") -> None:
    """Open a bordered panel using ``st.container`` — call within a
    ``with`` block. Renders just the header; the body is whatever the
    caller puts inside the surrounding ``with st.container(key=key):``
    scope. CSS (targeting ``.st-key-<key>``) provides the card chrome.
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
# Different acquisition systems log in different units. ``run_processing``
# auto-detects from the column header when it can, but headers aren't
# always reliable — this panel lets the user force the interpretation.
# Values flow into session state under ``rgf_unit_*`` and
# ``lib/processing.py`` reads them before feeding ``compute()``.
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
    """Header-based fuzzy column picker — exact match first, then
    substring. Used as a fallback when the smart auto-pick can't load
    the column data."""
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    for cand in candidates:
        for c in cols:
            if cand.lower() in c.lower():
                return c
    return cols[0] if cols else None


def render_data_setup() -> None:
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
    AUTOPICK_VERSION = 3   # v3: signal-quality scoring + derive fallback
    current_tbl = info.table_name if info else "_none_"
    needs_reseed = (
        ss.get("_rgf_colmap_table")  != current_tbl
        or ss.get("_rgf_colmap_ver") != AUTOPICK_VERSION
    )
    if needs_reseed:
        ss["_rgf_colmap_table"] = current_tbl
        ss["_rgf_colmap_ver"]   = AUTOPICK_VERSION
        # Time + Load: header-based pick (fast, no data scan needed)
        ss["rgf_map_time"]  = _pick_col(cols, ["time (s)", "time", "t"]) or cols[0]
        ss["rgf_map_load"]  = _pick_col(cols, ["load (kn)", "load summ", "load sum", "load scaled", "load", "force", "LOAD"]) or cols[0]
        # Accel: SCORED pick. Scan every column whose name contains
        # "accel", measure how well each one tracks the load impact
        # (peak-time alignment + SNR + saturation penalty), and use the
        # best. If nothing scores well, switch to Derive-from-Load so
        # the user immediately gets correct charts on files where the
        # accel sensor was dead / off-event / saturated.
        accel_candidates = [c for c in cols if "accel" in c.lower()]
        if not accel_candidates:
            accel_candidates = [_pick_col(cols, ["scaled (m/s2)", "acceleration scaled", "accel scaled", "acceleration raw", "accel"]) or cols[0]]
        ss["rgf_unit_time"] = "auto"
        ss["rgf_unit_load"] = "auto"
        try:
            from lib.processing import auto_pick_accel
            picked, score, mode = auto_pick_accel(
                info.table_name, ss["rgf_map_time"], ss["rgf_map_load"],
                accel_candidates, version=v,
            )
            ss["rgf_map_accel"]  = picked or accel_candidates[0]
            ss["rgf_unit_accel"] = "derive" if mode == "derive" else "auto"
            ss["_rgf_accel_score"] = float(score)
            ss["_rgf_accel_mode"]  = mode
        except Exception:
            ss["rgf_map_accel"]  = accel_candidates[0]
            ss["rgf_unit_accel"] = "auto"
            ss["_rgf_accel_score"] = 0.0
            ss["_rgf_accel_mode"]  = "sensor"

    # Defensive defaults — if anything above missed (e.g. session state
    # partially restored after a hot-reload), fall back to the first
    # available column so widget render never KeyErrors.
    ss.setdefault("rgf_map_time",   cols[0])
    ss.setdefault("rgf_map_accel",  cols[0])
    ss.setdefault("rgf_map_load",   cols[0])
    ss.setdefault("rgf_unit_time",  "auto")
    ss.setdefault("rgf_unit_accel", "auto")
    ss.setdefault("rgf_unit_load",  "auto")

    # Live per-column stats for the three picked columns. Computed in
    # one DuckDB query per file (cached via table_version) so it's free
    # on re-render.
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
            stats_for=ss["rgf_map_time"], stats=stats,
            disabled=not info,
        )
        # When "Derive from Load" is chosen the accel column is unused
        # — grey it out so the UI reflects the active source of truth.
        accel_col_disabled = (not info) or (ss.get("rgf_unit_accel") == "derive")
        _render_role_row(
            "ACCELERATION",
            "rgf_map_accel", "rgf_unit_accel",
            cols, _ACCEL_UNIT_CHOICES,
            stats_for=ss["rgf_map_accel"], stats=stats,
            disabled=not info,
            column_disabled=accel_col_disabled,
        )
        _render_role_row(
            "LOAD",
            "rgf_map_load", "rgf_unit_load",
            cols, _LOAD_UNIT_CHOICES,
            stats_for=ss["rgf_map_load"], stats=stats,
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
            "Column", cols,
            index=cols.index(cur) if cur in cols else 0,
            key=col_key,
            label_visibility="collapsed",
            disabled=column_disabled,
        )
    with unit_col:
        keys = [k for k, _ in unit_choices]
        cur_unit = st.session_state.get(unit_key, "auto")
        st.selectbox(
            "Unit", keys,
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
    uniq = list(dict.fromkeys(cols))   # de-dupe (3 roles may share a col)
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
def render_trim_panel() -> None:
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
            # ``step = (range / 500)`` gives ~500 detents — fine enough
            # for sub-ms impact widths without making the slider sluggish.
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
