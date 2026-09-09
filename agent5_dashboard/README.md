# SkyGuard AI — Agent 5 (Correction & Alert + Dashboard)

Team **Agentic Genesis** · Smart India Hackathon 2026 · **SIH26073** (Ministry of Earth Sciences)

This is the Agent 5 deliverable: corrected-value logic + the operator-facing dashboard,
sitting at the end of the 5-agent pipeline (Ingestion → Screening → ML Detection →
Root-Cause/Explainability → **Correction & Alert + Dashboard**).

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`.

## What's in here

| File | Purpose |
|---|---|
| `schema.py` | Shared constants matching the exact record contract from Agents 1–4 (health status, severity levels, colors, ordering). |
| `mock_data.py` | Simulates 18 AWS stations across India with realistic diurnal temp/pressure/humidity, and **injects** sensor faults (stuck / spike / drift / dropout) plus one genuine weather event, so the dashboard has real material. Also emulates the Agent 2–4 scoring/explanation output. |
| `correction.py` | The corrected/imputed value estimator — see below. |
| `app.py` | The Streamlit dashboard: map, alert feed, station list, detail view. |

## Corrected-value logic (`correction.py`)

When a reading is flagged as a sensor fault (`anomaly_type` ∈ `sensor_stuck`,
`sensor_spike`, `sensor_drift`, `sensor_dropout` — **not** `genuine_event`), we estimate
the likely true value by blending two estimators:

1. **Temporal** — linear trend fit on the station's own recent *clean* history (the
   last known-good window, explicitly excluding a tail assumed to be corrupted), extrapolated
   one step forward.
2. **Spatial** — inverse-distance-weighted average of the *current* readings from nearby
   **trustworthy** stations (haversine distance, radius-capped, top-4 neighbors). Stations
   currently flagged as faulty are excluded from being used as neighbors — otherwise a
   dropout's `-999` sentinel value would poison a neighboring correction.

Blend rule: 50/50 if both are available; falls back to whichever one is available if only
one is; falls back to the last known-good reading if neither is available. A sanity clamp
rejects a temporal extrapolation that jumps implausibly far from the last trusted reading
(protects against a still-contaminated fit window, e.g. slow drift bleeding into the
"clean" lookback).

This is intentionally simple and explainable for the hackathon demo — the interface
(`estimate_corrected_value(station_id, histories, current_snapshot, meta, healthy_station_ids)`)
is stable, so a Kalman filter or learned imputer can be swapped in later without touching
the dashboard.

`genuine_event` readings are **never corrected** — the raw values are trusted since Agent 4
determined the anomaly is real weather, not a fault.

## Dashboard (`app.py`)

- **Station map** — pydeck scatter map, colored by `sensor_health_status` (green/amber/red),
  point size scaled by `alert_severity`.
- **Station list** — sortable table (worst health first) with health/severity badges.
- **Alert feed** — sorted by `alert_severity` (critical → none), each card shows
  `anomaly_type` + the plain-language `explanation.reasoning_text` from Agent 4.
- **Station detail view** — pick any station: full raw vs. corrected value comparison,
  confidence score, detection scores (spatial deviation / physical consistency / ML anomaly
  score), top contributing factors, and a 12-hour trend chart with the corrected point overlaid.
- Sidebar filters by health status and severity, plus a manual "refresh feed" button that
  regenerates a new mock tick (stand-in for a live feed poll).

## Swapping in real data

Everything reads through `mock_data.build_current_records()` and `correction.py`'s pure
functions, which both work off the exact record schema in `schema.py`. To wire in the real
Agent 1–4 output:

1. In `app.py`, replace the body of `load_records()` — instead of calling
   `build_network()` / `build_current_records()`, read your live JSON/API feed and shape it
   into a `list[dict]` following `schema.RECORD_FIELDS`, plus a `histories` dict of
   `station_id -> list[{"timestamp","temperature_c","pressure_hpa","humidity_pct"}]` for the
   trend charts and temporal correction.
2. If the upstream pipeline computes `corrected_value` itself, just pass it through — the
   `correction.py` module here becomes optional (or a fallback/sanity-check path).
3. `_station_name` is a display-only field the mock generator adds; keep it or map it from
   station metadata (city/name lookup) on the real feed.
4. For live polling, replace the manual refresh button with `st.autorefresh` (via the
   `streamlit-autorefresh` package) or a `while True` + `st.rerun()` loop hitting your API on
   an interval.

## Known simplifications (call out in the demo)

- Mock network topology (18 fixed Indian cities) — real deployment will have the actual AWS
  station grid density/spacing, which changes the spatial correction's neighbor radius tuning.
- Correction blend weights (50/50 temporal/spatial, sanity-clamp thresholds) are fixed
  constants tuned for the demo dataset — these should be validated against real historical
  AWS data before deployment, ideally per-parameter (temperature/pressure/humidity have very
  different natural variability and spatial correlation lengths).
- No persistence/database — each Streamlit run regenerates mock state; the real system
  should read the live pipeline output on each refresh.
