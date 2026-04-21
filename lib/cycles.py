"""lib/cycles.py — RPLT cycle (impact) detection + per-cycle summaries.

Public:
    detect_cycles(df)                 — list of cycle dicts (summary + window)
    cycle_window(df, cycle_dict)      — slice df to one cycle's window

Each cycle dict looks like::

    {
        "cycle_no":    1,                  # 1-based index
        "peak_idx":    866,                # absolute index of peak |load|
        "start_idx":   766,                # inclusive window start
        "end_idx":     1066,               # exclusive window end
        "peak_load":   2219.2,             # kN
        "peak_time_s": 2.6808,             # s
        "peak_disp_m": -4.82e-6,           # m (for unit-agnostic downstream)
        "max_disp_m":  5.50e-6,            # m (max |disp| in window)
        "set_disp_m":  4.73e-6,            # m (residual disp at window end)
        "peak_vel":    0.24764,            # m/s
        "duration_s":  0.02209,            # s (window span)
    }

Downstream views (Dashboard cycle-summary table, Cycle Analysis view)
consume these dicts. Displacement values are returned in metres so each
caller can scale to mm / µm as it sees fit.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lib.processing import COL_DISP, COL_LOAD, COL_TIME, COL_VELOCITY


# Event-boundary threshold — a cycle is a contiguous run where
# |load| ≥ this fraction of the global maximum. Dropping below it marks
# the end of a cycle; rising back above starts the next one. This
# cleanly distinguishes a single impact with ringing (one contiguous
# event, one cycle) from a true multi-drop file (N contiguous events,
# N cycles) without needing a manually-tuned min-gap.
_EVENT_THRESHOLD_FRAC = 0.20


def detect_cycles(df: pd.DataFrame) -> list[dict]:
    """Return a list of cycle summary dicts for every impact in ``df``.

    Algorithm: find contiguous intervals where |load| is ≥ 20 % of the
    global max. Each interval is one cycle — its peak is the argmax of
    |load| inside that interval.

    For one-shot files (a single impact with ringing) this yields
    exactly one cycle, because the load trace stays elevated throughout
    the event. For multi-drop files it yields N, one per clean event.
    """
    if df.empty or COL_LOAD not in df.columns:
        return []

    load = df[COL_LOAD].to_numpy()
    time = df[COL_TIME].to_numpy()
    disp = df[COL_DISP].to_numpy() if COL_DISP in df.columns else np.zeros_like(load)
    vel  = df[COL_VELOCITY].to_numpy() if COL_VELOCITY in df.columns else np.zeros_like(load)

    abs_load = np.abs(load)
    peak_val = float(abs_load.max())
    if peak_val <= 0:
        return []

    # Mask of samples above the event threshold.
    threshold = peak_val * _EVENT_THRESHOLD_FRAC
    above = abs_load >= threshold

    # Find rising/falling edges of the above-threshold runs. Prepending
    # and appending 0 makes edge handling uniform (a run that starts at
    # sample 0 or ends at the last sample gets closed properly).
    edges = np.diff(above.astype(np.int8), prepend=0, append=0)
    starts = np.where(edges == 1)[0]
    ends   = np.where(edges == -1)[0]

    intervals = list(zip(starts.tolist(), ends.tolist()))
    # If nothing crossed the threshold (shouldn't happen because peak
    # is by definition above it), fall back to one cycle around the max.
    if not intervals:
        pk = int(np.argmax(abs_load))
        intervals = [(max(0, pk - 50), min(len(load), pk + 50))]

    cycles: list[dict] = []
    for n, (s, e) in enumerate(intervals, start=1):
        # The cycle's peak is the argmax of |load| inside the interval.
        pk = s + int(np.argmax(abs_load[s:e]))
        seg_time = time[s:e]
        seg_disp = disp[s:e]
        seg_vel  = vel[s:e]
        cycles.append({
            "cycle_no":    n,
            "peak_idx":    pk,
            "start_idx":   s,
            "end_idx":     e,
            "peak_load":   float(load[pk]),
            "peak_time_s": float(time[pk]),
            "peak_disp_m": float(disp[pk]),
            "max_disp_m":  float(np.max(np.abs(seg_disp))) if len(seg_disp) else 0.0,
            "set_disp_m":  float(seg_disp[-1]) if len(seg_disp) else 0.0,
            "peak_vel":    float(np.max(np.abs(seg_vel))) if len(seg_vel) else 0.0,
            "duration_s":  float(seg_time[-1] - seg_time[0]) if len(seg_time) > 1 else 0.0,
        })
    return cycles


def cycle_window(df: pd.DataFrame, cycle: dict) -> pd.DataFrame:
    """Slice ``df`` to one cycle's window. Returns a fresh view.

    Convenience for views that iterate a single cycle — lets the caller
    stay oblivious to whether it's drop #1 or #7 of a multi-event file.
    """
    return df.iloc[cycle["start_idx"]:cycle["end_idx"]].reset_index(drop=True)
