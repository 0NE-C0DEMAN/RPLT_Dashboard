"""Shared processing module — centralizes compute, params, and utils.

Used by standard_analysis, upm_analysis, and any future view that needs
RPLT processing. No view should duplicate this logic.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import streamlit as st

from .db import quote_identifier, quote_table_identifier
from .queries import run_custom_query
from .engine import compute


# ── Unit inference — look at the column header to figure out what
# the user's data is actually in, so the dashboard produces sensible
# numbers for any acquisition format, not just the RGF demo file. ──────────

_TIME_SCALE = {
    # (regex against lowercased header) → multiplier that takes the raw
    # value to seconds. Order matters — most specific first.
    r"\bs(ec(onds?)?)?\b": 1.0,
    r"\bms\b|millisec": 1e-3,
    r"\bus\b|\bμs\b|microsec": 1e-6,
    r"\bns\b|nanosec": 1e-9,
}


def infer_time_scale(col_name: str) -> tuple[float, str]:
    """Return ``(multiplier, detected_unit)`` based on the header.

    Examples
    --------
    >>> infer_time_scale("Time (us)")
    (1e-6, 'us')
    >>> infer_time_scale("Time (s)")
    (1.0, 's')
    >>> infer_time_scale("Timestamp")
    (1.0, 's')     # fall-through default
    """
    low = col_name.lower()
    # Strip out the base name — keep whatever's in the unit parentheses
    # or whatever sits after it
    for pattern, mult in _TIME_SCALE.items():
        if re.search(pattern, low):
            label = re.search(pattern, low).group(0)
            return mult, label
    return 1.0, "s"


def _score_accel_signal(
    load: np.ndarray, accel: np.ndarray, t: np.ndarray,
) -> float:
    """Score how plausibly an accel column is the impact accelerometer.

    Returns a value in [0, 1]. Higher = the column's peak lines up with
    the load impact and stands clear of its noise floor. Used to auto-
    pick the right accel channel on multi-channel acquisitions and to
    auto-fall-back to Derive-from-Load when no column qualifies.

    Components:
      * **Time alignment** — how close is the accel's peak (centered)
        to the load peak, scaled by total recording duration.
      * **SNR** — peak amplitude vs full-file RMS. Real impacts blow
        the noise floor; dead / disconnected sensors don't.
      * **Saturation penalty** — clipped sensors plateau at the rail
        for many samples; we down-weight them since the integration
        will under-shoot the real peak.

    All NaN-tolerant; returns 0 on any pathological input.
    """
    try:
        t = np.asarray(t, dtype=float)
        load = np.asarray(load, dtype=float)
        a = np.asarray(accel, dtype=float)
        if len(t) < 8 or len(t) != len(load) or len(t) != len(a):
            return 0.0
        finite = np.isfinite(load) & np.isfinite(a) & np.isfinite(t)
        if finite.sum() < 8:
            return 0.0
        t = t[finite]; load = load[finite]; a = a[finite]
        n = len(t)

        # ── Load-event window ─────────────────────────────────────────
        # Score within the impact window only, not the full recording.
        # Whole-file noise is irrelevant for "is THIS column the impact
        # accelerometer" — what matters is what the column does
        # AROUND the moment of peak load.
        peak_load_idx = int(np.argmax(np.abs(load)))
        peak_load_amp = float(np.abs(load[peak_load_idx]))
        thresh = 0.20 * peak_load_amp
        # walk outward from peak until 50 consecutive below-threshold
        below = 0; e_idx = n - 1
        for i in range(peak_load_idx, n):
            if abs(load[i]) < thresh:
                below += 1
                if below >= 50:
                    e_idx = i - 49; break
            else: below = 0
        below = 0; s_idx = 0
        for i in range(peak_load_idx, -1, -1):
            if abs(load[i]) < thresh:
                below += 1
                if below >= 50:
                    s_idx = i + 49; break
            else: below = 0
        if e_idx <= s_idx + 4:
            return 0.0
        # Pad outward by 25 % of window length on each side so the
        # accel's peak (which can lead/lag the load slightly in real
        # impacts) is still captured.
        win_len = e_idx - s_idx
        s_idx = max(0, s_idx - win_len // 4)
        e_idx = min(n - 1, e_idx + win_len // 4)

        a_win = a[s_idx:e_idx + 1]
        t_win = t[s_idx:e_idx + 1]

        # 1) Time alignment — accel peak (centered) should sit within
        # 25 % of the load-peak time inside the event window.
        a_centered_win = a_win - a_win.mean()
        peak_a_idx_win = int(np.argmax(np.abs(a_centered_win)))
        peak_load_idx_win = peak_load_idx - s_idx
        dt = abs(float(t_win[peak_load_idx_win] - t_win[peak_a_idx_win]))
        win_dur = float(t_win[-1] - t_win[0]) or 1.0
        align_score = max(0.0, 1.0 - dt / (0.5 * win_dur))

        # 2) SNR within the event window — peak amplitude vs RMS of
        # the centered signal. A real accel sensor produces an impulse
        # well above its in-window noise; a dead sensor doesn't.
        rms = float(np.sqrt((a_centered_win ** 2).mean()))
        peak_amp = float(np.max(np.abs(a_centered_win)))
        snr = peak_amp / (rms + 1e-12)
        snr_score = max(0.0, min(1.0, (snr - 2.0) / 6.0))

        # ABSOLUTE-AMPLITUDE FLOOR — real RPLT impacts produce at least
        # ~0.5 g of acceleration at the peak (≈5 m/s² when the column is
        # already scaled). Below 0.05 in EITHER unit is sensor noise
        # regardless of how cleanly it correlates with the load. This
        # catches files where the accelerometer was disconnected or set
        # to a dead-channel input — which look "correlated" only because
        # any in-window noise happens to peak somewhere.
        if peak_amp < 0.05:
            return 0.0

        # 3) Saturation penalty — judged within the event window so
        # full-file row-count differences don't change the answer.
        global_max = peak_amp
        if global_max <= 0:
            sat_penalty = 1.0
        else:
            flat_count = int(np.sum(np.abs(a_centered_win) >= 0.99 * global_max))
            flat_frac = flat_count / len(a_centered_win)
            if flat_frac > 0.20:    # heavily saturated inside the impulse
                sat_penalty = 0.05
            elif flat_frac > 0.05:
                sat_penalty = 0.30
            else:
                sat_penalty = 1.0

        return align_score * snr_score * sat_penalty
    except Exception:
        return 0.0


def auto_pick_accel(
    table_name: str, time_col: str, load_col: str,
    accel_candidates: list[str], version: float = 0.0,
    *, min_score: float = 0.05,
) -> tuple[str, float, str]:
    """Score every accel-candidate column against the load impact and
    return the best.

    Returns ``(picked_col, score, mode)`` where ``mode`` is one of:
      * ``"sensor"``   — a real sensor column scored above ``min_score``;
                          use it directly.
      * ``"derive"``   — no column qualified; the caller should switch
                          ``rgf_unit_accel`` to ``"derive"`` so the
                          pipeline reconstructs accel from load via
                          Newton's 2nd law (a = F / M).

    Reads the full table — accel scoring needs the peak row, and stride
    sampling can miss it on impulsive recordings. For typical RPLT
    files (≤200k rows × ~10 candidate cols) the read is ~10 MB which
    DuckDB handles in milliseconds.
    """
    if not accel_candidates:
        return "", 0.0, "derive"
    qt = quote_table_identifier(table_name)
    qa_alias = ", ".join(
        f"{quote_identifier(c)} AS __a{i}"
        for i, c in enumerate(accel_candidates)
    )
    sql = (
        f"SELECT {quote_identifier(time_col)} AS __t, "
        f"{quote_identifier(load_col)} AS __l, "
        f"{qa_alias} FROM {qt} ORDER BY __t"
    )
    df = run_custom_query(sql, version=version)
    if df.empty:
        return "", 0.0, "derive"

    t   = pd.to_numeric(df["__t"], errors="coerce").to_numpy()
    ld  = pd.to_numeric(df["__l"], errors="coerce").to_numpy()
    # Adjust time scale — auto-detect from header so µs files don't
    # break alignment scoring (would otherwise treat the whole
    # recording as N µs ≈ instantaneous).
    time_scale, _ = infer_time_scale(time_col)
    t = t * time_scale

    best_col, best_score = "", 0.0
    for i, c in enumerate(accel_candidates):
        a = pd.to_numeric(df[f"__a{i}"], errors="coerce").to_numpy()
        s = _score_accel_signal(ld, a, t)
        if s > best_score:
            best_col, best_score = c, s

    if best_score >= min_score:
        return best_col, best_score, "sensor"
    return (best_col or accel_candidates[0]), best_score, "derive"


def infer_accel_is_mps2(col_name: str) -> bool:
    """True if the accel column is already in m/s² (i.e. pre-scaled by
    the acquisition software and we should NOT multiply by g again).

    Matches ``Acceleration scaled 1``, ``Accel (m/s2)``, ``a_mps2``, etc.
    """
    low = col_name.lower()
    if "scaled" in low and "accel" in low:
        return True
    if re.search(r"m\s*/\s*s\s*[²2]", low):
        return True
    if "mps2" in low or "mps²" in low:
        return True
    return False

# ── Constants ────────────────────────────────────────────────────────────────
DEFAULT_SMOOTHING_WINDOW = 120
DEFAULT_SMOOTHING_TYPE = "linear"
DEFAULT_UPM_MASS = 12_000.0
DEFAULT_UPM_STIFFNESS = 1_397_000.0

COL_TIME = "Time (s)"
COL_LOAD = "Load (kN)"
COL_ACCEL = "Scaled (m/s2)"
COL_VELOCITY = "Velocity (m/s)"
COL_DISP = "Disp (m)"
COL_SMOOTHED = "Scaled (m/s2) Smoothed"
COL_FMA = "Fma (kN)"
COL_FKX = "Fkx (kN)"
COL_TOTAL_FORCE = "Total Force (kN)"


# ── Column utilities ─────────────────────────────────────────────────────────
def pick_column(cols: list[str], candidates: list[str]) -> str | None:
    """Find first column whose lowercase name matches a candidate (exact then substring)."""
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    for cand in candidates:
        for c in cols:
            if cand.lower() in c.lower():
                return c
    return cols[0] if cols else None


def col_index(items: list[str], target: str | None) -> int:
    """Safe index lookup with fallback to 0."""
    if target in items:
        return items.index(target)
    return 0


# ── Session state for processing params ──────────────────────────────────────
def _parse_number(val, default: float) -> float:
    """Parse ``"12,000"`` / ``12000`` / ``"1,397,000.0"`` → float.

    Settings → Processing Defaults stores mass / stiffness as human-
    readable comma-separated strings; the pipeline needs raw floats.
    Falls back to ``default`` on parse errors.
    """
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def get_params() -> dict:
    """Read processing params from session state, with defaults.

    Priority for each value:
      1. In-view widget state (``rplt_*`` — set by Standard / UPM views)
      2. Settings → Processing Defaults (``settings_*``)
      3. Hard-coded default

    This lets the Settings page act as the global baseline while still
    letting the user tweak mass / stiffness per-view on the Standard
    Analysis processing toolbar.
    """
    ss = st.session_state

    # Smoothing: inline widget > Settings dropdown (string "Enabled by default") > default
    smooth_setting = ss.get("settings_smoothing_on", "Enabled by default")
    smooth_default = smooth_setting.startswith("Enabled") if isinstance(smooth_setting, str) else True
    apply_smoothing = ss.get("rplt_smoothing", smooth_default)

    smoothing_window = int(_parse_number(
        ss.get("rplt_smoothing_window",
               ss.get("settings_smoothing_window", DEFAULT_SMOOTHING_WINDOW)),
        DEFAULT_SMOOTHING_WINDOW,
    ))
    smoothing_type = ss.get(
        "rplt_smoothing_type",
        ss.get("settings_smoothing_weight", DEFAULT_SMOOTHING_TYPE),
    )
    upm_mass = _parse_number(
        ss.get("rplt_upm_mass", ss.get("settings_upm_mass", DEFAULT_UPM_MASS)),
        DEFAULT_UPM_MASS,
    )
    upm_stiffness = _parse_number(
        ss.get("rplt_upm_stiffness", ss.get("settings_upm_stiffness", DEFAULT_UPM_STIFFNESS)),
        DEFAULT_UPM_STIFFNESS,
    )
    return {
        "apply_smoothing":  apply_smoothing,
        "smoothing_window": smoothing_window,
        "smoothing_type":   smoothing_type,
        "upm_mass":         upm_mass,
        "upm_stiffness":    upm_stiffness,
    }


def _set(key: str, val) -> None:
    st.session_state[f"rplt_{key}"] = val


# ── Shared processing controls widget ────────────────────────────────────────
def render_controls(cols: list[str], time_col, accel_col, load_col, key_prefix: str = "p"):
    """Compact inline parameter row. Returns (time_col, accel_col, load_col, params).

    The column pickers bind to the SHARED ``rgf_map_*`` session-state
    keys — same keys used by Import Data's Data Setup panel. Picking a
    column here updates it there (and everywhere else), and vice-versa.
    Mass / stiffness / smoothing stay per-view so the user can tweak
    them independently per analysis.
    """
    ss = st.session_state
    # Seed the shared keys with the caller's suggestions (auto-pick
    # results) on the FIRST call per session. Once set, Streamlit's
    # selectbox state wins. Also snap any stale value that's no longer
    # in the active table's column set back to a legal option so the
    # selectbox doesn't throw.
    ss.setdefault("rgf_map_time",  time_col or cols[0])
    ss.setdefault("rgf_map_accel", accel_col or cols[0])
    ss.setdefault("rgf_map_load",  load_col or cols[0])
    if ss["rgf_map_time"]  not in cols: ss["rgf_map_time"]  = time_col or cols[0]
    if ss["rgf_map_accel"] not in cols: ss["rgf_map_accel"] = accel_col or cols[0]
    if ss["rgf_map_load"]  not in cols: ss["rgf_map_load"]  = load_col or cols[0]

    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1.2, 1.2, 1.2, 0.7, 0.9, 0.9, 1.0, 1.0])
    with c1:
        time_col = st.selectbox("Time",  cols, key="rgf_map_time")
    with c2:
        accel_col = st.selectbox("Accel", cols, key="rgf_map_accel")
    with c3:
        load_col = st.selectbox("Load",  cols, key="rgf_map_load")
    with c4:
        smooth = st.checkbox(
            "Smooth",
            value=get_params()["apply_smoothing"],
            key=f"{key_prefix}_smooth",
        )
        _set("smoothing", smooth)
    with c5:
        smooth_window = st.number_input(
            "Window",
            min_value=2,
            max_value=10_000,
            value=int(get_params()["smoothing_window"]),
            step=1,
            key=f"{key_prefix}_window",
        )
        _set("smoothing_window", int(smooth_window))
    with c6:
        smooth_options = ["linear", "exponential", "uniform"]
        current_smoothing = get_params()["smoothing_type"]
        smooth_index = smooth_options.index(current_smoothing) if current_smoothing in smooth_options else 0
        smooth_type = st.selectbox(
            "Weight",
            smooth_options,
            index=smooth_index,
            key=f"{key_prefix}_smoothing_type",
        )
        _set("smoothing_type", smooth_type)
    with c7:
        mass = st.number_input("Mass (kg)", value=get_params()["upm_mass"],
                               min_value=0.1, max_value=1e8, format="%.0f", key=f"{key_prefix}_mass")
        _set("upm_mass", mass)
    with c8:
        stiff = st.number_input(
            "k (N/m)",
            value=get_params()["upm_stiffness"],
            min_value=0.1,
            max_value=1e12,
            format="%.0f",
            key=f"{key_prefix}_stiff",
        )
        _set("upm_stiffness", stiff)

    params = {
        "apply_smoothing": smooth,
        "smoothing_window": int(smooth_window),
        "smoothing_type": smooth_type,
        "upm_mass": mass,
        "upm_stiffness": stiff,
    }
    return time_col, accel_col, load_col, params


# ── Run compute with spinner + validation ────────────────────────────────────
def run_processing(table_name: str, version: float,
                   time_col: str, accel_col: str, load_col: str,
                   params: dict) -> pd.DataFrame | None:
    """Run compute() with spinner. Returns DataFrame or None on error."""
    qt = quote_table_identifier(table_name)
    raw_sql = (
        "SELECT "
        f"{quote_identifier(time_col)} AS __time, "
        f"{quote_identifier(accel_col)} AS __accel, "
        f"{quote_identifier(load_col)} AS __load "
        f"FROM {qt} ORDER BY __time"
    )
    raw_df = run_custom_query(raw_sql, version=version)

    if raw_df.empty or len(raw_df) < 2:
        st.warning("Not enough data to process.")
        return None

    t = pd.to_numeric(raw_df["__time"], errors="coerce")
    a = pd.to_numeric(raw_df["__accel"], errors="coerce")
    l = pd.to_numeric(raw_df["__load"], errors="coerce")
    # When the user is going to derive accel from load (a = F/M), we
    # don't need a valid accel column — skip it in the validity mask so
    # we don't throw away every row just because accel is NaN there.
    _ss_derive = st.session_state.get("rgf_unit_accel") == "derive"
    if _ss_derive:
        valid = t.notna() & l.notna()
    else:
        valid = t.notna() & a.notna() & l.notna()
    if not valid.any():
        st.error("Selected columns are not numeric enough for processing.")
        return None
    t = t[valid]
    a = a[valid]
    l = l[valid]
    if len(t) < 2:
        st.warning("Need at least 2 valid numeric samples after cleaning.")
        return None

    # ── Unit correction ─────────────────────────────────────────────────
    # Priority: explicit user override from the Import Data → Data Units
    # panel, then header-based auto-detect, then "as-is". Every override
    # key defaults to ``"auto"`` so existing behaviour is preserved.
    ss = st.session_state
    G_CONST = 9.81
    _TIME_UNITS = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9}
    _ACCEL_MODES = {"raw_g", "g", "mps2"}
    _LOAD_UNITS = {"kN": 1.0, "N": 1e-3, "lbf": 0.00444822}

    # 1) Time
    t_override = ss.get("rgf_unit_time", "auto")
    if t_override in _TIME_UNITS:
        time_scale, time_unit = _TIME_UNITS[t_override], t_override
    else:
        time_scale, time_unit = infer_time_scale(time_col)
    if time_scale != 1.0:
        t = t * time_scale

    # 3) Load (resolved first; derive-mode for accel depends on load)
    l_override = ss.get("rgf_unit_load", "auto")
    load_scale = _LOAD_UNITS.get(l_override, 1.0)
    if load_scale != 1.0:
        l = l * load_scale

    # 2) Acceleration mode + 4) Time-window trim
    # Time trim is applied AFTER unit correction (so user-picked seconds
    # match what the pipeline sees) but BEFORE compute() so integration
    # only sees the trimmed window. Order:
    #   manual range → user-picked [start, end] in seconds
    #   auto         → event-window detection on the load signal
    #   off          → no trim, except for derive-from-Load mode which
    #                  always auto-crops (otherwise integration of
    #                  load-derived accel over the long quiet tail
    #                  blows up).
    a_override = ss.get("rgf_unit_accel", "auto")
    derive_accel_from_load = (a_override == "derive")
    trim_mode = ss.get("rgf_trim_mode", "off")

    # Compute (s_idx, e_idx) for the trim, in indices of the (already
    # unit-converted) ``t`` series.
    s_idx, e_idx = 0, len(t) - 1
    cropped = False
    if trim_mode == "manual":
        ts = float(ss.get("rgf_trim_start_s", 0.0))
        te = float(ss.get("rgf_trim_end_s",   0.0))
        if te > ts:
            t_arr = t.to_numpy()
            mask = (t_arr >= ts) & (t_arr <= te)
            if mask.any():
                where = np.where(mask)[0]
                s_idx, e_idx = int(where[0]), int(where[-1])
                cropped = s_idx > 0 or e_idx < len(t) - 1
    elif trim_mode == "auto" or (derive_accel_from_load and trim_mode == "off"):
        from lib.charts.helpers import detect_event_window
        l_arr = l.to_numpy()
        s_idx, e_idx = detect_event_window(
            l_arr, threshold_pct=0.20, contiguous_run=50,
        )
        cropped = s_idx > 0 or e_idx < len(l) - 1

    if cropped:
        t = t.iloc[s_idx:e_idx + 1].reset_index(drop=True)
        a = a.iloc[s_idx:e_idx + 1].reset_index(drop=True)
        l = l.iloc[s_idx:e_idx + 1].reset_index(drop=True)
        # Re-zero the time origin at the window start so charts read 0
        # at the start of the analysis window (RPLT convention).
        t = t - t.iloc[0]

    # Acceleration mode resolution
    if derive_accel_from_load:
        # Newton's 2nd law — a(t) = F(t) / M. Used when the file's
        # accelerometer is unreliable but the load channel is clean.
        mass = float(params.get("upm_mass") or DEFAULT_UPM_MASS)
        if mass <= 0:
            mass = DEFAULT_UPM_MASS
        a_for_compute = (l.to_numpy() * 1000.0 / mass) / G_CONST
        # Derived accel has NO sensor DC bias — the (already applied)
        # event-window crop discarded any baseline offset. Flag as
        # ±1g already centered so compute skips auto_zero_mean (which
        # would otherwise subtract the mean of the impulse itself and
        # flatten the peak by ~50%).
        accel_mps2 = False
        accel_already_g = True
    elif a_override in _ACCEL_MODES:
        accel_mps2 = (a_override == "mps2")
        accel_already_g = (a_override == "g")
        a_for_compute = a / G_CONST if accel_mps2 else a
    else:
        accel_mps2 = infer_accel_is_mps2(accel_col)
        accel_already_g = False
        a_for_compute = a / G_CONST if accel_mps2 else a

    with st.spinner("Processing..."):
        try:
            result = compute(
                time=tuple(t.tolist()),
                accel_raw=tuple(a_for_compute.tolist()),
                # When accel is explicitly "±1g (already centered)" skip
                # auto-zero-mean so the pipeline just multiplies by g.
                use_auto_zero_mean=not accel_already_g,
                accel_offset=0.0,
                accel_sens=1.0,
                # Drift-fix assumes the rigid body returns to rest at the
                # end of the recording. True for full-length acquisitions;
                # false whenever we've cropped to a tight impulse window
                # (derive-mode or user-trim), since forcing v_end=0 over
                # a 14ms window flattens the velocity peak by ~50%.
                drift_fix_velocity=not (derive_accel_from_load or cropped),
                load_input="original",
                load_original=tuple(l.tolist()),
                apply_smoothing=params["apply_smoothing"],
                smoothing_window=params["smoothing_window"],
                smoothing_type=params["smoothing_type"],
                upm_mass=params["upm_mass"],
                upm_stiffness=params["upm_stiffness"],
            )
        except Exception as exc:
            st.error(f"Processing failed: {exc}")
            return None

    if result.empty:
        st.warning("Processing returned no data.")
        return None

    return result
