---
type: guide
domain: global
status: reviewed
confidence: high
evidence_level: user_experience
source: system-design
updated: 2026-05-20
use_for:
  - daily_usage
  - onboarding
  - command_phrasing
scope: simple entry points for using the knowledge vault
should_not_use_for: replacing domain standards or detailed maintenance rules
time_sensitivity: medium
review_cycle: 180d
human_review:
  reviewer: user
  decision: approved simple usage entry point
  reviewed_at: 2026-05-18
  result: accepted as reviewed user-facing guide, not external evidence
usage_count: 0
last_used:
last_feedback:
failure_modes: []
improvement_notes: []
---

# Usage Guide

Use these phrases instead of remembering internal files, folders, or scripts.

For the exact import interaction rules, see [[import-interaction-workflow]].

## 0. Choose Or Initialize A Vault Root

The local folder selected by the user is the primary knowledge vault. Obsidian, cloud folders, WebDAV, Git mirrors, NAS folders, or export packages are optional targets only.

Initialize a local-first vault:

```bash
python <vault_root>/00-global/scripts/kb.py init --root <vault_root>
```

Configure an optional local-to-target sync destination only when needed:

```bash
python <vault_root>/00-global/scripts/kb.py configure --root <vault_root> --sync-target <target-path>
```

The configuration is stored at `<vault_root>/00-global/state/vault-config.json`.

## 1. Import Material

Say:

```text
帮我把这篇文章导入知识库
```

or:

```text
把这个 PDF/图片/链接/笔记入库
```

Expected flow:

1. Ask or resolve `vault_root`.
2. Classify domain.
3. Extract facts, claims, methods, risks, and unknowns.
4. Show an `入库前确认` prompt in the chat window when the answer changes future retrieval behavior.
5. Apply the user's answers to `use_for`, `status`, `scope`, `should_not_use_for`, and review needs.
6. Save as `draft` unless there is human review or strong evidence.

If you do not want to answer questions, say:

```text
快速导入
```

Expected quick-import behavior:

1. Save as low-trust `draft`.
2. Keep `evidence_level: source_claim`.
3. Add risks, unknowns, and skipped review questions.
4. Do not mark as `reviewed` or `verified`.

## 2. Ask From The Knowledge Base

Say:

```text
基于我的知识库回答这个问题：...
```

Expected flow:

1. Read global governance and routing rules.
2. Read `human-review-registry.md`.
3. Read the relevant domain evidence standard.
4. Read only the most relevant notes.
5. State evidence, uncertainty, and missing validation.

## 3. Continue Human Review

Say:

```text
继续人工审核下一批
```

Expected flow:

1. Use `00-global/review-queue-v2.md`.
2. Show 3-8 items with path, excerpt, key claims, risks, and suggested dimensions.
3. Accept compact replies such as:

```text
1:S=B,U=C,R=B,E=E 2:S=A,U=D,R=D,E=B
```

4. Write accepted decisions to `human-review-registry.md` and a batch archive.

## 4. Scan And Maintain

Say:

```text
扫描知识库有没有问题
```

Expected command:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> doctor
```

The scan is diagnostic. It must not delete, merge, move, or upgrade trust status without approval.

If old content or stale agents cause reviewed note metadata to regress, repair from the registry overlay:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> repair
```

Only add `--write` after checking the dry-run output.

Before and after important maintenance, create or compare a manifest snapshot:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> snapshot
python <vault_root>/00-global/scripts/kb.py --root <vault_root> diff
```

## 5. Generate Improvement Candidates

Say:

```text
找出知识库里哪些内容需要升级、重验、拆分或降级
```

Expected dry-run command:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> improve
```

Only add `--write` when you want to write candidate reports:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> improve --write
```

This writes `00-global/improvement-candidates.md` and `00-global/state/improvement-candidates.jsonl`. It does not modify note frontmatter, trust status, standards, or `human-review-registry.md`.

## 6. Review Improvement Candidates

Say:

```text
继续审核改进候选
```

Expected command:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> review-improvements --limit 5
```

Record compact decisions after reviewing the batch:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> review-improvements --decisions "1A 2C 3E"
```

Decision meanings:

- `A`: accepted for manual review
- `B`: needs more evidence
- `C`: deferred
- `D`: rejected
- `E`: converted to task

Decisions are written to `00-global/improvement-review-registry.md`. This registry records how to handle improvement suggestions; it is not a trust-status overlay and does not modify `human-review-registry.md`.

## 7. Generate Consolidated Maintenance Plans

Say:

```text
把已审核的改进项整理成维护执行计划
```

Expected dry-run command:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> maintain plan
```

Write apply plan reports after checking the dry-run:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> maintain plan --write
```

Check maintenance status:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> maintain status
```

This writes `00-global/maintenance-apply-plans.md` and `00-global/state/maintenance-apply-plans.jsonl`. Apply plans consolidate the older task/proposal/draft/package pipeline into one reviewable preview. They do not apply patches or modify notes, registries, standards, task/proposal/draft/package status, or trust status.

For daily usefulness without adding a plugin system, `maintain plan` includes a few built-in domain suggestions for `fiction-reasoning/`, `programming/`, and `quant/` notes. These suggestions are advisory only; they still require human review and a later explicit apply step.

The reserved apply entry point is intentionally a safe stub in this phase:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> maintain apply --plan-id <plan-id>
```

It reports `not_implemented` and does not modify notes.

## 8. Advanced: Generate Maintenance Tasks

Say:

```text
把已审核的改进候选转成维护任务
```

Expected dry-run command:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> tasks generate
```

Write the task queue after checking the dry-run:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> tasks generate --write
```

List existing tasks:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> tasks list
```

This writes `00-global/maintenance-tasks.md` and `00-global/state/maintenance-tasks.jsonl`. Tasks are work items only; they do not modify notes, registries, standards, or trust status.

## 9. Advanced: Generate Maintenance Proposals

Say:

```text
把维护任务转成变更提案
```

Expected dry-run command:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> proposals generate
```

Write proposals after checking the dry-run:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> proposals generate --write
```

List existing proposals:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> proposals list
```

This writes `00-global/maintenance-proposals.md` and `00-global/state/maintenance-proposals.jsonl`. Proposals explain suggested changes, evidence needs, and risks. They are not patches and are not applied automatically.

## 10. Advanced: Review Maintenance Proposals

Say:

```text
继续审批维护提案
```

Expected command:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> review-proposals --limit 5
```

Record compact approval decisions after reviewing the batch:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> review-proposals --decisions "1A 2C 3E"
```

Decision meanings:

- `A`: approved
- `B`: needs more evidence
- `C`: request changes
- `D`: rejected
- `E`: deferred

Decisions are written to `00-global/maintenance-proposal-review-registry.md`. This registry records authorization for later maintenance planning only; it does not apply patches or modify notes, task status, proposals, domain standards, or trust status.

## 11. Advanced: Generate Maintenance Change Drafts

Say:

```text
把已批准的维护提案转成变更草案
```

Expected dry-run command:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> change-drafts generate
```

Write change draft reports after checking the dry-run:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> change-drafts generate --write
```

List existing change drafts:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> change-drafts list
```

This writes `00-global/maintenance-change-drafts.md` and `00-global/state/maintenance-change-drafts.jsonl`. Change drafts are concrete execution-preparation notes for approved proposals only; they still do not apply patches or modify notes, registries, standards, task status, proposal status, or trust status.

## 12. Advanced: Review Maintenance Change Drafts

Say:

```text
继续最终审批变更草案
```

Expected command:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> review-change-drafts --limit 5
```

Record compact final-approval decisions after reviewing the batch:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> review-change-drafts --decisions "1A 2C 3E"
```

Decision meanings:

- `A`: ready to apply in a later explicit apply workflow
- `B`: needs more evidence
- `C`: request changes
- `D`: rejected
- `E`: deferred

Decisions are written to `00-global/maintenance-change-draft-review-registry.md`. This registry is the authorization input for a future apply workflow; it does not apply patches or modify notes, tasks, proposals, drafts, standards, or trust status.

## 13. Advanced: Generate Apply Package Previews

Say:

```text
把可执行的变更草案打包成执行预览
```

Expected dry-run command:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> apply-packages generate
```

Write apply package reports after checking the dry-run:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> apply-packages generate --write
```

List existing apply packages:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> apply-packages list
```

This writes `00-global/maintenance-apply-packages.md` and `00-global/state/maintenance-apply-packages.jsonl`. Apply packages record target file hashes, preflight checks, proposed operations, and rollback notes for `ready_to_apply` drafts only. They are execution previews, not patches, and do not modify notes, registries, standards, task/proposal/draft status, or trust status.

## 14. Optional Export/Sync Target

Say:

```text
同步主知识库到一个可选目标
```

Expected dry-run command:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> sync --target <target-path>
```

Only use `--write` after checking the dry-run output.

To enable automatic sync after successful maintenance writes:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> autosync enable --target <target-path>
```

Check the configured target:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> autosync status
```

Run the configured sync manually:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> autosync run
```

Auto-sync is conservative: it skips writing to the optional target if the scan has blocking findings or registry overlay drift. If no target is configured, the vault remains fully usable as a local-only knowledge base.

## 15. Add A New Domain

Say:

```text
给这个领域新建知识标准：<domain>
```

Expected flow:

1. Start from `00-global/domain-standard-template.md`.
2. Define evidence types.
3. Define what `draft`, `reviewed`, `verified`, `stale`, and `rejected` mean in that domain.
4. Define conflict priority.
5. Define human review triggers.

## Default Reminder

The global framework governs the process. Domain standards define evidence. Individual notes should not make strong claims outside their domain standard.

For write conflicts, follow `00-global/write-protection-policy.md`: registry decisions are authoritative over stale individual-note frontmatter. Prefer `kb.py` for maintenance because it adds manifest snapshots, drift checks, and an advisory lock around writes.
