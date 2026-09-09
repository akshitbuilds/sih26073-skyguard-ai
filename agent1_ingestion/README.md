# Agent 1 - Data Ingestion

## Files
- `schema.json` - the record format. Read this first.
- `generate_dataset.py` -> `clean_dataset.csv` (5 stations, 30 days, 15-min intervals, ~14,400 readings)
- `fault_injector.py` -> `faulty_dataset.csv` + `ground_truth_labels.csv`
- `replay.py` -> streams a CSV as live JSON lines to stdout

## Important caveat
`generate_dataset.py` produces **synthetic** data, not real IMD/data.gov.in
data - this sandbox can't reach those sites. The seasonal/daily patterns
are realistic (daily temp cycle, slow pressure drift, humidity tied
inversely to temp) but it's not real station history. If you get real
IMD/data.gov.in access later, swap the generator for a real downloader -
the CSV schema (`schema.json`) doesn't need to change.

## How to run it, in order
```bash
python3 generate_dataset.py     # makes clean_dataset.csv
python3 fault_injector.py       # makes faulty_dataset.csv + ground_truth_labels.csv
python3 replay.py               # streams faulty_dataset.csv as JSON lines
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
- More stations / longer history: edit `STATIONS` and `DAYS` in `generate_dataset.py`
- Different fault mix: edit `FAULT_PROB`, `FROZEN_LEN`, `DRIFT_LEN`, `DRIFT_MAX_OFFSET` in `fault_injector.py`
