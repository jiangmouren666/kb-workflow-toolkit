---
type: standard
domain: global
status: reviewed
confidence: high
evidence_level: user_experience
source: system-design
updated: 2026-05-18
use_for:
  - canonical_governance
  - answer_routing
  - maintenance_routing
  - stale_writeback_protection
scope: current authoritative governance overlay for this knowledge vault
should_not_use_for: replacing external verification or domain-specific evidence standards
time_sensitivity: medium
review_cycle: 90d
human_review:
  reviewer: user
  decision: old flow writeback still exists, use canonical v2 overlay
  reviewed_at: 2026-05-18
  result: accepted as current governance entry point
usage_count: 0
last_used:
last_feedback:
failure_modes: []
improvement_notes: []
---

# Current Governance V2

This is the current governance entry point when older files are being rewritten by stale flows or sync tools.

## Authoritative Order

1. `00-global/current-governance-v2.md`
2. `00-global/human-review-registry.md`
3. `00-global/write-protection-policy.md`
4. `00-global/import-interaction-workflow.md`
5. domain evidence standards under each domain's `10-standards/`
6. individual note frontmatter

If an old file disagrees with the registry or this document, treat the old file as legacy maintenance debt.

## Old File Handling

The following legacy files may still be overwritten by old flows and should not be treated as the only source of truth:

- `00-global/routing-rules.md`
- `00-global/maintenance-rules.md`
- `00-global/human-machine-governance.md`
- `00-global/review-decision-questions.md`
- `00-global/answer-risk-reminders.md`
- `00-global/evaluation-scorecard.md`
- old `review-queue.md`

Use `review-queue-v2.md` for active review work.

## Registry Overlay Rule

When `human-review-registry.md` says a note is `reviewed`, the effective status is `reviewed` within the recorded scope, even if the note frontmatter has regressed to `draft`.

This does not make the note `verified`. External evidence, source code checks, experiments, backtests, official docs, or production results are still required for `verified`.

## Maintenance Rule

Scans should distinguish:

- blocking findings: metadata missing from unregistered active notes, invalid status, broken links, conflicts, stale candidates.
- overlay-applied notices: note frontmatter disagrees with registry, but the registry already supplies the effective state.
- legacy metadata notices: old draft notes with `use_when` but without full `use_for` governance fields.

Overlay notices should be visible, but should not block use of reviewed knowledge.

## CLI Governance Rule

Use `00-global/scripts/kb.py` as the preferred maintenance entry point:

- `doctor`: status, manifest drift, and registry repair dry-run.
- `scan`: strict diagnostic scan.
- `repair`: registry overlay repair, dry-run by default.
- `snapshot`: write SHA256 manifest snapshots under `00-global/state/`.
- `diff`: compare current vault files with the latest snapshot.
- `sync`: dry-run sync to an Obsidian target, with pre-sync scan.
- `autosync`: configure, inspect, or run the configured Obsidian sync target.

Write commands should acquire `00-global/state/kb.lock`. This is an advisory lock for compliant tools; it detects and reduces accidental concurrent writes but does not stop external processes that ignore it.

Auto-sync may run after compliant writes if configured, but it must skip when strict scan has blocking findings or registry overlay drift.

## Import Interaction Rule

Use `00-global/import-interaction-workflow.md` for user-facing ingestion.

- Guided import asks 2-3 high-impact questions in the chat window before final write.
- Quick import is allowed when the user says `快速导入`, `默认处理`, or equivalent wording.
- Quick import saves as low-trust `draft` and records skipped review questions.
