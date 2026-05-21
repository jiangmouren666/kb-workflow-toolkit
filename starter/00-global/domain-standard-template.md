---
type: template
domain: global
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
  - domain_standard_template
  - evidence_standard_design
  - verification_rule_design
scope: creating domain-specific evidence and verification standards
should_not_use_for: replacing domain expertise or external evidence
time_sensitivity: medium
review_cycle: 180d
---

# Domain Standard Template

Use this template when adding a new knowledge domain. The global framework defines shared status labels; the domain standard defines what those labels mean in that domain.

## Domain Scope

- Applies to:
- Does not apply to:
- High-risk uses:

## Evidence Types

| Evidence Type | Strength | Use For | Limit |
|---|---|---|---|
|  |  |  |  |

## Status Mapping

| Status | Domain Meaning | Required Evidence |
|---|---|---|
| `draft` | unconfirmed material | source claim, raw note, or AI summary |
| `reviewed` | human-accepted reference | human review and scope boundaries |
| `verified` | strong domain evidence | domain-specific verification evidence |
| `stale` | may be outdated | review cycle, version change, contradiction, or changed context |
| `rejected` | confirmed wrong or unsafe | contradiction, failed test, or human rejection |

## Verification Rules

`verified` requires:

-

`reviewed` means:

-

`draft` means:

-

## Risk Rules

Always warn when:

-

Never use this domain knowledge for:

-

## Conflict Priority

1.
2.
3.

## Human Review Triggers

Ask the user before:

-

## Extra Metadata

```yaml
domain_specific_field:
```
