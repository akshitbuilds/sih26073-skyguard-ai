"""
Mock data generator for SkyGuard AI.

Simulates what Agents 1-4 would hand off to Agent 5: a network of Automatic
Weather Stations across India, each producing a time-series of
(temperature, pressure, humidity) readings with realistic diurnal patterns,
PLUS injected sensor faults (stuck / spike / drift / dropout) on a subset of
stations so the dashboard has real material to display.

Swap-out point for real integration: replace `get_live_snapshot()` /
`get_station_history()` with calls into the real Agent 1-4 pipeline output
(same record schema, see schema.py).
"""

import random
import math
from datetime import datetime, timedelta, timezone

from schema import ANOMALY_TYPES

random.seed(42)

# The 5 real AWS stations from the live dataset (agent1_ingestion/clean_dataset.csv),
# Gujarat/Saurashtra coastal region. Real lat/lon - sourced directly from the dataset,
# not placeholders.
STATIONS = [
    ("AWS_DIU", "Diu", 20.7141, 70.9822),
    ("AWS_VERAVAL", "Veraval", 20.9077, 70.3679),
    ("AWS_MAHUVA", "Mahuva", 21.0901, 71.7690),
    ("AWS_PORBANDAR", "Porbandar", 21.6422, 69.6093),
    ("AWS_BHAVNAGAR", "Bhavnagar", 21.7629, 72.1533),
]

# Fault injected per station for this demo run. None = clean.
# Dropout isn't represented live here (only 5 stations) but IS covered in the
# real correction-accuracy evaluation (see correction_accuracy.py / README),
# which measures against all 4 real fault types from the labeled dataset.
FAULT_PLAN = {
    "AWS_DIU": "sensor_stuck",
    "AWS_VERAVAL": None,
    "AWS_MAHUVA": "sensor_drift",
    "AWS_PORBANDAR": "sensor_spike",
    "AWS_BHAVNAGAR": "genuine_event",
}

HISTORY_HOURS = 12
INTERVAL_MIN = 15  # one reading every 15 minutes


def _diurnal_base(lat, hour_frac, day_of_year=260):
    """Rough physically-plausible base values by latitude + time of day."""
    # Warmer near equator, cooler at higher latitude; simple seasonal tilt for Sept.
    base_temp = 33 - (lat - 8) * 0.55
    temp = base_temp + 6 * math.sin((hour_frac - 6) / 24 * 2 * math.pi)
    pressure = 1008 + 3 * math.cos(hour_frac / 24 * 2 * math.pi) - lat * 0.02
    humidity = 65 - 15 * math.sin((hour_frac - 6) / 24 * 2 * math.pi) + lat * 0.3
    return temp, pressure, max(20, min(98, humidity))


def _gen_clean_series(lat, lon, n_points, start_time):
    series = []
    for i in range(n_points):
        t = start_time + timedelta(minutes=INTERVAL_MIN * i)
        hour_frac = t.hour + t.minute / 60
        temp, pres, hum = _diurnal_base(lat, hour_frac)
        temp += random.gauss(0, 0.3)
        pres += random.gauss(0, 0.4)
        hum += random.gauss(0, 1.5)
        series.append({"timestamp": t, "temperature_c": round(temp, 2),
                        "pressure_hpa": round(pres, 2), "humidity_pct": round(max(10, min(100, hum)), 2)})
    return series


def _inject_fault(series, fault_type):
    """Corrupt the LAST reading(s) of a clean series to simulate a fault developing now."""
    if fault_type is None:
        return series, None

    last = series[-1]
    true_val = dict(last)  # keep the "would have been" value for correction-accuracy comparisons

    if fault_type == "sensor_stuck":
        # last 4 readings frozen at one value (typical of a jammed sensor)
        frozen = dict(series[-5])
        for i in range(-4, 0):
            series[i]["temperature_c"] = frozen["temperature_c"]
            series[i]["pressure_hpa"] = frozen["pressure_hpa"]
            series[i]["humidity_pct"] = frozen["humidity_pct"]

    elif fault_type == "sensor_spike":
        last["temperature_c"] += random.choice([-1, 1]) * random.uniform(12, 18)
        last["humidity_pct"] = max(0, min(100, last["humidity_pct"] + random.choice([-1, 1]) * random.uniform(35, 50)))

    elif fault_type == "sensor_drift":
        # progressive calibration drift over last 8 readings
        for idx, i in enumerate(range(-8, 0)):
            drift = (idx + 1) * 0.9
            series[i]["pressure_hpa"] -= drift
            series[i]["temperature_c"] += drift * 0.15

    elif fault_type == "sensor_dropout":
        last["temperature_c"] = -999.0
        last["pressure_hpa"] = -999.0
        last["humidity_pct"] = -999.0

    elif fault_type == "genuine_event":
        # real, physically-consistent pressure drop + humidity rise (e.g. approaching low)
        for idx, i in enumerate(range(-6, 0)):
            drop = (idx + 1) * 1.6
            series[i]["pressure_hpa"] -= drop
            series[i]["humidity_pct"] = min(100, series[i]["humidity_pct"] + drop * 1.8)
            series[i]["temperature_c"] -= drop * 0.1

    return series, true_val


def _score_and_annotate(station_id, series, fault_type):
    """Emulate Agents 2-4 output: screening flags, ML scores, explanation, health, severity."""
    last = series[-1]
    is_fault = fault_type is not None and fault_type != "genuine_event"
    is_event = fault_type == "genuine_event"

    if fault_type is None:
        screening_flag = "pass"
        ml_score = round(random.uniform(0.02, 0.12), 3)
        recon_err = round(random.uniform(0.01, 0.08), 3)
        anomaly_type = "none"
        confidence = round(random.uniform(0.85, 0.97), 2)
        health = "green"
        severity = "none"
        top_factors = ["within_normal_range"]
        reasoning = f"{station_id} readings track its own recent trend and neighboring stations closely. No fault indicators."
    elif is_event:
        screening_flag = "physical_inconsistency"  # flagged by screening, but ML+root-cause clear it
        ml_score = round(random.uniform(0.55, 0.7), 3)
        recon_err = round(random.uniform(0.2, 0.35), 3)
        anomaly_type = "genuine_event"
        confidence = round(random.uniform(0.8, 0.93), 2)
        health = "amber"
        severity = "medium"
        top_factors = ["pressure_drop_rate", "humidity_rise_correlated", "spatially_coherent_with_neighbors"]
        reasoning = (f"{station_id} shows a coordinated pressure drop and humidity rise that is spatially "
                     f"consistent with neighboring stations — this pattern matches a genuine weather system, not a sensor fault.")
    else:
        screening_flag = "spatial_outlier" if fault_type != "sensor_stuck" else "physical_inconsistency"
        ml_score = round(random.uniform(0.72, 0.96), 3)
        recon_err = round(random.uniform(0.4, 0.9), 3)
        anomaly_type = fault_type
        confidence = round(random.uniform(0.78, 0.98), 2)
        severity_map = {
            "sensor_stuck": "medium", "sensor_spike": "high",
            "sensor_drift": "low", "sensor_dropout": "critical",
        }
        severity = severity_map.get(fault_type, "medium")
        health = "red" if severity in ("high", "critical") else "amber"
        factor_map = {
            "sensor_stuck": ["zero_variance_last_4_readings", "no_spatial_correlation"],
            "sensor_spike": ["single_point_deviation", "physically_implausible_rate_of_change"],
            "sensor_drift": ["gradual_divergence_from_neighbors", "monotonic_bias_trend"],
            "sensor_dropout": ["sentinel_value_detected", "missing_data_pattern"],
        }
        top_factors = factor_map.get(fault_type, ["anomaly_detected"])
        reasoning_map = {
            "sensor_stuck": f"{station_id} has reported an identical value for 4 consecutive readings — statistically implausible for live weather sensors, indicating the sensor is frozen.",
            "sensor_spike": f"{station_id} shows a sudden, physically implausible jump not seen at any neighboring station in the same window — consistent with a transient sensor glitch.",
            "sensor_drift": f"{station_id} readings are steadily diverging from both its own historical baseline and neighboring stations, consistent with slow calibration drift.",
            "sensor_dropout": f"{station_id} is reporting sentinel/invalid values, indicating a dropout or communication failure at the sensor.",
        }
        reasoning = reasoning_map.get(fault_type, f"{station_id} flagged as anomalous.")

    return {
        "spatial_deviation_score": round(random.uniform(0.1, 0.95) if (is_fault or is_event) else random.uniform(0.0, 0.15), 3),
        "physical_consistency_score": round(random.uniform(0.05, 0.5) if is_fault else random.uniform(0.7, 0.99), 3),
        "screening_flag": screening_flag,
        "ml_anomaly_score": ml_score,
        "reconstruction_error": recon_err,
        "anomaly_type": anomaly_type,
        "confidence_score": confidence,
        "explanation": {"top_factors": top_factors, "reasoning_text": reasoning},
        "sensor_health_status": health,
        "alert_severity": severity,
    }


def build_network(now=None):
    """
    Build the full mock network: history per station + the current (latest) record
    for each, fully annotated as Agent 5 would receive it.
    Returns: (histories: dict[station_id -> list[dict]], true_values: dict[station_id -> dict|None])
    """
    now = now or datetime.now(timezone.utc)
    n_points = int(HISTORY_HOURS * 60 / INTERVAL_MIN)
    start_time = now - timedelta(minutes=INTERVAL_MIN * (n_points - 1))

    histories = {}
    true_values = {}
    for station_id, city, lat, lon in STATIONS:
        series = _gen_clean_series(lat, lon, n_points, start_time)
        fault_type = FAULT_PLAN.get(station_id)
        series, true_val = _inject_fault(series, fault_type)
        histories[station_id] = series
        true_values[station_id] = true_val

    return histories, true_values


def get_station_meta():
    return {sid: {"name": city, "latitude": lat, "longitude": lon} for sid, city, lat, lon in STATIONS}


def build_current_records(histories, correction_fn):
    """
    Given per-station histories, produce the final Agent-5-input-shaped record
    for each station's LATEST reading, including corrected_value via correction_fn.
    correction_fn(station_id, histories, current_snapshot, meta, trustworthy_ids) -> dict|None
    """
    meta = get_station_meta()
    # current snapshot = latest reading per station, used for spatial correction
    current_snapshot = {sid: hist[-1] for sid, hist in histories.items()}

    # Pass 1: annotate every station so we know which ones are trustworthy
    # enough to serve as spatial neighbors for correcting OTHER stations.
    all_annotations = {sid: _score_and_annotate(sid, hist, FAULT_PLAN.get(sid))
                        for sid, hist in histories.items()}
    trustworthy_ids = [sid for sid, ann in all_annotations.items()
                        if ann["anomaly_type"] in ("none", "genuine_event")]

    records = []
    for sid, hist in histories.items():
        last = hist[-1]
        annotations = all_annotations[sid]

        needs_correction = annotations["anomaly_type"] not in ("none", "genuine_event")
        corrected_value = None
        if needs_correction:
            corrected_value = correction_fn(sid, histories, current_snapshot, meta, trustworthy_ids)

        record = {
            "station_id": sid,
            "timestamp": last["timestamp"].isoformat(),
            "latitude": meta[sid]["latitude"],
            "longitude": meta[sid]["longitude"],
            "temperature_c": last["temperature_c"],
            "pressure_hpa": last["pressure_hpa"],
            "humidity_pct": last["humidity_pct"],
            **annotations,
            "corrected_value": corrected_value,
        }
        record["_station_name"] = meta[sid]["name"]
        records.append(record)

    return records