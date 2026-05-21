---
type: standard
domain: programming
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
  - code_verification
  - implementation_review
scope: code snippets, bug fixes, implementation patterns, scripts, and engineering decisions
should_not_use_for: claiming production safety without tests, review, and deployment evidence
time_sensitivity: medium
review_cycle: 180d
---

# Code Verification Standard

## Evidence Types

| Evidence Type | Strength | Use For | Limit |
|---|---|---|---|
| Passing tests in the current project | high | bug fix and behavior verification | only covers tested behavior |
| Minimal reproduction before/after | high | root-cause validation | must reproduce the real symptom |
| Source code in current repo | high | implementation truth | may differ from deployed version |
| Official docs / API reference | medium-high | API usage | version must match |
| Blog / StackOverflow / AI output | low | hypotheses | must be tested locally |

## Status Mapping

- `draft`: unrun code, AI-generated snippet, blog pattern, or untested idea.
- `reviewed`: human-accepted pattern or code review note, not yet run in current context.
- `verified`: tests or commands passed in the current environment, with version/context recorded.
- `stale`: dependency, API, runtime, or project version changed.
- `rejected`: fails reproduction, breaks tests, or contradicts current code.

## Verification Rules

`verified` requires:

- command output, test result, or runtime evidence
- version/environment when relevant
- clear scope of what was verified

## Risk Rules

- Do not treat code as working unless it has run.
- Do not generalize a fix beyond the tested scope.
- For production changes, include rollback or failure-mode notes.

## Conflict Priority

1. Current project tests and runtime logs.
2. Current project source code.
3. Official docs matching installed version.
4. Maintainer issues or release notes.
5. Tutorials, blogs, or AI summaries.
