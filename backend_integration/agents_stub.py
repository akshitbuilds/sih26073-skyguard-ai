"""
STUB agents. Each function fakes what the real teammate's module will do.
Replace ONE function at a time as each person's real code lands -- the
orchestrator in main.py doesn't need to change when you do.

Real modules should expose the SAME function signature:
    def run(reading: StationReading) -> StationReading
so swapping stub -> real is a one-line import change, nothing else.
"""
import random
from schema import StationReading, Explanation, CorrectedValue


def agent2_screening_stub(r: StationReading) -> StationReading:
    r.physical_consistency_score = round(random.uniform(0.6, 1.0), 2)
    r.spatial_deviation_score = round(random.uniform(0.0, 1.0), 2)
    # never silently discard high deviation -- escalate instead
    if r.spatial_deviation_score > 0.7:
        r.screening_flag = "high_priority"
    elif r.spatial_deviation_score > 0.4:
        r.screening_flag = "watch"
    else:
        r.screening_flag = "clean"
    return r


def agent3_ml_detection_stub(r: StationReading) -> StationReading:
    r.reconstruction_error = round(random.uniform(0.0, 1.0), 3)
    r.ml_anomaly_score = round(min(r.reconstruction_error * 1.2, 1.0), 2)
    return r


def agent4_explainability_stub(r: StationReading) -> StationReading:
    score = (r.spatial_deviation_score or 0) + (r.ml_anomaly_score or 0)
    if score < 0.5:
        r.anomaly_type = "normal"
        r.confidence_score = 0.9
    elif r.physical_consistency_score and r.physical_consistency_score > 0.8:
        # deviates from neighbors but internally coherent -> lean genuine event, don't suppress
        r.anomaly_type = "genuine_event"
        r.confidence_score = 0.55
    else:
        r.anomaly_type = random.choice(["sensor_spike", "frozen_value", "comm_error", "drift"])
        r.confidence_score = round(random.uniform(0.6, 0.9), 2)

    r.explanation = Explanation(
        top_factors=["spatial_deviation_score", "reconstruction_error"],
        reasoning_text=f"[STUB] Flagged as {r.anomaly_type} based on placeholder scoring logic.",
    )
    r.sensor_health_status = random.choice(["green", "green", "green", "amber", "red"])
    return r


def agent5_correction_alert_stub(r: StationReading) -> StationReading:
    if r.anomaly_type not in ("normal", "genuine_event"):
        r.corrected_value = CorrectedValue(
            temperature_c=round(r.temperature_c + random.uniform(-1, 1), 1),
            pressure_hpa=round(r.pressure_hpa + random.uniform(-2, 2), 1),
            humidity_pct=round(min(max(r.humidity_pct + random.uniform(-3, 3), 0), 100), 1),
        )
    severity_map = {
        "normal": "none", "genuine_event": "high",
        "sensor_spike": "medium", "frozen_value": "medium",
        "comm_error": "low", "drift": "low",
    }
    r.alert_severity = severity_map.get(r.anomaly_type, "low")
    return r
