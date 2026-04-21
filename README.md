# RPLT Dashboard

Streamlit app for Rapid Plate Load Test (RPLT) sensor data. Reads CSV / XLSX / TSV / TXT / Parquet, runs the client's processing pipeline in-process (DuckDB + NumPy + SciPy), renders the 9-view UI from the reference design mock as vanilla-JS Canvas charts inside `st.components.v1.html` iframes.

Live demo: <https://rpltdashboard.streamlit.app>

---

## Repo layout

```
.
├── app.py                         SPA shell — sidebar, JS bridge, view router
├── assets/rgf.css                 {TOKEN}-interpolated stylesheet
├── lib/
│   ├── tokens.py                  Palette, radii, sidebar widths
│   ├── theme.py                   CSS loader (@cache_resource, mtime-busted)
│   ├── icons.py                   SVG path registry (35 Feather-style icons)
│   ├── components.py              page_header, badge, empty_state
│   ├── db.py                      DuckDB singleton + identifier quoting
│   ├── cache.py                   table_version + process-level _registered set
│   ├── ingest.py                  File → Parquet → DuckDB view
│   ├── queries.py                 Cached SQL helpers (column_names, head)
│   ├── engine.py                  compute() — the RPLT math kernel
│   ├── processing.py              run_processing() — unit correction + compute bridge
│   ├── cycles.py                  Event-boundary cycle detection
│   ├── state.py                   session_state wrappers (active table, imports)
│   ├── sources/manual.py          Streamlit file_uploader adapter
│   └── charts/
│       ├── canvas.py              chart_panel / series / series_xy + LTTB
│       └── helpers.py             detect_event_window, find_unloading_point
├── views/
│   ├── dashboard.py               KPIs + 4 charts + cycle table
│   ├── import_data.py             Upload + Data Setup wizard + file list + preview
│   ├── standard_analysis.py       6-panel synchronized analysis
│   ├── upm_analysis.py            Fma / Fkx decomposition
│   ├── cycle_analysis.py          Per-cycle drilldown + overlay
│   ├── chart_builder.py           Ad-hoc Line/Scatter/Area/Bar/Histogram/Box
│   ├── report_builder.py          Section-toggled PDF report
│   ├── raw_sample.py              Search / filter / paginate / CSV export
│   └── settings.py                Processing defaults (only what drives pipeline)
├── demo/
│   ├── RPLTResults_demo.xlsx      LOAD DEMO dataset (6,315 samples)
│   └── sourceGraph_sample.txt     15k-row decimated acquisition sample
├── reference/                     Dev-only, not shipped to runtime:
│   ├── RPLTCodeLast.ipynb         Client's original notebook
│   ├── RPLT_Fully_Integrated.ipynb
│   └── design/                    Reference design mock (JSX + static HTML)
├── Dockerfile                     Cloud Run-friendly (listens on $PORT)
├── .dockerignore
├── cloudbuild.yaml                CI/CD for Cloud Build
├── DEPLOYMENT.md                  GCP runbook (Cloud Run)
├── requirements.txt               streamlit + duckdb + pyarrow + pandas + numpy + scipy + lttb + openpyxl
├── runtime.txt                    python-3.11
└── .streamlit/config.toml         Theme + upload size (2 GB)
```

`data/` is created at runtime under the CWD and holds `uploads/`, `parquet/`, `cache/`. Never committed.

---

## Data flow

```
 upload widget (views/import_data.py)
   ↓  stream_uploaded_to_disk
 data/uploads/<session_id>/<file>
   ↓  convert_to_parquet  (DuckDB COPY for CSV/TSV/TXT, pandas for XLSX)
 data/parquet/<session_id>/<base>.parquet
   ↓  register_parquet  (CREATE VIEW tblname AS SELECT * FROM read_parquet('...'))
 DuckDB view                            ← queried by every downstream view
   ↓  save_metadata
 data/cache/<tblname>.json              ← TableInfo record (rows, cols, paths)

 user picks Time / Accel / Load columns + units  (views/import_data.py::_render_data_setup)
   ↓  session_state: rgf_map_*, rgf_unit_*
 run_processing(table, version, time_col, accel_col, load_col, params)
   ↓  SELECT __time, __accel, __load FROM tblname ORDER BY __time
   ↓  pd.to_numeric + NaN filter
   ↓  unit correction   (time scale, accel mode, load scale, or derive a = F/M)
   ↓  compute()         (zero-mean → ×g → cumtrapz → drift-fix → cumtrapz → UPM)
 DataFrame with COL_TIME, COL_LOAD, COL_ACCEL, COL_VELOCITY, COL_DISP, COL_SMOOTHED, COL_FMA, COL_FKX
   ↓
 chart_panel(series_list, x_data)  →  iframe (vanilla JS + Canvas)
```

`compute()` is `@st.cache_data`-memoised on its (hashable) tuple arguments, so re-renders with unchanged inputs are free.

---

## Quick start

```bash
# Python 3.10+ (developed on 3.11)
pip install -r requirements.txt
streamlit run app.py
```

<http://localhost:8501> → Import Data → **LOAD DEMO** → Standard Analysis.

### Docker (same image as prod)

```bash
docker build -t rplt .
docker run -p 8080:8080 -e PORT=8080 rplt
```

### Deploy to Google Cloud Run

See [`DEPLOYMENT.md`](DEPLOYMENT.md). Two `gcloud` commands after one-time GCP setup.

---

## Processing pipeline — `lib/engine.py::compute()`

Exact port of the client's Jupyter notebook (`reference/RPLTCodeLast.ipynb`).

1. **Time monotonic-sort** — sort (t, a, l) by time if `np.any(np.diff(t) <= 0)`.
2. **Auto-zero-mean** — `scaled_g = raw - mean(raw)` (or `(raw - offset) / sens` in manual-calibration mode).
3. **g → m/s²** — `a_mps2 = scaled_g * 9.81`.
4. **Weighted smoothing (optional)** — linear / exponential / uniform window of `N` samples, `np.convolve(mode="same")`.
5. **Integrate a → v** — `cumtrapz(a, t)` with `v[0]=0`.
6. **Drift fix** — `v -= np.linspace(0, v[-1], n)` (final velocity = 0 assumption).
7. **Integrate v → x** — `cumtrapz(v, t)`.
8. **Load** — pass-through from source column (or calibration `load = a·x + b` in derived mode).
9. **UPM (if `mass` + `stiffness` provided)** — `Fma = m·a_smoothed`, `Fkx = k·x`, `Total = Fma + Fkx`.

Steps 5–7 only make physical sense when `a(t)` is the reaction-mass acceleration during an impact. For files where the accelerometer is unreliable, see *Derive-from-Load* below.

---

## Column mapping + unit semantics — `views/import_data.py::_render_data_setup`

One row per role (TIME / ACCELERATION / LOAD). Each row: column selector · unit selector · live `min · max · n` stats chip from a DuckDB aggregation cached per `(table, version, cols)`.

Session-state keys (shared across all views):

| Key | Values |
|---|---|
| `rgf_map_time` / `rgf_map_accel` / `rgf_map_load` | Column name from the active table |
| `rgf_unit_time` | `auto` / `s` / `ms` / `us` / `ns` |
| `rgf_unit_accel` | `auto` / `raw_g` / `g` / `mps2` / `derive` |
| `rgf_unit_load` | `auto` / `kN` / `N` / `lbf` |

Auto detects via header regex:

```python
infer_time_scale("Time (us)") == (1e-6, "us")
infer_accel_is_mps2("Acceleration scaled 1") == True
```

The auto-pick candidate order for Load is `["load (kn)", "load summ", "load sum", "load scaled", "load", "force", "LOAD"]` — ensures summed/scaled channels win over raw-voltage channels on multi-channel acquisition dumps.

An `AUTOPICK_VERSION` sentinel in session state re-seeds the picks when the candidate lists change, so upgrades don't strand users on stale selections.

---

## Derive-from-Load mode

For files where the accelerometer channel doesn't track the load impact (slow drift, mis-triggered, or recording a secondary event), set **Acceleration → "Derive from Load — a = F / M"**.

`run_processing()` then:

1. Crops `(t, l)` to the event window using `detect_event_window(l, threshold_pct=0.20, contiguous_run=50)` — walks outward from the load peak until 50 consecutive below-threshold samples. Handles non-zero baselines that break the first-crossing rule.
2. Re-zeros `t` at the window start.
3. Computes `a = l_kN · 1000 / upm_mass` (Newton's 2nd law).
4. Feeds to `compute()` with `use_auto_zero_mean=False` (derived signal has no DC bias) and `drift_fix_velocity=False` (forcing v_end=0 over a 14 ms window flattens the peak).

Result on the Judy txt file: peak velocity ≈ 301 mm/s, set displacement ≈ 2.8 mm, 14 ms event duration.

---

## Cycle detection — `lib/cycles.py::detect_cycles`

Event-boundary rather than peak-picking. A cycle = a contiguous run where `|load| ≥ 20 %` of the global peak load. For each run, emit:

```python
{
  "cycle_no": int,          # 1-based
  "start_idx": int, "end_idx": int,
  "peak_idx": int, "peak_load": float,
  "max_disp_m": float,      # abs max displacement in window
  "set_disp_m": float,      # displacement at end_idx (post-event "set")
  "peak_vel":  float,
  "duration_s": float,
}
```

Multi-impact tests split into real cycles instead of being chopped into sub-peaks of one ringing impulse.

---

## Chart engine — `lib/charts/canvas.py`

Every chart is a self-contained iframe emitted by `chart_panel(...)`. The payload contains `series_list` + `x_data` serialised to JSON; the iframe draws on a `<canvas>` with vanilla JS (no Plotly / ECharts).

Key behaviours:

- **LTTB downsampling**. `_joint_downsample_indices(x, series_list, n=1500)` builds a composite envelope (`max_i |y_i|`) and runs `lttb.downsample` against it. Same indices are applied to the x-array and every y-series, so multi-series charts stay locked together at peaks. Uniform stride was silently dropping 2200 kN peaks at 166k samples; LTTB preserves them.
- **XY-pair mode** (`series_xy`) for non-monotonic axes (Load-vs-Disp hysteresis, phase space). `None` / `NaN` entries act as pen-up gaps.
- **Engineering x-axis ticks** — `10,000 → 10k`, `2,000,000 → 2M`, `9,800,000 → 10M`. Prevents the ugly 7-digit µs labels on long recordings.
- **Controls**: zoom/pan toolbar, fullscreen, PNG download, hover crosshair with tooltip, optional unit-toggle buttons (`mm` / `µm`), optional annotations (peak dots, v=0 vlines).

Every panel wraps in `st.container(key=f"rgf_chart_panel_{safe_key}")` so the DOM is addressable from the JS bridge (for Export CSV, PDF Print, etc.).

---

## JS bridge — `app.py`

Single capture-phase click listener on `parent.document` (attached once via `doc.__rgfBridged` guard inside an iframe). Any HTML element with `data-nav="dashboard"`, `data-cycle="3"`, `data-cb-type="Line"` etc. gets dispatched to its matching hidden `st.button(key="__nav_dashboard")` via `.click()`. Streamlit re-runs on the websocket, no page reload.

Prefix → hidden-key mapping lives in the `ATTRS` array at the top of the bridge script. Add a row to extend.

`data-action="..."` handlers cover non-prefix one-offs: `load-demo`, `toggle-sidebar`, `cb-toggle-sql`, `cb-download`, `cb-print`, `rd-filter-toggle`, `rd-export-csv`, `settings-save`, `settings-reset`, `rb-generate-pdf`, `export-dashboard`.

---

## Requirements

See `requirements.txt`. Core stack:

| Package | Version | Purpose |
|---|---|---|
| streamlit | ≥ 1.40 | Web framework |
| duckdb | ≥ 1.1 | Query engine + Parquet reader |
| pyarrow | ≥ 18 | Parquet I/O |
| pandas | ≥ 2.2 | DataFrame ops |
| numpy | ≥ 2 | Array math |
| scipy | ≥ 1.14 | Integration / stats |
| openpyxl | ≥ 3.1 | XLSX reader |
| lttb | ≥ 0.3 | Peak-preserving downsample |

Python 3.11 target (`runtime.txt`, `Dockerfile` base). 3.10+ works.

---

## Development

```bash
# Lint
pip install pyflakes
python -m pyflakes views/ lib/ app.py

# Watch the CSS — edit assets/rgf.css, Streamlit hot-reloads via the
# mtime-keyed @cache_resource on lib/theme.py::_load_css
```

To add a new view:

1. Create `views/new_view.py` exposing `def render() -> None:`.
2. Add a row to `NAV` in `app.py` (id, label, icon name from `lib/icons.py::ICONS`).
3. Add the dispatch branch near the bottom of `app.py`.

---

## License

Proprietary — delivered to Riyadh Geotechnique & Foundations Co.
