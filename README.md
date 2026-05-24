# KB Workflow Toolkit

Local-first knowledge base workflow toolkit for Obsidian-style vaults and AI-assisted maintenance.

The core rule is simple:

> AI proposes. Humans and rules approve. Core knowledge is never silently modified.

This repository packages a clean starter vault, maintenance scripts, companion AI skills, workflow docs, and sanitized examples. It is designed for users who want a reusable knowledge base process across domains such as fiction reasoning, programming, quant research, and machine learning.

## What Is Included

- `starter/`: an empty starter vault with domain standards, global governance docs, and CLI scripts.
- `skills/`: companion Cursor Skills for cited answers, safe import/maintenance behavior, and manual conversation distillation.
- `docs/`: installation, usage, workflow, safety, and publishing notes.
- `examples/`: small sanitized examples that show import, review, and maintenance flows.

## What Is Not Included

- Private Obsidian notes.
- Raw source materials from your personal vault.
- Runtime state such as locks, JSONL queues, audit outputs, or local sync config.
- Credentials, API keys, cookies, or machine-specific paths.

## Quick Start

Copy the starter vault to your own location:

```bash
cp -R starter my-knowledge-vault
```

Run a diagnostic scan:

```bash
python my-knowledge-vault/00-global/scripts/kb.py --root my-knowledge-vault scan
```

Generate improvement suggestions without changing notes:

```bash
python my-knowledge-vault/00-global/scripts/kb.py --root my-knowledge-vault improve
```

After human review, generate a consolidated maintenance plan:

```bash
python my-knowledge-vault/00-global/scripts/kb.py --root my-knowledge-vault maintain plan
```

Preview a checksum-gated apply:

```bash
python my-knowledge-vault/00-global/scripts/kb.py --root my-knowledge-vault maintain apply --plan-id <plan-id>
```

Actually applying requires explicit confirmation:

```bash
python my-knowledge-vault/00-global/scripts/kb.py --root my-knowledge-vault maintain apply --plan-id <plan-id> --write --confirm <plan-id>
```

The apply step checks the target SHA256 and saves a rollback snapshot before writing.

## Recommended Daily Flow

1. Import material as a low-trust draft unless it has been reviewed.
2. Scan the vault for metadata, category, and governance issues.
3. Generate improvement candidates.
4. Record human decisions.
5. Generate a maintenance plan preview.
6. Apply only checksum-gated safe operations with explicit confirmation.
7. Periodically generate trust drift reports for registry/frontmatter and `verified` evidence drift.

See [docs/workflow.md](docs/workflow.md) for the full flow.

## Companion AI Skills

The CLI manages notes and maintenance reports. The skills guide AI behavior:

- `skills/kb-answer-with-citations`: answer from the vault with citations, evidence levels, and uncertainty.
- `skills/kb-import-and-maintain`: import material and run safe maintenance workflows.
- `skills/kb-conversation-distiller`: manually distill reusable insight from agent conversations into draft digest notes.

See [docs/skills.md](docs/skills.md) for installation and usage.

## Safety Model

The toolkit is conservative by design:

- Scans and improvement loops are read-only by default.
- Review registries record decisions; they do not prove external truth.
- `reviewed` means useful within a human-approved scope.
- `verified` requires stronger evidence such as official docs, source code, experiments, backtests, or production results.
- `maintain apply --write` requires `--confirm <plan-id>`, target SHA256 match, and rollback snapshot creation.
- Private knowledge should stay outside this public repository.

See [docs/safety.md](docs/safety.md) before publishing or syncing a vault.

## Repository Layout

```text
.
  README.md
  LICENSE
  docs/
  examples/
  skills/
  starter/
```

## License

MIT. Use the toolkit freely, but review and adapt the rules before trusting it in high-risk domains.
