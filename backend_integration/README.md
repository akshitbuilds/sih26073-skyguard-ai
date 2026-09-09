# SkyGuard AI — Backend Integration (SIH26073)

## Run it
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Then open http://localhost:8000/demo/0 in a browser, or:
```bash
curl http://localhost:8000/demo/0
curl "http://localhost:8000/demo/0?inject_fault=true"
```

## What's here right now
Every agent is a STUB (`agents_stub.py`) — fake logic that returns
realistic-shaped fake data. This lets the whole pipeline run end-to-end
today, before anyone's real module is ready.

## How to swap in a real teammate's module (do this one at a time)
1. Teammate pushes their code to their folder, e.g. `agent3_ml_detection/model.py`,
   exposing a function: `def run(reading: StationReading) -> StationReading`
2. In `main.py`, change:
   ```python
   from agents_stub import agent3_ml_detection_stub as agent3_run
   ```
   to:
   ```python
   from agent3_ml_detection.model import run as agent3_run
   ```
3. Re-run `uvicorn main:app --reload` and hit `/demo/0` again — if it still
   returns valid JSON, that agent is integrated. Move to the next one.

Do this in order: Agent 2 → Agent 3 → Agent 4 → Agent 5, since each one's
output feeds the next. Never wait for all 4 to be ready — swap each in
the moment it lands.

## Real usage (once Agent 1's real data is ready)
`POST /process` with a raw reading — Agent 1's module should output
JSON matching this shape, which this endpoint accepts directly:
```json
{
  "station_id": "AWS_001", "timestamp": "2026-09-09T10:00:00Z",
  "latitude": 19.076, "longitude": 72.8777,
  "temperature_c": 28.5, "pressure_hpa": 1008.2, "humidity_pct": 65.0
}
```
