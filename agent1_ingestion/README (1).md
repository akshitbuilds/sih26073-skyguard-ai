# Agent 1 - Data Ingestion

## Files
- `schema.json` - the record format. Read this first.
- `generate_dataset.py` -> `clean_dataset.csv` (5 Gujarat coastal stations, hourly, May 2021, ~3,720 readings)
- `fault_injector.py` -> `faulty_dataset.csv` + `ground_truth_labels.csv`
- `replay.py` -> streams a CSV as live JSON lines to stdout
- `run_all.sh` -> runs all three in order
- `requirements.txt` -> Python packages needed to run `generate_dataset.py`

## Data source
`generate_dataset.py` pulls **real historical weather data** from the
Open-Meteo Archive API (archive-api.open-meteo.com) for 5 Gujarat
coastal stations (Diu, Veraval, Mahuva, Porbandar, Bhavnagar),
May 1-31, 2021. This is real data, not synthetic.

Note: Open-Meteo gives **hourly** readings (not 15-minute), and
`surface_pressure` is station-altitude-dependent, not sea-level
pressure - so baseline pressure will differ slightly station to
station. That's expected and realistic.

## Before running - install dependencies
```bash
pip install -r requirements.txt
```

## How to run it, in order
```bash
python3 generate_dataset.py     # makes clean_dataset.csv
python3 fault_injector.py       # makes faulty_dataset.csv + ground_truth_labels.csv
python3 replay.py               # streams faulty_dataset.csv as JSON lines
```
Or all at once:
```bash
./run_all.sh
```

## For Agent 2 (anomaly detector)
Read `faulty_dataset.csv` (or pipe from `replay.py`) - that's your input,
it has no labels. Train/evaluate against `ground_truth_labels.csv`
separately. Don't let the detector see the labels file.

```bash
python3 replay.py --speed 0.05 | your_detector.py
```

## Fault types in ground_truth_labels.csv
- `spike` - one reading jumps 15-30 units off
- `frozen` - value repeats unchanged for 4-10 readings
- `dropout` - field is blank / null
- `drift` - value gradually drifts up to 6 units over 10-30 readings

~13% of readings currently carry a fault (tune `FAULT_PROB` in
`fault_injector.py` if you want it rarer/more common).

## Tuning
- Different stations / date range: edit `STATIONS` and `start_date`/`end_date` in `generate_dataset.py`
- Different fault mix: edit `FAULT_PROB`, `FROZEN_LEN`, `DRIFT_LEN`, `DRIFT_MAX_OFFSET` in `fault_injector.py`

## Note
Delete `tempCodeRunnerFile.py` if you see it in this folder - it's a
VS Code "Code Runner" auto-generated leftover, not a real project file.
