"""
Adapter wrapping Agent 5's real correction.py (estimate_corrected_value)
with our shared StationState. This one IS fully tested -- see
test_agent5_correction.py in this same folder.

anomaly_type values that should trigger a correction attempt: anything
in agent5_dashboard/schema.py's ANOMALY_TYPES except "none" and
"genuine_event" (a real weather event isn't something we want to
"correct" -- there's nothing wrong with the reading).
"""

from datetime import datetime
from typing import Dict, Optional

from correction import estimate_corrected_value, FIELDS
from station_state import StationState

FAULT_TYPES_TO_CORRECT = {"sensor_stuck", "sensor_spike", "sensor_drift", "sensor_dropout"}


def _parse_history_for_correction(raw_history: list, current_timestamp: str) -> list:
    """correction.py expects each history point's 'timestamp' as a real
    datetime, and expects the LAST list entry to be an anchor for the
    current timestamp (its field values are never read -- only .timestamp
    matters, per correction_accuracy.py's own usage)."""
    parsed = []
    for r in raw_history:
        parsed.append({
            "timestamp": datetime.fromisoformat(r["timestamp"]),
            **{f: r[f] for f in FIELDS},
        })
    parsed.append({
        "timestamp": datetime.fromisoformat(current_timestamp),
        **{f: 0.0 for f in FIELDS},  # unused anchor values, see correction.py
    })
    return parsed


def maybe_correct(
    reading: dict,
    anomaly_type: str,
    state: StationState,
    latest_screening: Dict[str, str],
) -> Optional[dict]:
    """Returns a corrected_value dict, or None if no correction was
    attempted/possible (normal reading, genuine_event, or not enough
    data to estimate from)."""
    if anomaly_type not in FAULT_TYPES_TO_CORRECT:
        return None

    station_id = reading["station_id"]
    raw_history = state.get_history(station_id)
    histories = {station_id: _parse_history_for_correction(raw_history, reading["timestamp"])}

    neighbors_current = state.get_neighbors_current(station_id)
    current_snapshot = {
        sid: {f: r[f] for f in FIELDS} for sid, r in neighbors_current.items()
        if all(r.get(f) is not None for f in FIELDS)
    }
    healthy_ids = state.healthy_neighbor_ids(station_id, latest_screening)

    return estimate_corrected_value(
        station_id=station_id,
        histories=histories,
        current_snapshot=current_snapshot,
        meta=state.meta,
        healthy_station_ids=healthy_ids,
    )
