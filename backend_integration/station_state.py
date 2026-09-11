"""
Shared per-station state for the SkyGuard AI pipeline.

Both Agent 2 (needs neighbors' CURRENT readings + this station's HISTORY)
and Agent 5's correction.py (needs the exact same two things, same shape)
depend on this, so it lives in one place instead of being duplicated.

This is intentionally an in-memory, single-process store -- fine for a
hackathon demo driven by replay.py. Swap for Redis/a real time-series DB
if this ever needs to survive a restart or run across multiple processes.
"""

from collections import defaultdict, deque
from typing import Dict, List, Optional

HISTORY_WINDOW = 50  # how many past readings we keep per station


class StationState:
    def __init__(self, station_meta: Dict[str, dict], history_window: int = HISTORY_WINDOW):
        """station_meta: {station_id: {"latitude": .., "longitude": ..}}"""
        self.meta = station_meta
        self.history_window = history_window
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_window))
        self._current: Dict[str, dict] = {}

    def record(self, reading: dict) -> None:
        """Call this for every incoming reading, BEFORE running any agent on it,
        so 'history' means 'everything up to but not including current'."""
        station_id = reading["station_id"]
        # snapshot current BEFORE overwriting, so get_history/get_neighbors below
        # reflect the state as of just-before this reading (matches what a real
        # streaming system would have had available when this reading arrived)
        if station_id in self._current:
            self._history[station_id].append(self._current[station_id])
        self._current[station_id] = reading

    def get_history(self, station_id: str) -> List[dict]:
        """This station's past readings, oldest -> newest, NOT including current."""
        return list(self._history[station_id])

    def get_neighbors_current(self, station_id: str) -> Dict[str, dict]:
        """Every OTHER station's most recent reading (may be from a different
        tick if that station hasn't reported yet this round -- fine for a demo)."""
        return {sid: r for sid, r in self._current.items() if sid != station_id}

    def healthy_neighbor_ids(self, station_id: str, latest_screening: Dict[str, str]) -> List[str]:
        """latest_screening: {station_id: screening_flag} for whichever stations
        we've already screened this tick. A neighbor counts as healthy if we
        have no reason yet to think ITS reading is itself bad."""
        neighbors = self.get_neighbors_current(station_id)
        return [
            sid for sid in neighbors
            if latest_screening.get(sid, "clean") == "clean"
        ]
