#!/bin/bash
# Runs the full data ingestion pipeline in order.
set -e

python3 generate_dataset.py
python3 fault_injector.py
python3 replay.py --speed 0
