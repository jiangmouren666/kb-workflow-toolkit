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
- Keep decision and risk boundaries explicit.
- Prefer reproducible commands, data versions, and audit trails.
