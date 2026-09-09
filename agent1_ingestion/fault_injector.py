"""
Reads clean_dataset.csv, injects faults, writes two files:

  faulty_dataset.csv     - same schema as clean_dataset.csv, but with
                            faults applied. This is what Agent 2 sees.
  ground_truth_labels.csv - station_id, timestamp, fault_type. This is
                            the answer key. Keep it separate so nobody
                            accidentally trains on it.

Fault types:
  spike     - one reading jumps far outside its normal range
  frozen    - value repeats unchanged for several consecutive readings
  dropout   - reading is missing (blank fields)
  drift     - value gradually drifts away from truth over a window
"""

import csv
import random

random.seed(7)

FAULT_PROB = 0.02          # chance a given reading starts a fault
FROZEN_LEN = (4, 10)        # how many readings a frozen fault lasts
DRIFT_LEN = (10, 30)         # how many readings a drift fault lasts
DRIFT_MAX_OFFSET = 6.0      # max degrees/hPa/percent drifted away by


def inject_faults(rows):
    """rows: list of dicts with station_id, timestamp, temp, pressure, humidity, lat, lon"""
    faulty_rows = [dict(r) for r in rows]
    labels = []

    i = 0
    n = len(faulty_rows)
    while i < n:
        if random.random() < FAULT_PROB:
            fault_type = random.choice(["spike", "frozen", "dropout", "drift"])
            field = random.choice(["temp", "pressure", "humidity"])
            station = faulty_rows[i]["station_id"]

            if fault_type == "spike":
                orig = float(faulty_rows[i][field])
                sign = random.choice([1, -1])
                faulty_rows[i][field] = round(orig + sign * random.uniform(15, 30), 2)
                labels.append((station, faulty_rows[i]["timestamp"], "spike"))
                i += 1

            elif fault_type == "frozen":
                length = random.randint(*FROZEN_LEN)
                frozen_value = faulty_rows[i][field]
                for j in range(i, min(i + length, n)):
                    if faulty_rows[j]["station_id"] != station:
                        break
                    faulty_rows[j][field] = frozen_value
                    labels.append((station, faulty_rows[j]["timestamp"], "frozen"))
                i += length

            elif fault_type == "dropout":
                faulty_rows[i][field] = ""
                labels.append((station, faulty_rows[i]["timestamp"], "dropout"))
                i += 1

            elif fault_type == "drift":
                length = random.randint(*DRIFT_LEN)
                offset_step = DRIFT_MAX_OFFSET / length
                for j in range(i, min(i + length, n)):
                    if faulty_rows[j]["station_id"] != station:
                        break
                    steps_in = j - i
                    orig = float(faulty_rows[j][field])
                    faulty_rows[j][field] = round(orig + offset_step * steps_in, 2)
                    labels.append((station, faulty_rows[j]["timestamp"], "drift"))
                i += length
        else:
            i += 1

    return faulty_rows, labels


def main():
    with open("clean_dataset.csv") as f:
        rows = list(csv.DictReader(f))

    faulty_rows, labels = inject_faults(rows)

    fieldnames = ["station_id", "timestamp", "temp", "pressure", "humidity", "lat", "lon"]
    with open("faulty_dataset.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(faulty_rows)

    with open("ground_truth_labels.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["station_id", "timestamp", "fault_type"])
        writer.writerows(labels)

    print(f"Wrote faulty_dataset.csv ({len(faulty_rows)} rows)")
    print(f"Wrote ground_truth_labels.csv ({len(labels)} faulty readings, "
          f"{len(labels)/len(faulty_rows):.1%} of total)")


if __name__ == "__main__":
    main()