---
type: standard
domain: global
status: draft
confidence: high
source: system-design
updated: 2026-05-20
use_when:
  - scan knowledge vault
  - audit stale notes
  - review classification quality
  - maintain Obsidian links
---

# Maintenance Rules

## Core Rule

The scanner and improvement loop are read-only by default. They may create audit reports, review queues, and improvement candidate reports, but they must not delete, merge, move, or upgrade trust status without explicit approval.

## Scan Checks

- Required metadata: `type`, `domain` or `primary_domain`, `status`, `confidence`, `source`, `updated` or `ingested`.
- Status values: `raw`, `draft`, `reviewed`, `verified`, `stale`, `deprecated`, `rejected`, `needs-review`.
- Confidence values: `low`, `medium`, `high`.
- Review cycle values: `none`, `30d`, `90d`, `180d`, `365d`.
- Link health: wikilinks should resolve to a note or be listed as unresolved.
- Category fit: folder domain should agree with `domain` or `primary_domain`.
- Conflict hints: notes that recommend behavior rejected by standards should be reviewed.

## Status Update Policy

- `draft -> reviewed`: allowed after human review and system consistency check.
- `draft -> verified`: never automatic.
- `reviewed -> verified`: requires external evidence, experiment, source-code check, official documentation, or comparable proof.
- `draft/verified -> stale`: allowed only as a suggestion unless user authorizes status updates.
- `stale -> deprecated`: requires reason and replacement note when possible.
- `any -> rejected`: requires evidence and human approval.

## Review Queue Policy

Every high-priority finding should be added to `00-global/review-queue.md` with:

- path
- finding type
- suggested action
- reason
- confidence
- approval needed

Use [[review-decision-questions]] to present compact A/B/C/D decisions. Human review should decide status, classification, trust level, or validation need; it should not require rewriting the full note.

## Improvement Candidate Policy

`improvement-loop.py` is a suggestion generator, not a repair tool.

It may propose candidates such as:

- `stale_high_risk`
- `frequently_used_but_draft`
- `negative_feedback`
- `missing_evidence_for_verified`
- `missing_feedback_fields`
- `conflict_candidate`
- `low_quality_context_signal`

Allowed outputs:

- `00-global/improvement-candidates.md`
- `00-global/state/improvement-candidates.jsonl`

Forbidden actions without explicit approval:

- changing note `status`, `confidence`, or `evidence_level`
- editing `human-review-registry.md`
- deleting, moving, merging, or rewriting notes
- treating low retrieval score as proof that a note is wrong

Candidate reports should explain path, candidate type, severity, reason, suggested action, and whether human review is required.

## Improvement Review Registry Policy

`00-global/improvement-review-registry.md` records decisions about improvement candidates only.

Allowed decisions:

- `accepted_for_review`
- `needs_more_evidence`
- `deferred`
- `rejected`
- `converted_to_task`

This registry may suppress repeated improvement suggestions when the exact candidate fingerprint has already been rejected, accepted for review, or converted to a task. It must not be treated as evidence that the underlying note is correct, reviewed, verified, stale, or rejected.

If a candidate is marked `deferred` or `needs_more_evidence`, it may appear again with prior decision metadata so the user can revisit it later.

## Maintenance Task Queue Policy

`maintenance-tasks.py` turns reviewed improvement decisions into work items.

Allowed task types:

- `manual_knowledge_review`
- `evidence_collection`
- `external_task`

Allowed outputs:

- `00-global/maintenance-tasks.md`
- `00-global/state/maintenance-tasks.jsonl`

The task queue is not an automatic repair plan. Tasks must not change note frontmatter, `human-review-registry.md`, `improvement-review-registry.md`, domain standards, or trust status unless the user separately approves the actual maintenance action.

Tasks are generated only from actionable improvement review decisions:

- `accepted_for_review`
- `needs_more_evidence`
- `converted_to_task`

`deferred` and `rejected` decisions should not create maintenance tasks.

## Consolidated Maintenance Apply Plan Policy

`maintenance-apply-plans.py` is the preferred daily maintenance planning entry point. It turns actionable `improvement-review-registry.md` decisions directly into consolidated apply plan previews.

Allowed outputs:

- `00-global/maintenance-apply-plans.md`
- `00-global/state/maintenance-apply-plans.jsonl`

Apply plans may record source candidate, review decision, target path, current SHA256, proposed operations, evidence requirements, risk notes, rollback notes, and blocked/ready status. They must not apply patches, edit notes, change task/proposal/draft/package status, update review registries, alter domain standards, or change trust status.

Domain-specific proposed operations should remain intentionally small and hard-coded for now. Supported advisory templates are limited to `fiction-reasoning/`, `programming/`, and `quant/`; adding a generalized plugin or multi-domain rules engine is out of scope unless explicitly approved.

`kb.py maintain apply` is reserved as a future explicit apply workflow. In this phase it must remain a safe stub and must not modify notes.

The older task/proposal/draft/package stages remain available as advanced/internal debug pipeline stages, but daily use should prefer `improve -> review-improvements -> maintain plan`.

## Maintenance Proposal Policy

`maintenance-proposals.py` turns open maintenance tasks into change proposals.

Allowed proposal types:

- `metadata_update_proposal`
- `evidence_collection_plan`
- `external_task_brief`

Allowed outputs:

- `00-global/maintenance-proposals.md`
- `00-global/state/maintenance-proposals.jsonl`

Proposals are approval-stage drafts. They may describe possible metadata updates, evidence collection plans, or rewrite/split considerations, but they must not include an automatically applied patch and must not edit notes, task status, review registries, human-review registries, domain standards, or trust status.

Applying a proposal requires a later explicit approval workflow.

## Maintenance Proposal Review Registry Policy

`00-global/maintenance-proposal-review-registry.md` records human approval decisions for maintenance proposals only.

Allowed decisions:

- `approved`
- `needs_more_evidence`
- `request_changes`
- `rejected`
- `deferred`

`approved` and `rejected` decisions suppress repeated generation of the same proposal. `needs_more_evidence`, `request_changes`, and `deferred` proposals may remain visible with prior decision metadata so the user can revisit them.

This registry is an authorization record for later maintenance planning. It must not apply patches, edit notes, change task status, rewrite proposals, update human-review registries, alter domain standards, or change trust status.

## Maintenance Change Draft Policy

`maintenance-change-drafts.py` turns approved maintenance proposals into concrete change drafts.

Allowed draft types:

- `metadata_change_draft`
- `evidence_collection_draft`
- `external_task_draft`

Allowed outputs:

- `00-global/maintenance-change-drafts.md`
- `00-global/state/maintenance-change-drafts.jsonl`

Change drafts are execution-preparation artifacts. They may describe specific review steps, suggested metadata edits, evidence checks, or external work briefs, but they must not apply patches, edit notes, change task or proposal status, update review registries, alter domain standards, or change trust status.

Only proposals with an `approved` decision in `00-global/maintenance-proposal-review-registry.md` may generate change drafts. A later explicit apply workflow is still required before any knowledge note is changed.

## Maintenance Change Draft Review Registry Policy

`00-global/maintenance-change-draft-review-registry.md` records human final-approval decisions for concrete change drafts.

Allowed decisions:

- `ready_to_apply`
- `needs_more_evidence`
- `request_changes`
- `rejected`
- `deferred`

`ready_to_apply` and `rejected` decisions suppress repeated review of the same draft. `needs_more_evidence`, `request_changes`, and `deferred` drafts may remain visible with prior decision metadata so the user can revisit them.

This registry is an authorization input for a later explicit apply workflow. It must not apply patches, edit notes, change task/proposal/draft status, update other review registries, alter domain standards, or change trust status.

## Maintenance Apply Package Policy

`maintenance-apply-packages.py` turns `ready_to_apply` change drafts into apply package previews.

Allowed outputs:

- `00-global/maintenance-apply-packages.md`
- `00-global/state/maintenance-apply-packages.jsonl`

Apply packages may record target file existence, current SHA256, preflight checks, proposed operations, risk notes, and rollback notes. They must not apply patches, edit notes, change task/proposal/draft status, update review registries, alter domain standards, or change trust status.

Only change drafts with a `ready_to_apply` decision in `00-global/maintenance-change-draft-review-registry.md` may generate apply packages. A later explicit apply command with target-hash verification is still required before any knowledge note is changed.

## Exclusions

Do not scan hidden folders, binary attachments, generated caches, or files under `00-global/audit-reports/` as source notes. Generated context/evaluation runs may be used only as feedback signals for improvement candidates.
