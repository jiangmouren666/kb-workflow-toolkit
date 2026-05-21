# Safety Model

The toolkit is built for conservative knowledge maintenance.

## Core Principle

AI can suggest changes. Humans and rules approve changes. Core knowledge is never silently modified.

## Trust Status

- `draft`: useful but not reviewed.
- `reviewed`: accepted by a human within a recorded scope.
- `verified`: supported by stronger evidence such as official docs, source code, experiments, backtests, or production results.
- `stale`: likely outdated or contradicted.
- `rejected`: should not be used.

No command should automatically upgrade a note to `verified`.

## Registries

Registries record decisions. They are not proof of truth.

- `human-review-registry.md`: durable human decisions about note usefulness and scope.
- `improvement-review-registry.md`: decisions about improvement candidates.
- Maintenance review registries: optional advanced pipeline records.

## Runtime State

Do not publish runtime state:

- `00-global/state/`
- `*.jsonl`
- lock files
- audit outputs
- generated maintenance reports

These files can contain local paths, note fingerprints, or private review decisions.

## Checksum-Gated Apply

`maintain apply` is not a general-purpose auto-editor. It can write only when all gates pass:

- The plan exists in `00-global/state/maintenance-apply-plans.jsonl`.
- The plan is `ready_preview`.
- The target path is a relative Markdown file inside the vault.
- The current target SHA256 matches the plan's `target_sha256`.
- The user passes `--write --confirm <plan-id>`.

Before writing, the tool saves a rollback snapshot under `00-global/state/rollback/`.

Allowed operations are limited to:

- Metadata patch.
- Append maintenance review note.
- Create split draft scaffold.

Do not use this as a full automatic rewrite system.

## Trust Drift

Trust drift happens when registry decisions, frontmatter status, and evidence metadata diverge over time.

Generate a report with:

```bash
python <vault_root>/00-global/scripts/trust-drift-report.py --root <vault_root> --write
```

The report is diagnostic. It should not automatically downgrade or upgrade notes.

## Private Material

Before publishing:

- Search for machine-specific absolute paths, mount points, source vault names, and user names.
- Search for raw copied content from books, papers, private notes, PDFs, chat logs, or source vaults.
- Remove API keys, cookies, credentials, and `.env` files.
- Prefer short synthetic examples.

## High-Risk Domains

For finance, medicine, legal, security, or production engineering:

- Treat LLM output as a hypothesis.
- Require external evidence before `verified`.
- Require an evidence checklist field before trusting `verified` metadata.
- Keep decision and risk boundaries explicit.
- Prefer reproducible commands, data versions, and audit trails.
