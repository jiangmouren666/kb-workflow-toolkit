# Usage

The toolkit is meant to be driven by plain language plus a small CLI.

## Import Material

When adding a document, default to a low-trust draft unless the material has been reviewed.

Suggested metadata:

```yaml
status: draft
confidence: low
evidence_level: source_claim
```

Add:

- `scope`: what this note is useful for.
- `should_not_use_for`: how the note can be misused.
- `failure_modes`: likely mistakes.
- `improvement_notes`: what a human should clarify later.

## Ask From The Knowledge Base

Before answering from the vault:

1. Read global governance.
2. Read `human-review-registry.md`.
3. Read the relevant domain standard.
4. Use only the most relevant notes.
5. State evidence and uncertainty.

## Human Review

A compact decision can record status, use, risk, and evidence needs:

```text
S=A,U=C,R=C,E=A,Split=Y
```

Meaning:

- `S=A`: keep as draft.
- `U=C`: use for decision or risk review.
- `R=C`: high misuse risk.
- `E=A`: source/docs evidence exists, but more structure may be needed.
- `Split=Y`: split before upgrading.

## Maintenance

Daily maintenance should use:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> improve
python <vault_root>/00-global/scripts/kb.py --root <vault_root> review-improvements --limit 5
python <vault_root>/00-global/scripts/kb.py --root <vault_root> maintain plan
```

The older task, proposal, draft, and package commands remain available for debugging advanced workflows, but `maintain plan` is the recommended daily entry point.
