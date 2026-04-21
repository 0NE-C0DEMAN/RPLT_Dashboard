"""RPLT processing engine — ported from Judy's team's Jupyter notebooks.

This is the EXACT same computation pipeline as RPLTCodeLast.ipynb and
RPLT_Fully_Integrated.ipynb, exposed as a clean module. The compute()
function is the single entry point that takes raw (Time, Acceleration, Load)
and produces all derived columns.

Processing steps:
  1. Raw acceleration → zero-mean (or manual offset/sens calibration)
  2. Scaled (±1g) → Scaled (m/s²)
  3. Integrate acceleration → Velocity (with linear drift removal)
  4. Integrate velocity → Displacement
  5. Load: from calibration formula (a*x + b) or original LOAD column
  6. Optional: weighted smoothing of acceleration
  7. Optional: UPM force analysis (Fma = m*a, Fkx = k*x, Total = Fma + Fkx)
"""

from __future__ import annotations

from typing import Literal, Tuple

import numpy as np
import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Internal helpers (exact ports from the notebooks)
# ---------------------------------------------------------------------------
def _ensure_increasing_time(
    t: np.ndarray, *arrays: np.ndarray
) -> Tuple[np.ndarray, ...]:
    """Sort by time if not monotonically increasing."""
    if np.any(np.diff(t) <= 0):
        idx = np.argsort(t)
        return (t[idx],) + tuple(arr[idx] for arr in arrays)
    return (t,) + arrays


def _cumtrapz_same_length(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Cumulative trapezoidal integration, same output length as input.
    First element is 0.0 (initial condition).
    """
    n = len(y)
    if n < 2:
        return np.zeros_like(y, dtype=float)
    dx = np.diff(x)
    avg = 0.5 * (y[1:] + y[:-1])
    out = np.empty(n, dtype=float)
    out[0] = 0.0
    out[1:] = np.cumsum(avg * dx)
    return out


def _remove_linear_drift(vec: np.ndarray) -> np.ndarray:
    """Remove linear drift — subtracts a line from start (0) to end value.

    Physical assumption: the pile/foundation returns to rest after impact,
    so final velocity should be ~0 m/s.
    """
    if len(vec) < 2:
        return vec
    trend = np.linspace(0.0, vec[-1], len(vec))
    return vec - trend


def apply_weighted_smoothing(
    data: np.ndarray,
    window: int = 120,
    weight_type: Literal["linear", "exponential", "uniform"] = "linear",
) -> np.ndarray:
    """Apply weighted moving average smoothing (John's method).

    Weight types:
      linear      — np.linspace(1, 2, window)  — recent values weighted more
      exponential — np.geomspace(1, 10, window) — sharper emphasis on recent
      uniform     — np.ones(window)             — simple moving average
    """
    if window < 2 or len(data) < window:
        return data.copy()

    if weight_type == "linear":
        weights = np.linspace(1, 2, window)
    elif weight_type == "exponential":
        weights = np.geomspace(1, 10, window)
    elif weight_type == "uniform":
        weights = np.ones(window)
    else:
        raise ValueError(f"Unknown weight_type: {weight_type}")

    weights = weights / weights.sum()
    return np.convolve(data, weights, mode="same")


# ---------------------------------------------------------------------------
# Main compute function
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Processing RPLT data...", max_entries=16)
def compute(
    time: tuple,
    accel_raw: tuple,
    *,
    use_auto_zero_mean: bool = True,
    accel_offset: float = 0.0,
    accel_sens: float = 1.0,
    g_const: float = 9.81,
    drift_fix_velocity: bool = True,
    load_a: float = 754.717,
    load_b: float = -0.26717,
    load_input: str = "original",
    load_original: tuple | None = None,
    apply_smoothing: bool = False,
    smoothing_window: int = 120,
    smoothing_type: str = "linear",
    upm_mass: float | None = None,
    upm_stiffness: float | None = None,
) -> pd.DataFrame:
    """Run the full RPLT processing pipeline.

    All array arguments are tuples (for Streamlit cache hashability).
    Returns a DataFrame with all computed columns.
    """
    t = np.asarray(time, dtype=float)
    raw = np.asarray(accel_raw, dtype=float)

    if t.size != raw.size:
        raise ValueError("time and accel_raw must have the same length.")
    if t.size < 2:
        raise ValueError("Need at least 2 samples to integrate.")

    t, raw = _ensure_increasing_time(t, raw)

    # Raw → g
    if use_auto_zero_mean:
        scaled_g = raw - np.nanmean(raw)
    else:
        scaled_g = (raw - accel_offset) / accel_sens

    # g → m/s²
    a_mps2 = scaled_g * g_const

    # Smoothing (optional)
    if apply_smoothing and smoothing_window >= 2:
        a_mps2_smoothed = apply_weighted_smoothing(
            a_mps2, smoothing_window, smoothing_type
        )
    else:
        a_mps2_smoothed = None

    # Integrate acceleration → velocity
    v = _cumtrapz_same_length(a_mps2, t)
    if drift_fix_velocity:
        v = _remove_linear_drift(v)

    # Integrate velocity → displacement
    disp = _cumtrapz_same_length(v, t)

    # Load
    if load_input == "original" and load_original is not None:
        load = np.asarray(load_original, dtype=float)
        _, load = _ensure_increasing_time(t, load)
    elif load_input == "raw":
        load = load_a * raw + load_b
    elif load_input == "scaled_g":
        load = load_a * scaled_g + load_b
    elif load_input == "scaled_mps2":
        load = load_a * a_mps2 + load_b
    else:
        load = load_a * raw + load_b

    # Build base result
    result = pd.DataFrame({
        "Time (s)": t,
        "Acceleration raw": raw,
        "Load (kN)": load,
        "Scaled (+/-1g)": scaled_g,
        "Scaled (m/s2)": a_mps2,
        "Velocity (m/s)": v,
        "Disp (m)": disp,
    })

    # Smoothed acceleration (if requested)
    if a_mps2_smoothed is not None:
        result["Scaled (m/s2) Smoothed"] = a_mps2_smoothed

    # UPM force analysis (if params provided)
    if upm_mass is not None and upm_stiffness is not None:
        accel_for_force = (
            a_mps2_smoothed if a_mps2_smoothed is not None else a_mps2
        )
        fma = upm_mass * accel_for_force
        fkx = upm_stiffness * disp
        result["Fma (N)"] = fma
        result["Fkx (N)"] = fkx
        result["Total Force (N)"] = fma + fkx
        result["Fma (kN)"] = fma / 1000.0
        result["Fkx (kN)"] = fkx / 1000.0
        result["Total Force (kN)"] = (fma + fkx) / 1000.0

    return result
