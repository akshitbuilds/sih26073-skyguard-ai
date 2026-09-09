"""
SkyGuard AI - backend orchestrator (SIH26073)

Runs a raw station reading through all 5 agents in sequence and returns
the fully-enriched object. Right now every agent is STUBBED -- swap each
import below for the real teammate's module the moment it lands. The
pipeline logic here does not need to change when you do that.
"""
from fastapi import FastAPI
from schema import StationReading
from fake_ingestion import get_fake_reading

# --- SWAP THESE ONE AT A TIME AS REAL MODULES LAND ---
from agents_stub import (
    agent2_screening_stub as agent2_run,
    agent3_ml_detection_stub as agent3_run,
    agent4_explainability_stub as agent4_run,
    agent5_correction_alert_stub as agent5_run,
)
# Example of what it looks like once Agent 3's real code lands:
# from agent3_ml_detection.model import run as agent3_run

app = FastAPI(title="SkyGuard AI - SIH26073")


def run_pipeline(reading: StationReading) -> StationReading:
    reading = agent2_run(reading)
    reading = agent3_run(reading)
    reading = agent4_run(reading)
    reading = agent5_run(reading)
    return reading


@app.get("/")
def health_check():
    return {"status": "SkyGuard AI backend is running", "ps": "SIH26073"}


@app.post("/process", response_model=StationReading)
def process_reading(reading: StationReading):
    """Real endpoint: POST a raw reading (station_id, timestamp, lat, lon,
    temperature_c, pressure_hpa, humidity_pct), get back the full pipeline output."""
    return run_pipeline(reading)


@app.get("/demo/{station_index}", response_model=StationReading)
def demo_run(station_index: int = 0, inject_fault: bool = False):
    """Convenience endpoint for local testing without needing Agent 1's
    real data yet -- generates a fake reading and runs it through the pipeline."""
    reading = get_fake_reading(station_index, inject_fault)
    return run_pipeline(reading)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
