"""
Shared data contract for SkyGuard AI (SIH26073). Every agent reads a
StationReading, fills in its own fields, and passes the same object on.
This is the one file the whole team should treat as "do not change the
field names without telling everyone" -- everything else can change freely.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class Explanation(BaseModel):
    top_factors: List[str] = []
    reasoning_text: str = ""


class CorrectedValue(BaseModel):
    temperature_c: float
    pressure_hpa: float
    humidity_pct: float


class StationReading(BaseModel):
    # ---- Filled by Agent 1 (Data Ingestion) ----
    station_id: str
    timestamp: str
    latitude: float
    longitude: float
    temperature_c: float
    pressure_hpa: float
    humidity_pct: float

    # ---- Filled by Agent 2 (Consistency Screening) ----
    spatial_deviation_score: Optional[float] = None
    physical_consistency_score: Optional[float] = None
    screening_flag: Optional[str] = None  # "clean" | "watch" | "high_priority"
    agent2_detail: Optional[Dict[str, Any]] = None  # verdict/explanation from Agent 2's
                                                       # reasoning layer -- IMPORTANT: a
                                                       # "clean" screening_flag + verdict
                                                       # "POSSIBLE_REAL_EVENT" here means a
                                                       # real event was detected and correctly
                                                       # NOT penalized as a sensor fault --
                                                       # Agent 4 should treat this as strong
                                                       # evidence for anomaly_type=genuine_event

    # ---- Filled by Agent 3 (ML Detection) ----
    ml_anomaly_score: Optional[float] = None
    reconstruction_error: Optional[float] = None

    # ---- Filled by Agent 4 (Root-Cause + Explainability) ----
    anomaly_type: Optional[str] = None  # sensor_spike | frozen_value | comm_error | drift | genuine_event | normal
    confidence_score: Optional[float] = None
    explanation: Optional[Dict[str, Any]] = None  # Agent 4's real shape: gate_verdict,
                                                     # model_verdict, safety_override_triggered,
                                                     # gate_reason (kept flexible since Agent 2's
                                                     # agent2_detail has a different, also useful shape)
    sensor_health_status: Optional[str] = None  # "green" | "amber" | "red"

    # ---- Filled by Agent 5 (Correction & Alert) ----
    corrected_value: Optional[CorrectedValue] = None
    alert_severity: Optional[str] = None  # none | low | medium | high | critical
