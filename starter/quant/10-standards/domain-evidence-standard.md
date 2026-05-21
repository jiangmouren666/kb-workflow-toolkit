---
type: standard
domain: quant-factor
status: reviewed
confidence: high
usage_count: 0
last_used:
last_feedback:
failure_modes: []
improvement_notes: []
human_review:
  reviewer: user
  decision: approved three-layer global/domain/content framework
  reviewed_at: 2026-05-18
  result: accepted as reviewed system-design standard, not externally verified fact
evidence_level: user_experience
source: system-design
updated: 2026-05-18
use_for:
  - domain_evidence_standard
  - factor_research_verification
  - conflict_resolution
scope: quantitative factor research, backtests, portfolio validation, and live-trading readiness review
should_not_use_for: approving real-money trading without independent validation
time_sensitivity: medium
review_cycle: 180d
---

# Quant Domain Evidence Standard

## Evidence Types

| Evidence Type | Strength | Use For | Limit |
|---|---|---|---|
| Point-in-time data and availability dates | high | leakage checks | must match actual data pipeline |
| Reproducible backtest with costs | high | research validation | not live proof |
| Out-of-sample or paper trading | high | deployment readiness | still not guaranteed future performance |
| RankIC, ICIR, grouped returns | medium | signal quality | insufficient alone |
| Blog, article, AI summary | low | hypotheses | never final evidence |

## Status Mapping

- `draft`: factor idea, paper note, unverified result, or incomplete backtest.
- `reviewed`: accepted research checklist, method, or template.
- `verified`: no lookahead, point-in-time data, costs, robustness, and out-of-sample or paper-trading evidence.
- `stale`: old market regime, old data vendor behavior, or unreviewed after review cycle.
- `rejected`: future leakage, untradeable universe, unstable result, or data error.

## Risk Rules

- High Sharpe is not live-trading permission.
- Missing costs, turnover, tradability, or point-in-time universe requires answer downgrade.
- Test-set reuse and parameter fishing must be called out.

## Conflict Priority

1. Point-in-time data and executable backtest logs.
2. Domain standards and reviewed checklists.
3. Paper or official dataset documentation.
4. User notes and articles.
5. AI-generated summaries.
