---
type: standard
domain: machine-learning
status: reviewed
confidence: medium
source: system-design
updated: 2026-05-17
use_when:
  - design ML experiments
  - split train validation holdout
  - evaluate time series prediction
evidence_level: user_experience
use_for:
  - decision_risk_review
scope: Default ML leakage prevention standard, not model-effectiveness proof
should_not_use_for: treating this reviewed note as externally verified fact
time_sensitivity: medium
review_cycle: 180d
usage_count: 0
last_used: 
last_feedback: 
failure_modes:
improvement_notes:
human_review:
  reviewer: user
  decision: S=B,U=C,R=B,E=E
  reviewed_at: 2026-05-17
  result: registry overlay restored; Default ML leakage prevention standard, not model-effectiveness proof
---

# Leakage Prevention

## Rules

- Split data according to the prediction setting, not convenience.
- For temporal prediction, prefer time-based validation, rolling windows, or walk-forward validation.
- Fit preprocessing only on the training window, then apply it to validation and holdout.
- Keep holdout isolated; do not repeatedly tune after reading holdout results.
- Record feature availability time and label horizon.

## Finance-Specific Note

For stock return prediction, route jointly with `quant` standards. Point-in-time data, trade delay, transaction costs, and survivorship bias checks outrank generic ML convenience.
