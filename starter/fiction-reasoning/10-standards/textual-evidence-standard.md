---
type: standard
domain: fiction-reasoning
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
  - textual_evidence
  - plot_reasoning
scope: fiction analysis, plot inference, character reasoning, timeline checks, and contradiction detection
should_not_use_for: treating speculation, fan theory, or adaptation changes as source-text fact
time_sensitivity: low
review_cycle: 365d
---

# Textual Evidence Standard

## Evidence Types

| Evidence Type | Strength | Use For | Limit |
|---|---|---|---|
| Direct source-text quote with chapter/position | high | verified textual fact | translation/version may matter |
| Multiple indirect textual clues | medium-high | reviewed inference | still inferential |
| Narrator or character statement | medium | perspective analysis | may be unreliable |
| Adaptation, commentary, fan theory | low | context or hypothesis | not source-text proof |

## Status Mapping

- `draft`: hypothesis, reader theory, foreshadowing guess, or incomplete timeline note.
- `reviewed`: human-accepted inference with textual support.
- `verified`: directly supported by source text with chapter/position.
- `stale`: contradicted by later chapters, revised edition, or updated canon.
- `rejected`: conflicts with source text or established timeline.

## Extra Metadata

```yaml
source_chapter:
quote_location:
character_perspective:
narrator_reliability:
spoiler_scope:
timeline_position:
```

## Risk Rules

- Do not present speculation as source-text fact.
- Always separate direct textual evidence from inference.
- Track spoiler scope before answering.
- Unreliable narrators and character bias must be marked.

## Conflict Priority

1. Direct source text with location.
2. Multiple consistent textual clues.
3. Reliable narrator perspective.
4. Character statements.
5. Reader inference, commentary, adaptation, or fan theory.
