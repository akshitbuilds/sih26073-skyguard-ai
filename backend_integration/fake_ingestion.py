"""
STUB for Agent 1 (Data Ingestion) -- just enough to test the pipeline
locally before the real dataset/stream lands. Delete this once Agent 1's
real module is ready and point main.py at their code instead.
"""
import random
from datetime import datetime
from schema import StationReading

STATIONS = [
    {"station_id": "AWS_001", "latitude": 19.0760, "longitude": 72.8777},  # Mumbai
    {"station_id": "AWS_002", "latitude": 19.2183, "longitude": 72.9781},  # Thane
    {"station_id": "AWS_003", "latitude": 18.5204, "longitude": 73.8567},  # Pune
]


def get_fake_reading(station_index: int = 0, inject_fault: bool = False) -> StationReading:
    st = STATIONS[station_index % len(STATIONS)]
    temp = round(random.uniform(24, 34), 1)
    pres = round(random.uniform(1000, 1015), 1)
    hum = round(random.uniform(50, 85), 1)

    if inject_fault:
        # simulate a sudden extreme spike, like the official example use case
        temp, hum, pres = 55.0, 98.0, 985.0

    return StationReading(
        station_id=st["station_id"],
        timestamp=datetime.utcnow().isoformat() + "Z",
        latitude=st["latitude"],
        longitude=st["longitude"],
        temperature_c=temp,
        pressure_hpa=pres,
        humidity_pct=hum,
    )
