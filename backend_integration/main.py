"""
SkyGuard AI - backend orchestrator (SIH26073)

Agent status as of this integration pass:
  Agent 1 (ingestion)      REAL   - agent1_ingestion/*.csv
  Agent 2 (screening)      REAL   - via agent2_adapter.py, imports the
                                     REAL agent2_screening/ package that
                                     sits alongside this backend_integration/
                                     folder in the repo (see sys.path fix below)
  Agent 3 (ML detection)   STUB   - swap when it lands
  Agent 4 (explainability) STUB   - swap when it lands
  Agent 5 (correction)     REAL   - via agent5_correction_adapter.py,
                                     fully tested (see test_integration.py)
  Agent 5 (alert severity) STUB   - correction is real, alert-severity
                                     assignment isn't wired yet
"""
import sys
import os
# Repo layout is: sih26073-skyguard-ai/agent2_screening/  (Agent 2's real code)
#                 sih26073-skyguard-ai/backend_integration/main.py  (this file)
# agent2_screening is a SIBLING folder, not nested inside backend_integration --
# this line makes it importable regardless of which directory you launch
# uvicorn from, as long as the repo's folder layout itself is correct.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi import FastAPI
from schema import StationReading
from fake_ingestion import get_fake_reading
from station_state import StationState

from agents_stub import (
    agent3_ml_detection_stub as agent3_run,
    agent5_correction_alert_stub as agent5_alert_stub,
)
from agent5_correction_adapter import maybe_correct
from agent4_adapter import run_agent4_gate

try:
    from agent2_adapter import run_agent2_screening, AGENT2_AVAILABLE
except ImportError:
    AGENT2_AVAILABLE = False

if not AGENT2_AVAILABLE:
    from agents_stub import agent2_screening_stub

app = FastAPI(title="SkyGuard AI - SIH26073")

# 5 real Gujarat stations from agent1_ingestion/generate_dataset.py
STATION_META = {
    "AWS_DIU":       {"latitude": 20.7141, "longitude": 70.9822},
    "AWS_VERAVAL":   {"latitude": 20.9077, "longitude": 70.3679},
    "AWS_MAHUVA":    {"latitude": 21.0901, "longitude": 71.7690},
    "AWS_PORBANDAR": {"latitude": 21.6422, "longitude": 69.6093},
    "AWS_BHAVNAGAR": {"latitude": 21.7629, "longitude": 72.1533},
}
state = StationState(STATION_META)
_latest_screening: dict = {}  # station_id -> screening_flag, updated as we go


def run_pipeline(reading: StationReading) -> StationReading:
    r = reading.dict()
    history_before = state.get_history(r["station_id"])
    neighbors_before = list(state.get_neighbors_current(r["station_id"]).values())

    # --- Agent 2: screening ---
    if AGENT2_AVAILABLE:
        a2_out = run_agent2_screening(r, neighbors_before, history_before)
        r.update(a2_out)
        reading = StationReading(**r)
    else:
        reading = agent2_screening_stub(reading)
        r = reading.dict()
    _latest_screening[r["station_id"]] = r.get("screening_flag", "clean")

    # --- Agent 3: still stubbed (waiting on real inference code) ---
    reading = agent3_run(reading)

    # --- Agent 4: real safety gate, placeholder model call underneath it ---
    r = reading.dict()
    a4_out = run_agent4_gate(r, _latest_screening.get(r["station_id"], "clean"))
    r.update(a4_out)
    reading = StationReading(**r)

    # --- Agent 5: real correction, stubbed alert severity ---
    r = reading.dict()
    corrected = maybe_correct(r, r.get("anomaly_type"), state, _latest_screening)
    if corrected is not None:
        r["corrected_value"] = corrected
    reading = StationReading(**r)
    reading = agent5_alert_stub(reading)  # alert_severity still stubbed

    # record AFTER processing, so this reading becomes "history" for next time
    state.record(reading.dict())
    return reading


@app.get("/")
def health_check():
    return {
        "status": "SkyGuard AI backend is running",
        "ps": "SIH26073",
        "agent2_real": AGENT2_AVAILABLE,
    }


@app.post("/process", response_model=StationReading)
def process_reading(reading: StationReading):
    return run_pipeline(reading)


@app.get("/demo/{station_index}", response_model=StationReading)
def demo_run(station_index: int = 0, inject_fault: bool = False):
    reading = get_fake_reading(station_index, inject_fault)
    return run_pipeline(reading)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
