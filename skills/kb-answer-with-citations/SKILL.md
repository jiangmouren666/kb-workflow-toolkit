---
name: kb-answer-with-citations
description: Answer questions from a local KB Workflow Toolkit vault with explicit citations, evidence levels, uncertainty, and misuse boundaries. Use when the user asks to answer from their knowledge base, Obsidian vault, KB, notes, or wants cited answers grounded in the vault.
---

# KB Answer With Citations

## Purpose

Use this skill when answering from a KB Workflow Toolkit vault. The goal is not only to find relevant notes, but to preserve trust boundaries: cite source paths, separate fact from inference, and state what the vault does not prove.

## Required Reading Order

1. Read `<vault_root>/00-global/current-governance-v2.md` if present.
2. Read `<vault_root>/00-global/routing-rules.md` if present.
3. Read `<vault_root>/00-global/human-review-registry.md` if present.
4. Read the relevant domain standard, for example:
   - `fiction-reasoning/10-standards/textual-evidence-standard.md`
   - `programming/10-standards/code-verification-standard.md`
   - `quant/10-standards/domain-evidence-standard.md`
   - `machine-learning/10-standards/leakage-prevention.md`
5. Read only the most relevant notes needed to answer.

## Answer Rules

- Cite every substantive claim with note paths.
- Prefer `reviewed` and registry-approved notes over unreviewed drafts.
- Treat `draft` notes as low-trust context, not settled knowledge.
- Treat `verified` as valid only when the note includes strong evidence.
- Do not present user annotations, fan theories, model output, or source excerpts as proven facts.
- If evidence is missing, say what is missing.
- If the vault does not contain enough support, say so instead of filling gaps from memory.

## Citation Format

Use concise path citations:

```markdown
结论句。依据：`domain/path/note.md`
```

For mixed evidence:

```markdown
结论：...

依据：
- `path/a.md`: reviewed checklist, medium confidence.
- `path/b.md`: draft source excerpt, useful as context only.

不确定性：
- 缺少可运行实验或外部验证。
```

## Output Template

```markdown
## Answer

<direct answer>

## Evidence

- `<path>`: <status/evidence_level/use>.

## Boundaries

- <what this answer should not be used for>.
- <missing validation or open questions>.
```

## Domain Notes

For fiction reasoning, keep source-text quotes separate from inference and mention spoiler scope when known.

For programming, include runnable command, dependency versions, official docs, or source-code checks when available.

For quant, never treat backtest notes as trading approval. Mention train/test split, data availability, transaction costs, and leakage checks when relevant.
