"""
Agent 4 adapter.

STATUS -- be precise about what's real vs placeholder here, this matters:

  REAL, verbatim, no placeholder: apply_safety_gate() -- the non-negotiable
  "never silently dismiss a high_priority reading" rule. Zero dependency on
  the missing files, genuinely running.

  PLACEHOLDER, clearly marked below: the model_verdict/model_confidence that
  would normally come from Agent 4's real ScoreGateClassifier (RandomForest +
  SHAP). That needs score_classifier.py, score_features.py,
  score_explainability.py, which haven't landed yet. Until then, a simple
  rule-based stand-in feeds the (REAL) safety gate so the pipeline runs
  end-to-end. Swap `_placeholder_model_call()` for a real
  ScreeningGate().classify() call the moment those 3 files arrive -- nothing
  else in this file needs to change.

  BONUS, using real Agent 2 output: when the gate's final verdict is
  "sensor_fault", we still need ONE of our locked anomaly_type strings
  (sensor_spike/sensor_stuck/sensor_drift/sensor_dropout) -- the gate itself
  only says fault-vs-not. We use Agent 2's real temporal signals
  (jump_variables/stale_variables, from agent2_detail) as a genuine, non-fake
  hint for which one, rather than guessing blindly. This is a real inference
  from real upstream data, not a placeholder.
"""

from agent4_explainability.schemas import ScreeningFlag
from agent4_explainability.screening_gate_core import apply_safety_gate

# our locked screening_flag vocabulary -> Agent 4's ScreeningFlag enum.
# Only HIGH_PRIORITY changes gate behavior (see screening_gate.py's own
# docstring: "Standard/low_priority readings use the classifier's call
# directly... since a false dismissal there does not carry the same cost"),
# so the exact clean->? / watch->? split below doesn't affect correctness,
# only audit-log readability.
_FLAG_MAP = {
    "high_priority": ScreeningFlag.HIGH_PRIORITY.value,
    "watch": ScreeningFlag.STANDARD.value,
    "clean": ScreeningFlag.LOW_PRIORITY.value,
}

PHYSICALLY_COHERENT_THRESHOLD = 0.5  # physical_consistency_score >= this counts as coherent


def _placeholder_model_call(ml_anomaly_score: float, physically_coherent: bool) -> tuple[str, float]:
    """PLACEHOLDER for ScoreGateClassifier.predict() -- simple rule, not a
    trained model. Replace with the real classifier once its 3 files land."""
    if ml_anomaly_score >= 0.6 and not physically_coherent:
        return "sensor_fault", round(min(0.5 + ml_anomaly_score / 2, 0.95), 2)
    return "genuine_event", 0.6


def _hint_fault_type(agent2_detail: dict) -> str:
    """Real inference from Agent 2's real temporal output -- not a guess."""
    if not agent2_detail:
        return "sensor_spike"
    if agent2_detail.get("stale_variables"):
        return "sensor_stuck"
    if agent2_detail.get("jump_variables"):
        return "sensor_spike"
    return "sensor_spike"  # default when neither signal is present


def run_agent4_gate(reading: dict, latest_screening_flag: str) -> dict:
    """
    reading: flat dict, must already have spatial_deviation_score,
    physical_consistency_score, ml_anomaly_score (Agent 3's field --
    still stub-sourced until Agent 3's real inference code lands),
    and optionally agent2_detail.
    """
    physically_coherent = (reading.get("physical_consistency_score") or 1.0) >= PHYSICALLY_COHERENT_THRESHOLD
    spatial_dev = reading.get("spatial_deviation_score") or 0.0
    ml_score = reading.get("ml_anomaly_score") or 0.0
    agent2_detail = reading.get("agent2_detail")

    # Honor Agent 2's own multi-variable corroboration reasoning directly --
    # it already did real work identifying a probable genuine event, don't
    # make the (currently placeholder) classifier re-litigate it.
    if agent2_detail and agent2_detail.get("verdict") == "POSSIBLE_REAL_EVENT":
        model_verdict, model_confidence = "genuine_event", 0.75
    else:
        model_verdict, model_confidence = _placeholder_model_call(ml_score, physically_coherent)

    a4_flag = _FLAG_MAP.get(latest_screening_flag, ScreeningFlag.STANDARD.value)

    # --- REAL, non-placeholder logic from here down ---
    final_verdict, override_triggered, gate_reason = apply_safety_gate(
        screening_flag=a4_flag,
        model_verdict=model_verdict,
        model_confidence=model_confidence,
        physically_coherent=physically_coherent,
        spatial_deviation_score=spatial_dev,
    )

    if final_verdict == "genuine_event":
        anomaly_type = "genuine_event"
    elif final_verdict == "escalate_uncertain":
        # non-negotiable: never silently dismissed -- treated as a real
        # event pending review, per the module's own design principle
        anomaly_type = "genuine_event"
    else:  # sensor_fault
        anomaly_type = _hint_fault_type(agent2_detail)

    return {
        "anomaly_type": anomaly_type,
        "confidence_score": model_confidence,
        "explanation": {
            "gate_verdict": final_verdict,
            "model_verdict": model_verdict,
            "safety_override_triggered": override_triggered,
            "gate_reason": gate_reason,
        },
    }
