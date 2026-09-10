"""
Corrected/imputed value estimation for SkyGuard AI - Agent 5.

Approach (as scoped): when a reading is flagged as a sensor fault
(anomaly_type in sensor_stuck/spike/drift/dropout), estimate the "true" value by
blending two independent estimators:

  1. TEMPORAL: linear trend fit on the station's own recent CLEAN history
     (last N readings, excluding the corrupted tail).
  2. SPATIAL: inverse-distance-weighted (IDW) average of current readings from
     nearby HEALTHY stations (haversine distance, capped radius).

The two estimates are blended with weights based on how much of each is
available:
  - Both available -> 15/85 temporal/spatial (see comment below for why)
  - Only temporal available (no nearby healthy stations) -> 100% temporal
  - Only spatial available (no usable history, e.g. dropout at series start) -> 100% spatial
  - Neither available -> falls back to last known-good reading

This is intentionally simple/explainable for a hackathon demo - swap in a
Kalman filter or learned imputer later without changing the calling contract.
"""

import math
from datetime import datetime

CLEAN_LOOKBACK_EXCLUDING_TAIL = 6   # how many pre-fault points to use for the trend
FAULT_TAIL_TO_EXCLUDE = 10          # assume last N points (~2.5h) may be corrupted/drifting
NEIGHBOR_RADIUS_KM = 800
MAX_NEIGHBORS = 4
TEMPORAL_WEIGHT_WHEN_BOTH = 0.15
# Tuned against real ground-truth data (agent1_ingestion/): spatial (neighbor
# IDW) substantially outperforms temporal (self-trend) extrapolation for this
# station network - measured MAE was ~5-6x lower for spatial across all three
# fields (see correction_accuracy.py). This makes sense here: stations are
# close enough (~100-250km, shared coastal climate) for strong spatial
# correlation, while several fault types (esp. drift) persist for very long
# windows, which contaminates the "clean" lookback a self-trend fit relies on.
# Temporal is kept as a real (non-zero) contributor rather than dropped
# entirely, since it's still a genuine independent signal and the weighting
# should generalize better than a pure-spatial rule if the sensor network
# geometry changes (sparser network -> temporal matters more).

# Sanity bounds: max plausible change from the last trusted reading over one
# correction step. If a temporal extrapolation blows past this, we don't trust
# it (protects against a contaminated fit, e.g. slow drift bleeding into the
# "clean" window) and fall back to the spatial estimate instead.
MAX_PLAUSIBLE_DELTA = {"temperature_c": 8.0, "pressure_hpa": 12.0, "humidity_pct": 25.0}

FIELDS = ["temperature_c", "pressure_hpa", "humidity_pct"]


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _temporal_estimate(station_id, histories):
    """Fit a simple linear trend on the clean part of this station's own history
    and extrapolate one step forward. Returns dict|None."""
    series = histories.get(station_id, [])
    if len(series) <= FAULT_TAIL_TO_EXCLUDE + 2:
        return None

    clean_tail = series[-(FAULT_TAIL_TO_EXCLUDE + CLEAN_LOOKBACK_EXCLUDING_TAIL):-FAULT_TAIL_TO_EXCLUDE]
    if len(clean_tail) < 3:
        return None

    t0 = clean_tail[0]["timestamp"]
    xs = [(p["timestamp"] - t0).total_seconds() for p in clean_tail]
    target_t = (series[-1]["timestamp"] - t0).total_seconds()

    result = {}
    for field in FIELDS:
        ys = [p[field] for p in clean_tail]
        # basic least-squares slope/intercept
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        denom = sum((x - mean_x) ** 2 for x in xs)
        if denom == 0:
            slope = 0.0
        else:
            slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
        intercept = mean_y - slope * mean_x
        result[field] = round(intercept + slope * target_t, 2)

    # Sanity check against the last trusted (pre-tail) reading - guards against
    # a still-contaminated fit window producing an implausible extrapolation.
    last_clean = clean_tail[-1]
    for field in FIELDS:
        if abs(result[field] - last_clean[field]) > MAX_PLAUSIBLE_DELTA[field]:
            return None
    return result


def _spatial_estimate(station_id, current_snapshot, meta, healthy_station_ids):
    """IDW average of current readings from nearby healthy stations."""
    if station_id not in meta:
        return None
    lat0, lon0 = meta[station_id]["latitude"], meta[station_id]["longitude"]

    candidates = []
    for other_id in healthy_station_ids:
        if other_id == station_id or other_id not in meta or other_id not in current_snapshot:
            continue
        d = _haversine_km(lat0, lon0, meta[other_id]["latitude"], meta[other_id]["longitude"])
        if d <= NEIGHBOR_RADIUS_KM:
            candidates.append((d, other_id))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    candidates = candidates[:MAX_NEIGHBORS]

    weights = [1.0 / max(d, 1.0) ** 2 for d, _ in candidates]
    total_w = sum(weights)

    result = {}
    for field in FIELDS:
        result[field] = round(
            sum(w * current_snapshot[oid][field] for w, (_, oid) in zip(weights, candidates)) / total_w, 2
        )
    return result


def estimate_corrected_value(station_id, histories, current_snapshot, meta, healthy_station_ids=None):
    """
    Main entry point. Returns {"temperature_c":.., "pressure_hpa":.., "humidity_pct":..}
    or None if no estimate could be made at all.
    """
    if healthy_station_ids is None:
        # caller can pass explicit health status; default: treat every OTHER station
        # as a usable neighbor (good enough for the demo's IDW purpose)
        healthy_station_ids = [sid for sid in meta if sid != station_id]

    temporal = _temporal_estimate(station_id, histories)
    spatial = _spatial_estimate(station_id, current_snapshot, meta, healthy_station_ids)

    if temporal and spatial:
        w = TEMPORAL_WEIGHT_WHEN_BOTH
        return {f: round(w * temporal[f] + (1 - w) * spatial[f], 2) for f in FIELDS}
    if temporal:
        return temporal
    if spatial:
        return spatial

    # last resort: most recent value before the corrupted tail, if any
    series = histories.get(station_id, [])
    if len(series) > FAULT_TAIL_TO_EXCLUDE:
        fallback = series[-FAULT_TAIL_TO_EXCLUDE - 1]
        return {f: fallback[f] for f in FIELDS}
    return None