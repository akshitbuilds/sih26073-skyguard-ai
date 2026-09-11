# SkyGuard AI — Backend Integration (SIH26073)

## Status as of this integration pass
| Agent | Status | Notes |
|---|---|---|
| 1 — Ingestion | **REAL** | agent1_ingestion/*.csv, verified |
| 2 — Screening | **REAL, verified** | Full pipeline running live, cyclone scenario proven |
| 3 — ML Detection | STUB | still waiting on real inference code |
| 4 — Safety Gate | **REAL** (`apply_safety_gate`) | verbatim, all 4 logic branches directly verified — see test output |
| 4 — ML Classifier | PLACEHOLDER | rule-based stand-in until score_classifier.py/score_features.py/score_explainability.py land |
| 4 — Root-cause detail | PLACEHOLDER | fault-type hint uses Agent 2's real temporal signals, not the full RootCauseClassifier (needs features.py/explainability.py/degradation_tracker.py) |
| 5 — Correction | **REAL, verified** | recovers a 55°C fault to 28.75°C using real history+neighbor data |
| 5 — Alert severity | STUB | correction is real, severity assignment still stubbed |

## What's genuinely proven right now
- Agent 2's real pipeline correctly recognizes a Cyclone-Tauktae-like signature
  as `POSSIBLE_REAL_EVENT`, not a sensor fault (see test_integration.py)
- Agent 4's safety gate: verified all 4 branches directly — standard-priority
  passthrough, high-priority+strong-evidence dismissal, and (the critical one)
  high-priority+weak-evidence correctly escalates to `escalate_uncertain`
  rather than silently dismissing. This is your core "never suppress a real
  disaster" design principle, proven in real code, not just described in
  a pitch deck.
- Agent 5's correction engine recovers a real fault to within ~0.4°C of true
  value using actual multi-station history

## Still needed from Agent 4, in priority order
1. `score_classifier.py`, `score_features.py`, `score_explainability.py` —
   replaces the current rule-based placeholder model call with the real
   trained RandomForest + SHAP classifier. The safety gate underneath
   doesn't need to change at all once these land — only
   `agent4_adapter.py`'s `_placeholder_model_call()` gets swapped for a
   real `ScreeningGate().classify()` call.
2. `features.py`, `explainability.py`, `degradation_tracker.py` — needed for
   the OTHER Agent 4 capability (`explain_flag`/RootCauseClassifier),
   which gives fine-grained root-cause + sensor degradation status. Lower
   priority than #1.

## Still needed from Agent 3
Real inference code — a function that takes recent readings for a station
and returns `reconstruction_error` / `ml_anomaly_score`. Send `src/`
folder contents once available.

## LOCKED vocabulary — final, no more changes
`anomaly_type`: `sensor_stuck | sensor_spike | sensor_drift | sensor_dropout | genuine_event | none`
`screening_flag`: `clean | watch | high_priority`

## Running it
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
`python3 test_integration.py` for the real multi-tick proof (includes
history/neighbor state the single-shot /demo endpoint can't show).
