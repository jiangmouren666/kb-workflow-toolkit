---
name: kb-import-and-maintain
description: Import materials into a KB Workflow Toolkit vault and run safe maintenance workflows. Use when the user asks to import notes, PDFs, Obsidian documents, source files, or to scan, review, improve, maintain, or package a knowledge vault.
---

# KB Import And Maintain

## Core Rule

AI proposes. Humans and rules approve. Core knowledge is never silently modified.

## Resolve Vault Root

Resolve `<vault_root>` before importing or maintaining. Use this order:

1. User-provided `vault_root` in the current request.
2. `knowledge-vaults/` under the current workspace.
3. Environment variable `KNOWLEDGE_VAULT_ROOT`.
4. `00-global/state/vault-config.json` if already inside a vault.
5. Repository `starter/` only for examples or smoke tests.

If no candidate is clear, ask the user for the vault path. Do not hardcode local paths into this skill.

## Import Flow

1. Resolve `<vault_root>`.
2. Classify the domain.
3. Extract facts, claims, methods, risks, and unknowns.
4. Ask for confirmation before final write when placement, trust status, or future retrieval behavior is affected.
5. If the user asks for quick import, save as low-trust `draft`.
6. Add `scope`, `should_not_use_for`, `failure_modes`, and `improvement_notes`.
7. Never mark imported material `reviewed` or `verified` without explicit human review or strong evidence.

## Recommended Metadata

```yaml
type: source-note
status: draft
confidence: low
evidence_level: source_claim
use_for:
  - reference
scope: <what this note is useful for>
should_not_use_for: <misuse boundary>
time_sensitivity: medium
review_cycle: 180d
failure_modes: []
improvement_notes: []
```

## Maintenance Flow

Run dry-run commands first:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> scan
python <vault_root>/00-global/scripts/kb.py --root <vault_root> improve
python <vault_root>/00-global/scripts/kb.py --root <vault_root> maintain status
```

Only use `--write` after the user approves writing reports or registries.

## Human Review Decisions

Use compact decisions when possible:

```text
S=A,U=C,R=C,E=A,Split=Y
```

Meanings:

- `S`: status decision.
- `U`: intended use.
- `R`: misuse or time-sensitivity risk.
- `E`: evidence need.
- `Split`: whether the note should be split before upgrading.

Write human decisions to `00-global/human-review-registry.md`. This registry is a usefulness and scope overlay, not proof of external truth.

## Maintain Plan

After improvement review:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> maintain plan
```

The plan is a preview. It may record target SHA256, proposed operations, safe operations, evidence requirements, and rollback notes.

To apply, first dry-run:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> maintain apply --plan-id <plan-id>
```

Only write when the user explicitly confirms:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> maintain apply --plan-id <plan-id> --write --confirm <plan-id>
```

Apply must block if target SHA256 no longer matches. Successful writes must create a rollback snapshot.

## Trust Drift

Generate trust drift reports when registry decisions and frontmatter may have diverged:

```bash
python <vault_root>/00-global/scripts/trust-drift-report.py --root <vault_root>
```

The report is diagnostic and must not automatically upgrade or downgrade notes.

## Prohibited Without Explicit Approval

- Deleting, moving, merging, or rewriting notes.
- Upgrading `draft` to `reviewed`.
- Upgrading anything to `verified`.
- Editing trust status based only on AI judgment.
- Publishing private source material.
