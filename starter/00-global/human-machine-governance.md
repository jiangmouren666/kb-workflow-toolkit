---
type: standard
domain: global
status: draft
confidence: high
source: system-design
updated: 2026-05-17
use_when:
  - combine human review with machine triage
  - choose knowledge metadata parameters
  - resolve conflicts between notes
  - improve retrieval and answer quality from feedback
---

# Human Machine Governance

## Core Rule

Machine processing improves scale, structure, and anomaly detection. It must not automatically increase knowledge trust. Trust increases only through human review, external evidence, experiments, source-code checks, backtests, production results, or comparable proof.

## Responsibility Split

| Actor | Responsible For | Must Not Do Alone |
|---|---|---|
| Machine | extract facts, claims, risks, unknowns, metadata drafts, conflicts, duplicates, stale candidates | mark unverified claims as facts; delete, merge, or verify knowledge automatically |
| Human | direction, usefulness, business fit, acceptable risk, final judgment for high-impact ambiguity | treat preference as factual proof |
| Evidence | official docs, source code, experiments, backtests, production results | replace judgment about scope and business fit |

## Required Parameters

Every reusable note should prefer these fields:

```yaml
status: draft
confidence: low
evidence_level: source_claim
use_for: []
scope: ""
should_not_use_for: ""
time_sensitivity: medium
review_cycle: 180d
usage_count: 0
last_used:
last_feedback:
failure_modes: []
improvement_notes: []
```

## Parameter Selection

| Material Type | Suggested Defaults |
|---|---|
| raw article, image, conversation, blog | `status: draft`, `confidence: low`, `evidence_level: source_claim` |
| user-approved workflow or preference | `status: reviewed`, `confidence: medium`, `evidence_level: user_experience` |
| official documentation or source-code verified note | `status: verified`, `confidence: high`, `evidence_level: official_doc` or `source_code` |
| experiment, backtest, or production result | `status: verified`, `confidence: high`, matching `evidence_level` |
| API, market, policy, model-performance, or library behavior | `time_sensitivity: high`, `review_cycle: 30d` or `90d` |
| stable concept, checklist, or thinking framework | `time_sensitivity: low` or `medium`, `review_cycle: 180d` or `365d` |

## Conflict Resolution

Resolve conflicts by evidence and scope, not by recency alone.

Priority:

1. safety, legal, money, health, and production constraints
2. global and domain standards
3. `verified` notes
4. `reviewed` notes
5. `draft` notes
6. `raw`, `stale`, `deprecated`, or source material

Evidence priority:

1. official documentation, source code, experiments, backtests, production results
2. human expert review or user experience
3. high-quality papers, books, or standards
4. articles, blogs, forum posts, or vendor claims
5. AI summaries or unverified notes

When conflict remains:

- state both sides
- show each side's status, evidence level, and scope
- use the higher-priority source only within its valid scope
- downgrade weaker material to hypothesis, risk reminder, or `needs-review`
- ask human review only when the conflict changes decisions, safety, money, production behavior, or core workflow rules

## Self-Optimization Loop

Use feedback to improve retrieval and answer quality:

```text
question answered
-> notes used are recorded or suggested for recording
-> feedback is captured as useful / wrong / incomplete / too_generic / stale
-> maintenance scan reviews feedback signals
-> metadata, scope, links, review cycle, or status suggestions are generated
-> human or evidence approves high-impact mutations
```

Allowed automatic improvements:

- suggest better `use_for`
- suggest narrower `scope`
- suggest `should_not_use_for`
- suggest links to related standards
- suggest review queue items

Not automatic:

- `draft -> verified`
- deleting notes
- resolving high-risk conflicts
- treating repeated usage as proof of correctness

## Human Review Questions

Ask only questions that change future behavior:

- What should this material be used for?
- What must it not be used for?
- Is it acceptable as `reviewed`, or only `draft`?
- What evidence is required before stronger claims?
- What is the most harmful misuse?

Every option must explain meaning, recommendation, and consequence.
