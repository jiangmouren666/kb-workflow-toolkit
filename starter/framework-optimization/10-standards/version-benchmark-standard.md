---
type: standard
domain: framework-optimization
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
  - framework_optimization
  - benchmark_review
scope: framework performance, configuration, caching, rendering, bundling, and architecture optimization
should_not_use_for: applying old framework advice without version and benchmark checks
time_sensitivity: high
review_cycle: 90d
---

# Framework Optimization Evidence Standard

## Evidence Types

| Evidence Type | Strength | Use For | Limit |
|---|---|---|---|
| Benchmark before/after | high | performance claims | must match workload |
| Profiling trace | high | bottleneck identification | may not generalize |
| Official docs for exact version | high | supported configuration | can change across versions |
| Production metrics | high | real impact | affected by traffic and environment |
| Generic optimization advice | low | hypotheses | must be measured |

## Status Mapping

- `draft`: generic advice, old article, or unmeasured configuration idea.
- `reviewed`: human-accepted optimization pattern with clear caveats.
- `verified`: version recorded, benchmark/profiling evidence captured, and no known regression.
- `stale`: framework version changed, API deprecated, or benchmark older than review cycle.
- `rejected`: no improvement, regression, unsupported config, or harmful side effects.

## Extra Metadata

```yaml
framework:
version:
benchmark_env:
metric_before:
metric_after:
side_effects:
```

## Risk Rules

- Never claim optimization without measurement.
- Always record version and environment.
- Prefer rollback notes for production-facing optimizations.

## Conflict Priority

1. Current project benchmark and profiling results.
2. Official docs for exact version.
3. Production telemetry.
4. Maintainer issues and release notes.
5. Older blog posts or AI summaries.
