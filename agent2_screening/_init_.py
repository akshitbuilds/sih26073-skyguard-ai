"""
Agent 2 — AWS (Automatic Weather Station) Anomaly Pre-Screening Agent
======================================================================

Implements Phases 1-8 of the design:

    Phase 1  Input schema              -> agent2.schema
    Phase 2  Physical consistency      -> agent2.physical
    Phase 3  Spatial consistency       -> agent2.spatial
    Phase 4  Temporal consistency      -> agent2.temporal
    Phase 5  Reasoning / non-rejection -> agent2.reasoning
    Phase 6  Confidence scoring        -> agent2.scoring
    Phase 7  Historical validation     -> agent2.validation
    Phase 8  Integration pipeline      -> agent2.pipeline

Quick start:

    from agent2 import Agent2
    agent = Agent2()
    report = agent.evaluate(station_reading, neighbor_readings, history)
    print(report.final_label, report.confidence_score)
"""

from .pipeline import Agent2
from .schema import StationReading, Coordinates

__all__ = ["Agent2", "StationReading", "Coordinates"]
__version__ = "1.0.0"
