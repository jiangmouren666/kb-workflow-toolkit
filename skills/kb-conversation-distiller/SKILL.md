---
name: kb-conversation-distiller
description: Distill reusable insights from agent conversations into KB Workflow Toolkit conversation digest drafts. Use when the user asks to save, remember, summarize, distill, or 沉淀 a conversation into the knowledge base.
---

# KB Conversation Distiller

## Purpose

Create a concise knowledge digest from an agent conversation. Save reusable decisions, workflows, failure modes, and follow-up actions. Do not save the full chat transcript.

## Resolve Vault Root

Resolve `<vault_root>` before writing:

1. User-provided `vault_root` in the current request.
2. `knowledge-vaults/` under the current workspace.
3. Environment variable `KNOWLEDGE_VAULT_ROOT`.
4. `00-global/state/vault-config.json` if already inside a vault.
5. Repository `starter/` only for examples or smoke tests.

If no candidate is clear, ask for the vault path.

## When To Use

Use this skill when the user says things like:

- `把这段对话沉淀到知识库`
- `记一下这个结论`
- `保存这次复盘`
- `把刚才的流程变成知识库笔记`
- `总结这次 agent 交流里的精华`

## What To Extract

- Decision: what was chosen and why.
- Workflow: reusable steps.
- Failure/fix: what went wrong and how it was fixed.
- Anti-pattern: what to avoid next time.
- Prompt pattern: a useful way to ask or review.
- Follow-up: what should become a note, checklist, skill, or rule.

## What Not To Save

- Full chat transcript.
- Secrets, API keys, credentials, private paths, or raw personal data.
- Long copyrighted source excerpts.
- Agent claims as `verified` knowledge.

## Metadata Rules

Use:

```yaml
type: conversation-digest
domain: ai-agent
status: draft
confidence: medium
evidence_level: user_experience
source: agent-conversation
```

`evidence_level` must be one of `ALLOWED_EVIDENCE_LEVEL`: `none`, `source_claim`, `user_experience`, `official_doc`, `source_code`, `experiment`, `backtest`, `production_result`.

## Output Location

Default path:

```text
<vault_root>/00-global/conversation-digests/YYYY-MM-DD-<short-topic>.md
```

If the digest is clearly domain-specific, still start in `00-global/conversation-digests/` unless the user explicitly asks to create a domain note. Human review can split it later.

## Digest Template

```markdown
# Conversation Digest: <Topic>

## Source Context

- Conversation date:
- User intent:
- Relevant vault/domain:

## Why This Matters

## Reusable Insights

## Decisions

## Failure Modes Or Anti-Patterns

## Evidence And Confidence

## Follow-Up Actions

## Should Split Into
```

## Post-Write Validation

After writing a digest, run:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> scan
```

Fix safe metadata issues and re-run scan before claiming the digest is complete.
